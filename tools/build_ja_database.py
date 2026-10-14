#!/usr/bin/env python3
"""
build_ja_database.py  (version 2.2)

Builds `ja_cards.json.gz` - the card database for the 悪知恵 site: one entry
per real Magic card, with its Japanese name / type / rules text wherever a
Japanese printing exists, and English for every card.

Data source: Scryfall's free official bulk export ('all_cards', every
language of every printing) - https://scryfall.com/docs/api/bulk-data

WHAT VERSION 2 FIXES
--------------------
1. Junk objects are left out. Version 1 kept anything with an oracle ID,
   which included tokens, emblems, art-series cards, gold-bordered
   memorabilia, minigame inserts and Arena-only digital cards. These cluttered
   search results (for example many "Spirit" and "Bird" tokens for 飛行).

2. Better Japanese text. Version 1 kept whichever Japanese printing happened
   to come first in the file, often an old printing with outdated wording
   (場に出る instead of 戦場に出る, etc.). Version 2 takes the newest paper
   Japanese printing, and fills in the rules text from the newest Japanese
   printing that actually has it.

3. Older Japanese names still match. Some cards were renamed in Japanese
   across reprints. Every distinct Japanese name a card has been printed under
   is kept, so searching an older name still finds the card.

4. Smaller file. The output is gzip-compressed (typically 5-10 MB instead of
   30+ MB), so it fits under GitHub's 25 MB browser-upload limit and loads
   faster. The site decompresses it in the browser.

5. A coverage check at the end looks up some well-known cards and prints
   whether each was found, plus totals, so you can see the result is complete.

6. (2.1) Better pictures. For the picture shown in search results, the
   Japanese printing Scryfall has a real scan of is preferred - a sharp scan
   over a low-resolution one - instead of the newest printing, which is
   sometimes only a placeholder. The Japanese name and text still come from
   the newest printing.

7. (2.2) Format legality: each card gets a short "legal" field (s=Standard,
   p=Pioneer, m=Modern, l=Legacy, v=Vintage, a=Pauper, c=Commander) so the
   site's advanced search can filter by format.

USAGE
-----
    python build_ja_database.py

Then upload ja_cards.json.gz to the same folder as index.html in your
GitHub repo. You can delete the old ja_cards.json (the site prefers the .gz
file when both exist). Re-run after new sets release.
"""

import gzip
import io
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date

BULK_DATA_ENDPOINT = "https://api.scryfall.com/bulk-data"
OUT_PATH = r"A:\Akuchie\ja_cards.json.gz"

# Scryfall requires every request to carry a real User-Agent identifying the
# calling app, plus an Accept header - requests missing either are rejected
# with 400 Bad Request:
# https://scryfall.com/docs/faqs/i-m-having-trouble-accessing-the-scryfall-api-or-i-m-blocked-17
HEADERS = {
    "User-Agent": "AkuchieJaCardDatabaseBuilder/2.0",
    "Accept": "application/json",
}

FIELD_ORDER = [
    "id", "oracle_id", "name_en", "name_ja", "type_en", "type_ja",
    "oracle_en", "oracle_ja", "mana_cost", "colors", "cmc",
    "power", "toughness", "rarity", "set", "keywords", "released_at",
    "alt_names_ja", "legal",
]

# Formats the site can filter by, one letter each in the row's "legal" field
# (a letter means legal or restricted there).
LEGAL_CODES = [("standard", "s"), ("pioneer", "p"), ("modern", "m"), ("legacy", "l"),
               ("vintage", "v"), ("pauper", "a"), ("commander", "c")]

# Card objects that aren't playable cards.
EXCLUDED_LAYOUTS = {
    "token", "double_faced_token", "emblem", "art_series",
    "vanguard", "planar", "scheme",
}
EXCLUDED_SET_TYPES = {"token", "memorabilia", "minigame", "alchemy"}

# Spot checks printed at the end: English name -> expected to have Japanese.
SPOT_CHECKS = [
    "Lightning Bolt", "Counterspell", "Slippery Bogle", "Ragavan, Nimble Pilferer",
    "Sheoldred, the Apocalypse", "The One Ring", "Orcish Bowmasters",
    "Fable of the Mirror-Breaker // Reflection of Kiki-Jiki", "Solitude",
    "Thoughtseize", "Llanowar Elves", "Black Lotus",
]


def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def get_bulk_cards_url():
    """Returns (url, is_jsonl) for the 'all_cards' export. Handles Scryfall's
    September 2026 switch from 'download_uri' (one JSON array) to
    'jsonl_download_uri' (gzipped JSON Lines)."""
    manifest = fetch_json(BULK_DATA_ENDPOINT)

    if not isinstance(manifest, dict) or "data" not in manifest:
        print("\nScryfall did not return the expected bulk-data list. Raw response:")
        print(json.dumps(manifest, indent=2, ensure_ascii=False)[:2000])
        raise RuntimeError("Unexpected response shape from Scryfall - see above.")

    for entry in manifest["data"]:
        if entry.get("type") == "all_cards":
            if "jsonl_download_uri" in entry:
                return entry["jsonl_download_uri"], True
            if "download_uri" in entry:
                return entry["download_uri"], False
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            raise RuntimeError("'all_cards' entry has no download link - see above.")

    print("Types present:", [e.get("type") for e in manifest["data"]])
    raise RuntimeError("No 'all_cards' entry in Scryfall's bulk-data manifest")


def iter_cards(url, is_jsonl):
    """Streams card objects one at a time, never holding the whole export
    (several GB uncompressed) in memory."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        if is_jsonl:
            with gzip.GzipFile(fileobj=resp) as gz:
                for raw_line in io.TextIOWrapper(gz, encoding="utf-8"):
                    line = raw_line.strip()
                    if line:
                        yield json.loads(line)
        else:
            for card in json.load(resp):
                yield card


def faces_of(card):
    return card.get("card_faces") or []


def joined(card, key):
    """Top-level field, or the faces' values joined with ' // ' for
    double-faced / split / adventure cards."""
    if card.get(key):
        return card[key]
    parts = [f.get(key) for f in faces_of(card) if f.get(key)]
    return " // ".join(parts)


def oracle_id_of(card):
    return card.get("oracle_id") or (faces_of(card)[0].get("oracle_id") if faces_of(card) else None)


def is_excluded(card):
    if card.get("layout") in EXCLUDED_LAYOUTS:
        return True
    if card.get("set_type") in EXCLUDED_SET_TYPES:
        return True
    if card.get("digital"):
        return True  # Arena/MTGO-only printings; paper printings are kept
    if card.get("type_line", "").startswith("Token"):
        return True
    return False


# Special printings (promos, Secret Lair, Mystical Archive-style showcases,
# etc.) often have a different rarity or no rules text, so a regular set
# printing is preferred as the card's representative when one exists.
SPECIAL_SET_TYPES = {
    "promo", "funny", "masterpiece", "box", "from_the_vault", "spellbook",
    "premium_deck", "arsenal", "treasure_chest",
}


def printing_rank(card):
    """Sort key for choosing a representative printing (higher is better):
    regular set over special printing, normal over variant, then newest."""
    special = bool(card.get("promo")) or card.get("set_type") in SPECIAL_SET_TYPES
    variant = bool(card.get("variation")) or bool(card.get("textless"))
    return (0 if special else 1, 0 if variant else 1, card.get("released_at", ""))


# How good Scryfall's picture of a printing is. "placeholder" is common for
# Japanese printings Scryfall has no scan of.
IMAGE_QUALITY = {"highres_scan": 3, "lowres": 2, "placeholder": 1, "missing": 0}


def picture_rank(card):
    """Sort key for choosing the printing whose picture is shown (higher is
    better): a real scan first, then the usual printing preferences, a sharp
    scan over a low-resolution one, then newest."""
    quality = IMAGE_QUALITY.get(card.get("image_status"), 1)
    regular, normal, released = printing_rank(card)
    return (1 if quality >= 2 else 0, regular, normal, quality, released)


class CardEntry:
    """Everything collected for one oracle card across all its printings."""
    __slots__ = ("en", "ja", "ja_pic", "ja_text", "ja_names", "first_released")

    def __init__(self):
        self.en = None          # best English printing
        self.ja = None          # best Japanese printing with a Japanese name
        self.ja_pic = None      # Japanese printing with the best picture
        self.ja_text = None     # best Japanese printing with Japanese rules text
        self.ja_names = set()   # every Japanese name seen
        self.first_released = None

    def add(self, card):
        released = card.get("released_at", "")
        if released and (self.first_released is None or released < self.first_released):
            self.first_released = released

        lang = card.get("lang")
        if lang == "en":
            if self.en is None or picture_rank(card) > picture_rank(self.en):
                self.en = card
        elif lang == "ja":
            name_ja = joined(card, "printed_name")
            if not name_ja:
                return
            self.ja_names.add(name_ja)
            if self.ja is None or printing_rank(card) > printing_rank(self.ja):
                self.ja = card
            if self.ja_pic is None or picture_rank(card) > picture_rank(self.ja_pic):
                self.ja_pic = card
            if joined(card, "printed_text"):
                if self.ja_text is None or printing_rank(card) > printing_rank(self.ja_text):
                    self.ja_text = card
        elif self.en is None and self.ja is None:
            # card that only exists in some other language - keep as a fallback
            self.en = card

    def to_row(self):
        base = self.ja or self.en
        en = self.en or base
        pic = self.ja_pic or base   # the printing whose picture the site shows
        faces = faces_of(base)
        name_ja = joined(self.ja, "printed_name") if self.ja else ""
        text_src = self.ja_text or self.ja
        row = {
            "id": pic.get("id", ""),
            "oracle_id": oracle_id_of(base) or "",
            "name_en": en.get("name", ""),
            "name_ja": name_ja,
            "type_en": en.get("type_line", "") or joined(en, "type_line"),
            "type_ja": joined(text_src, "printed_type_line") if text_src else "",
            "oracle_en": joined(en, "oracle_text"),
            "oracle_ja": joined(text_src, "printed_text") if text_src else "",
            "mana_cost": base.get("mana_cost") or (faces[0].get("mana_cost", "") if faces else ""),
            "colors": "".join(base.get("colors") or sorted({c for f in faces for c in f.get("colors", [])})),
            "cmc": base.get("cmc", 0),
            "power": base.get("power", faces[0].get("power") if faces else None),
            "toughness": base.get("toughness", faces[0].get("toughness") if faces else None),
            "rarity": pic.get("rarity", "") or base.get("rarity", ""),
            "set": pic.get("set", "") or base.get("set", ""),
            "keywords": ",".join(en.get("keywords", [])),
            "released_at": self.first_released or "",
            "alt_names_ja": "|".join(sorted(n for n in self.ja_names if n != name_ja)),
            "legal": "".join(code for fmt, code in LEGAL_CODES
                             if ((en.get("legalities") or base.get("legalities") or {}).get(fmt)) in ("legal", "restricted")),
        }
        return [row[f] for f in FIELD_ORDER]


def main():
    print("Fetching Scryfall bulk-data manifest...")
    url, is_jsonl = get_bulk_cards_url()
    print(f"Downloading Scryfall's full multi-language export (large, one-time):\n  {url}\n")

    entries = {}
    scanned = excluded = 0
    for card in iter_cards(url, is_jsonl):
        scanned += 1
        if scanned % 100000 == 0:
            print(f"  ...scanned {scanned:,} printings, {len(entries):,} cards so far")
        if is_excluded(card):
            excluded += 1
            continue
        oid = oracle_id_of(card)
        if not oid:
            excluded += 1
            continue
        entries.setdefault(oid, CardEntry()).add(card)

    rows = [e.to_row() for e in entries.values() if (e.ja or e.en)]
    rows.sort(key=lambda r: r[FIELD_ORDER.index("name_en")])
    with_ja = sum(1 for r in rows if r[FIELD_ORDER.index("name_ja")])
    with_ja_text = sum(1 for r in rows if r[FIELD_ORDER.index("oracle_ja")])

    payload = {
        "version": 2,
        "generated": date.today().isoformat(),
        "fields": FIELD_ORDER,
        "cards": rows,
    }
    os.makedirs(os.path.dirname(OUT_PATH) or ".", exist_ok=True)
    with gzip.open(OUT_PATH, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    size_mb = os.path.getsize(OUT_PATH) / (1024 * 1024)

    print(f"\nScanned {scanned:,} printings ({excluded:,} tokens/art cards/digital-only skipped).")
    print(f"Wrote {OUT_PATH}  ({size_mb:.1f} MB)")
    print(f"  {len(rows):,} cards total")
    print(f"    {with_ja:,} with a Japanese name")
    print(f"    {with_ja_text:,} with Japanese rules text")
    print(f"    {len(rows) - with_ja:,} English only (never printed in Japanese)")

    print("\nSpot check:")
    by_name = {r[FIELD_ORDER.index("name_en")]: r for r in rows}
    missing = 0
    for name in SPOT_CHECKS:
        r = by_name.get(name)
        if r is None:
            missing += 1
            print(f"  MISSING   {name}")
        else:
            ja = r[FIELD_ORDER.index("name_ja")] or "(English only)"
            print(f"  ok        {name}  ->  {ja}")
    if missing:
        print(f"\n{missing} spot-check card(s) missing - please share this output.")
    if size_mb > 25:
        print("\nNote: the file is over 25 MB, GitHub's browser-upload limit. "
              "Upload it with GitHub Desktop instead (limit 100 MB).")
    print("\nUpload ja_cards.json.gz next to index.html in your repo.")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)

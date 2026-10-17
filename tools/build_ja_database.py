#!/usr/bin/env python3
"""
build_ja_database.py  (version 2.5)

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

8. (2.3) Every rarity a card was printed at: the "rarities" field (c u r m s b)
   lists the rarities of its paper printings, promos and Secret Lair included,
   so the rarity filter finds a card by any of them, as Scryfall's r: does.
   Like Scryfall, it counts the English printing, or the printing's own
   language where there is no English one at that set and number
   (Renaissance, Japanese-only promos, Phyrexian). "rarity" stays the rarity
   of the printing shown.

9. (2.4) The fixes that used to be made by hand after a build are made by the
   builder, so a rebuild keeps them: a Japanese type line taken from another
   Japanese printing when the chosen one has none (888 cards), and a Japanese
   printing with a real scan chosen over one without, at the same rarity in a
   regular set (51 cards). Two new fields: "sets" (every set the card was
   printed in) and "treatments" (borderless, showcase... in any language,
   upper case where a Japanese printing has it). A second file,
   printings.json.gz, lists every printing (set and number) with its
   languages, rarity and treatments.

10. (2.5) A Japanese rules text or type line must have Japanese in it. Scryfall
   gives some Japanese printings the English text (most of Edge of Eternities);
   such a text is skipped for another Japanese printing's, or left empty, so
   the site translates the type and finds the card through its English text.

USAGE
-----
    python build_ja_database.py [--out ja_cards.json.gz] [--printings printings.json.gz]

GitHub rebuilds both files every week (.github/workflows/update-cards.yml,
tools/update_database.py), checks them and puts them on the test site.
"""

import argparse
import gzip
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date

BULK_DATA_ENDPOINT = "https://api.scryfall.com/bulk-data"
OUT_PATH = r"A:\Warujie\ja_cards.json.gz"
PRINTINGS_NAME = "printings.json.gz"   # written next to the card database unless --printings says where

# Scryfall requires every request to carry a real User-Agent identifying the
# calling app, plus an Accept header - requests missing either are rejected
# with 400 Bad Request:
# https://scryfall.com/docs/faqs/i-m-having-trouble-accessing-the-scryfall-api-or-i-m-blocked-17
HEADERS = {
    "User-Agent": "WarujieJaCardDatabaseBuilder/2.0",
    "Accept": "application/json",
}

FIELD_ORDER = [
    "id", "oracle_id", "name_en", "name_ja", "type_en", "type_ja",
    "oracle_en", "oracle_ja", "mana_cost", "colors", "cmc",
    "power", "toughness", "rarity", "set", "keywords", "released_at",
    "alt_names_ja", "legal", "layout", "rarities", "sets", "treatments",
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

# Rarities in the "rarities" field, one letter each, in this order.
RARITY_LETTERS = [("common", "c"), ("uncommon", "u"), ("rare", "r"), ("mythic", "m"),
                  ("special", "s"), ("bonus", "b")]

# Treatments the site searches by (ボーダーレス, ショーケース...), one letter each, in this order;
# the site's treatmentLabels() reads the same Scryfall fields for the card page.
TREATMENT_LETTERS = "bsxfouten"
JA_CHARS = re.compile("[\u3040-\u30ff\u3400-\u9fff]")

# The languages of the printings file, in the order the card page shows them.
PRINT_LANGS = ["en", "ja", "zhs", "zht", "ko", "fr", "de", "it", "es", "pt", "ru", "ph", "he", "la", "grc", "ar", "sa", "qya"]
# Sets whose other-language printings Scryfall files under a set code of their own, with the
# same collector numbers (the site's SET_TWIN): the Japanese 4th Edition (4bb) is the English 4ed's.
SET_TWIN = {"4bb": "4ed", "4ed": "4bb", "bchr": "chr", "chr": "bchr", "fbb": "3ed", "3ed": "fbb"}


def treatment_letters(card):
    """b borderless, s showcase, x extended art, f full art, o old frame (1993/1997),
    u future frame, t textless, e etched, n serialized."""
    fe = set(card.get("frame_effects") or [])
    finishes = card.get("finishes") or []
    found = {
        "b": card.get("border_color") == "borderless",
        "s": "showcase" in fe,
        "x": "extendedart" in fe,
        "f": bool(card.get("full_art")),
        "o": card.get("frame") in ("1993", "1997"),
        "u": card.get("frame") == "future",
        "t": bool(card.get("textless")),
        "e": "etched" in finishes or "etched" in fe,
        "n": "serialized" in (card.get("promo_types") or []),
    }
    return "".join(letter for letter in TREATMENT_LETTERS if found[letter])


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


# Card shapes the site searches by (分割カード, 両面カード, 出来事...): Scryfall's layout,
# empty for an ordinary one-faced card.
SHAPE_LAYOUTS = {
    "split", "transform", "modal_dfc", "meld", "flip", "adventure", "prepare", "saga",
    "class", "case", "leveler", "mutate", "prototype", "host", "augment",
}


def english_name(card):
    """Some Omen printings repeat the front: "Bloomvine Regent // Claim Territory //
    Bloomvine Regent". The repeat is dropped."""
    parts = card.get("name", "").split(" // ")
    if len(parts) > 2 and parts[-1] == parts[0]:
        parts = parts[:-1]
    return " // ".join(parts)


def layout_of(card):
    return card.get("layout") if card.get("layout") in SHAPE_LAYOUTS else ""


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


# Frame treatments of a variant printing (showcase, borderless...).
VARIANT_FRAMES = {"showcase", "extendedart", "inverted", "etched"}


def picture_rank(card):
    """Sort key for choosing the printing whose picture is shown (higher is
    better): a real scan first, then the usual printing preferences, a sharp
    scan over a low-resolution one, then newest; when all that is level, the
    ordinary frame over a showcase or borderless variant (Clarion Conqueror's
    #5, not #400)."""
    quality = IMAGE_QUALITY.get(card.get("image_status"), 1)
    regular, normal, released = printing_rank(card)
    plain = not (card.get("full_art") or card.get("border_color") == "borderless"
                 or VARIANT_FRAMES & set(card.get("frame_effects") or []))
    return (1 if quality >= 2 else 0, regular, normal, quality, released, plain)


class CardEntry:
    """Everything collected for one oracle card across all its printings."""
    __slots__ = ("en", "ja", "ja_pic", "ja_text", "ja_type", "ja_scans", "ja_names", "first_released",
                 "rarities", "en_numbers", "other_rarities", "sets", "treatments", "treatments_ja")

    def __init__(self):
        self.en = None          # best English printing
        self.ja = None          # best Japanese printing with a Japanese name
        self.ja_pic = None      # Japanese printing with the best picture
        self.ja_text = None     # best Japanese printing with Japanese rules text
        self.ja_names = set()   # every Japanese name seen
        self.first_released = None
        self.rarities = set()        # rarities of its English printings
        self.en_numbers = set()      # (set, number) of its English printings
        self.other_rarities = {}     # (set, number) -> rarities of other languages' printings
        self.ja_type = None          # best Japanese printing with a Japanese type line
        self.ja_scans = []           # Japanese printings Scryfall has a sharp scan of
        self.sets = {}               # set code -> its first release date for this card
        self.treatments = set()      # treatment letters of every printing
        self.treatments_ja = set()   # ... of the Japanese printings

    def add(self, card):
        released = card.get("released_at", "")
        if released and (self.first_released is None or released < self.first_released):
            self.first_released = released

        lang = card.get("lang")
        if card.get("set"):
            first = self.sets.get(card["set"])
            if first is None or released < first:
                self.sets[card["set"]] = released
        letters = treatment_letters(card)
        self.treatments.update(letters)
        if lang == "ja":
            self.treatments_ja.update(letters)
        # Scryfall's r: looks at the English printing, or the printing's own language
        # where that set and number has no English one: some Italian and Portuguese
        # printings carry a rarity their English one doesn't.
        number = (card.get("set"), card.get("collector_number"))
        if lang != "en":
            self.other_rarities.setdefault(number, set()).add(card.get("rarity"))
        if lang == "en":
            self.en_numbers.add(number)
            self.rarities.add(card.get("rarity"))
            # an English printing always replaces another language's kept as a fallback
            # (Italian Legends printings used to stay, ranked level with the English)
            if (self.en is None or self.en.get("lang") != "en"
                    or picture_rank(card) > picture_rank(self.en)):
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
            if JA_CHARS.search(joined(card, "printed_text")):
                if self.ja_text is None or printing_rank(card) > printing_rank(self.ja_text):
                    self.ja_text = card
            if JA_CHARS.search(joined(card, "printed_type_line")):
                if self.ja_type is None or printing_rank(card) > printing_rank(self.ja_type):
                    self.ja_type = card
            if card.get("image_status") == "highres_scan" and not card.get("oversized"):
                self.ja_scans.append(card)
        elif self.en is None and self.ja is None:
            # card that only exists in some other language - keep as a fallback
            self.en = card

    def all_rarities(self, shown):
        """Letters of every rarity counted for the card, the shown printing's included."""
        found = set(self.rarities) | {shown}
        for number, rarities in self.other_rarities.items():
            if number not in self.en_numbers:
                found |= rarities
        return "".join(letter for rarity, letter in RARITY_LETTERS if rarity in found)

    def picture(self):
        """The printing whose picture the site shows: the Japanese one picture_rank()
        prefers; when Scryfall has no sharp scan of it, a Japanese printing with one at the
        same rarity in a regular set (not a promo), plainest frame first, then newest."""
        pic = self.ja_pic
        if pic is None or pic.get("image_status") == "highres_scan":
            return pic
        good = [c for c in self.ja_scans if c.get("rarity") == pic.get("rarity")
                and not c.get("promo") and c.get("set_type") not in SPECIAL_SET_TYPES]
        if not good:
            return pic
        good.sort(key=lambda c: (bool(VARIANT_FRAMES & set(c.get("frame_effects") or [])), bool(c.get("full_art")),
                                 c.get("border_color") not in ("black", None), [-ord(ch) for ch in c.get("released_at", "")]))
        return good[0]

    def to_row(self):
        base = self.ja or self.en
        en = self.en or base
        pic = self.picture() or base   # the printing whose picture the site shows
        faces = faces_of(base)
        name_ja = joined(self.ja, "printed_name") if self.ja else ""
        text_src = self.ja_text or self.ja
        type_ja = joined(text_src, "printed_type_line") if text_src else ""
        if not JA_CHARS.search(type_ja):
            type_ja = joined(self.ja_type, "printed_type_line") if self.ja_type else ""
        row = {
            "id": pic.get("id", ""),
            "oracle_id": oracle_id_of(base) or "",
            "name_en": english_name(en),
            "name_ja": name_ja,
            "type_en": en.get("type_line", "") or joined(en, "type_line"),
            "type_ja": type_ja,
            "oracle_en": joined(en, "oracle_text"),
            "oracle_ja": joined(self.ja_text, "printed_text") if self.ja_text else "",
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
            "layout": layout_of(en),
            "rarities": self.all_rarities(pic.get("rarity", "") or base.get("rarity", "")),
            "sets": " ".join(sorted(self.sets, key=lambda code: (self.sets[code], code))),
            "treatments": "".join(letter for letter in TREATMENT_LETTERS if letter in self.treatments)
                          + "".join(letter.upper() for letter in TREATMENT_LETTERS if letter in self.treatments_ja),
            "legal": "".join(code for fmt, code in LEGAL_CODES
                             if ((en.get("legalities") or base.get("legalities") or {}).get(fmt)) in ("legal", "restricted")),
        }
        return [row[f] for f in FIELD_ORDER]


class Printings:
    """Every printing (set and collector number) with its languages, rarity and treatments,
    for printings.json.gz."""

    def __init__(self):
        self.by_number = {}   # (set, number) -> {"oracle", "langs", "rarity", "treatments"}

    def add(self, card, oracle_id):
        key = (card.get("set"), card.get("collector_number"))
        if not key[0] or not key[1]:
            return
        p = self.by_number.setdefault(key, {"oracle": oracle_id, "langs": set(), "rarity": "", "treatments": set()})
        lang = card.get("lang") or "en"
        p["langs"].add(lang)
        if card.get("rarity") and (lang == "en" or not p["rarity"]):
            p["rarity"] = card["rarity"]
        p["treatments"].update(treatment_letters(card))

    def payload(self):
        letter = dict(RARITY_LETTERS)
        sets = {}
        for (code, number), p in sorted(self.by_number.items()):
            langs = sorted(p["langs"], key=lambda l: (PRINT_LANGS.index(l) if l in PRINT_LANGS else 99, l))
            twin = SET_TWIN.get(code)
            other = self.by_number.get((twin, number)) if twin else None
            if other and other["oracle"] == p["oracle"]:
                langs += [f"{l}@{twin}" for l in sorted(other["langs"], key=lambda l: (PRINT_LANGS.index(l) if l in PRINT_LANGS else 99, l))
                          if l not in p["langs"]]
            sets.setdefault(code, {})[number] = [" ".join(langs), letter.get(p["rarity"], ""),
                                                  "".join(t for t in TREATMENT_LETTERS if t in p["treatments"])]
        return {"version": 1, "generated": date.today().isoformat(), "fields": ["langs", "rarity", "treatments"], "sets": sets}


def write_gz(path, payload):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as f:
            f.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def main():
    ap = argparse.ArgumentParser(description="Build the card database and the printings file from Scryfall's bulk data.")
    ap.add_argument("--out", default=OUT_PATH, help="where to write ja_cards.json.gz")
    ap.add_argument("--printings", help="where to write printings.json.gz (default: next to --out)")
    args = ap.parse_args()
    out_path = args.out
    printings_path = args.printings or os.path.join(os.path.dirname(out_path), PRINTINGS_NAME)
    print("Fetching Scryfall bulk-data manifest...")
    url, is_jsonl = get_bulk_cards_url()
    print(f"Downloading Scryfall's full multi-language export (large, one-time):\n  {url}\n")

    entries = {}
    printings = Printings()
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
        printings.add(card, oid)

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
    write_gz(out_path, payload)
    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    write_gz(printings_path, printings.payload())

    print(f"\nScanned {scanned:,} printings ({excluded:,} tokens/art cards/digital-only skipped).")
    print(f"Wrote {out_path}  ({size_mb:.1f} MB)")
    print(f"Wrote {printings_path}  ({os.path.getsize(printings_path) / (1024 * 1024):.1f} MB, {len(printings.by_number):,} printings)")
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
    print("\nUpload ja_cards.json.gz and printings.json.gz next to index.html in your repo.")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)

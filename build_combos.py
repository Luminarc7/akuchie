#!/usr/bin/env python3
"""
build_combos.py

Builds `combos_golgari.json.gz` - the data behind the combo suggestions of the
悪知恵 Golgari edition: for every green/black card, the known combos it is
part of, the other cards they need, and what they do.

WHERE THE COMBOS COME FROM
--------------------------
Commander Spellbook (https://commanderspellbook.com/), a community combo
database. It publishes every combo as one bulk file and asks other sites to
download that file on a schedule of their own instead of calling its API from
each visitor's browser - which is what this script does. The site credits
Commander Spellbook and links each combo back to its page there.

WHAT IS KEPT
------------
Combos whose colour identity is within the chosen colours (default: black
and green), so every one of them fits in a Golgari deck. Combos made only of
colourless cards are left out, since the Golgari edition has no pages for
colourless cards to show them on.

USAGE
-----
    python build_combos.py

Downloads the bulk file (large - give it a few minutes), then writes
combos_golgari.json.gz. Upload that file next to golgari.html. Run it again
now and then (once a week is plenty) to pick up new combos.

Options (all optional):
    --out PATH        where to write the result
    --colors BG       colour identity to keep
    --cache DIR       where the downloaded bulk file is kept
    --source PATH     use a variants.json(.gz) file you already have
"""

import argparse
import datetime
import gzip
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

BULK_URL = os.environ.get("AKUCHIE_COMBOS_URL", "https://json.commanderspellbook.com/variants.json.gz")
HEADERS = {"User-Agent": "AkuchieComboBuilder/1.0 (https://luminarc7.github.io/akuchie/)", "Accept": "application/json"}

# Formats shown as badges on the site, in the site's own order.
FORMAT_BITS = ["standard", "pioneer", "modern", "legacy", "vintage", "premodern", "commander", "pauper"]

FIELDS = ["id", "identity", "cards", "templates", "results", "mana", "popularity", "legal", "prerequisites", "steps"]
MAX_TEXT = 1500   # longest prerequisites / steps text kept per combo


def log(msg=""):
    print(msg, flush=True)


def pick(obj, *names, default=None):
    """First present key - the bulk file uses camelCase, older exports snake_case."""
    for name in names:
        if isinstance(obj, dict) and name in obj and obj[name] is not None:
            return obj[name]
    return default


# ------------------------------------------------------------- download

def download(url, dest):
    """Downloads url to dest (resumable only as a whole; skipped when the
    server says our copy is still current)."""
    etag_path = dest + ".etag"
    headers = dict(HEADERS)
    if os.path.exists(dest) and os.path.exists(etag_path):
        with open(etag_path, encoding="utf-8") as f:
            headers["If-None-Match"] = f.read().strip()
    delay = 3.0
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                done, last = 0, time.time()
                with open(dest + ".part", "wb") as out:
                    while True:
                        chunk = resp.read(1 << 20)
                        if not chunk:
                            break
                        out.write(chunk)
                        done += len(chunk)
                        if time.time() - last > 5:
                            last = time.time()
                            log(f"  ...{done / 1e6:,.0f} MB" + (f" of {total / 1e6:,.0f} MB" if total else ""))
                os.replace(dest + ".part", dest)
                etag = resp.headers.get("ETag")
                if etag:
                    with open(etag_path, "w", encoding="utf-8") as f:
                        f.write(etag)
                return
        except urllib.error.HTTPError as e:
            if e.code == 304:
                log("  the copy downloaded earlier is still current.")
                return
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(float(e.headers.get("Retry-After") or delay))
                delay *= 2
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt < 3:
                time.sleep(delay)
                delay *= 2
                continue
            raise


def open_text(path):
    """Opens a .json or .json.gz file as text, whatever its extension says."""
    f = open(path, "rb")
    magic = f.read(2)
    f.seek(0)
    if magic == b"\x1f\x8b":
        return io.TextIOWrapper(gzip.GzipFile(fileobj=f), encoding="utf-8")
    return io.TextIOWrapper(f, encoding="utf-8")


# -------------------------------------------------- streaming JSON reader

def iter_array(stream, key, chunk_size=1 << 20):
    """Yields the objects of the array stored under `key` in a big JSON
    document, one at a time, without loading the whole document (the bulk
    file is hundreds of megabytes once unpacked). Also returns nothing else
    of the document; see read_head for the small fields in front."""
    decoder = json.JSONDecoder()
    needle = '"%s"' % key
    buf = ""
    # 1. find the start of the array
    while True:
        i = buf.find(needle)
        if i >= 0:
            j = buf.find("[", i + len(needle))
            if j >= 0:
                buf = buf[j + 1:]
                break
            more = stream.read(chunk_size)
            if not more:
                return
            buf += more
            continue
        more = stream.read(chunk_size)
        if not more:
            return
        buf = buf[-len(needle):] + more
    # 2. decode one object after another
    pos = 0
    while True:
        while True:  # skip separators, reading more when the buffer runs out
            while pos < len(buf) and buf[pos] in " \t\r\n,":
                pos += 1
            if pos < len(buf):
                break
            more = stream.read(chunk_size)
            if not more:
                return
            buf, pos = more, 0
        if buf[pos] == "]":
            return
        try:
            obj, end = decoder.raw_decode(buf, pos)
        except ValueError:
            more = stream.read(chunk_size)
            if not more:
                raise ValueError("The combo file ends in the middle of a record - the download was probably cut short.")
            buf, pos = buf[pos:] + more, 0
            continue
        yield obj
        pos = end
        if pos > (1 << 22):   # drop what has been read
            buf, pos = buf[pos:], 0


def read_head(path, limit=4096):
    """The 'timestamp' the bulk file was built at, from its first bytes."""
    with open_text(path) as f:
        head = f.read(limit)
    marker = '"timestamp"'
    i = head.find(marker)
    if i < 0:
        return ""
    rest = head[i + len(marker):].lstrip(" :")
    try:
        value, _ = json.JSONDecoder().raw_decode(rest)
        return str(value)
    except ValueError:
        return ""


# -------------------------------------------------------------- building

def clean_text(text):
    text = (text or "").replace("\r\n", "\n").strip()
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT].rsplit("\n", 1)[0] + "\n…"
    return text


def build(source_path, colors):
    allowed = set(colors.upper())
    cards, card_index = [], {}        # [name, oracle id]
    results, result_index = [], {}    # feature names
    combos = []
    seen = kept = 0

    def card_ref(card):
        name = pick(card, "name", default="")
        oracle = pick(card, "oracleId", "oracle_id", default="") or ""
        key = oracle or name
        if key not in card_index:
            card_index[key] = len(cards)
            cards.append([name, oracle])
        return card_index[key]

    def result_ref(name):
        if name not in result_index:
            result_index[name] = len(results)
            results.append(name)
        return result_index[name]

    with open_text(source_path) as stream:
        for variant in iter_array(stream, "variants"):
            seen += 1
            if seen % 20000 == 0:
                log(f"  ...read {seen:,} combos, kept {kept:,}")
            if not isinstance(variant, dict):
                continue
            if pick(variant, "status", default="OK") not in ("OK", "E"):
                continue
            identity = str(pick(variant, "identity", default="C") or "C").upper()
            if identity == "C" or any(c not in allowed for c in identity):
                continue
            uses = pick(variant, "uses", default=[]) or []
            if not uses:
                continue
            used = []
            for u in uses:
                card = pick(u, "card", default={}) or {}
                if not pick(card, "name"):
                    continue
                zones = "".join(pick(u, "zoneLocations", "zone_locations", default=[]) or [])
                used.append([card_ref(card), int(pick(u, "quantity", default=1) or 1), zones])
            if not used:
                continue
            templates = []
            for r in pick(variant, "requires", default=[]) or []:
                name = pick(pick(r, "template", default={}) or {}, "name")
                if name:
                    qty = int(pick(r, "quantity", default=1) or 1)
                    templates.append(f"{qty}x {name}" if qty > 1 else name)
            produced = []
            for p in pick(variant, "produces", default=[]) or []:
                feature = pick(p, "feature", default={}) or {}
                name = pick(feature, "name")
                if not name or name.lower() == "lock" or pick(feature, "status") in ("HU", "PU"):
                    continue
                qty = int(pick(p, "quantity", default=1) or 1)
                produced.append(result_ref(f"{qty} {name}" if qty > 1 else name))
            legal = pick(variant, "legalities", default={}) or {}
            mask = sum(1 << i for i, fmt in enumerate(FORMAT_BITS) if legal.get(fmt))
            prerequisites = "\n".join(t for t in (
                clean_text(pick(variant, "notablePrerequisites", "notable_prerequisites", default="")),
                clean_text(pick(variant, "easyPrerequisites", "easy_prerequisites", default="")),
            ) if t)
            combos.append([
                str(pick(variant, "id", default="")),
                identity,
                used,
                templates,
                produced,
                pick(variant, "manaNeeded", "mana_needed", default="") or "",
                int(pick(variant, "popularity", default=0) or 0),
                mask,
                prerequisites,
                clean_text(pick(variant, "description", default="")),
            ])
            kept += 1

    combos.sort(key=lambda c: (-c[6], c[0]))   # most played first
    return seen, cards, results, combos


def default_out_path(colors):
    name = "combos_golgari.json.gz" if set(colors.upper()) == set("BG") else f"combos_{colors.lower()}.json.gz"
    folder = r"A:\Akuchie"
    return os.path.join(folder, name) if os.path.isdir(folder) else name


def main():
    ap = argparse.ArgumentParser(description="Build the combo data for the 悪知恵 Golgari edition.")
    ap.add_argument("--out", default=None)
    ap.add_argument("--colors", default="BG")
    ap.add_argument("--cache", default=None)
    ap.add_argument("--source", default=None)
    args = ap.parse_args()

    colors = "".join(c for c in "WUBRG" if c in args.colors.upper())
    if not colors:
        ap.error("--colors needs one or more of W, U, B, R, G - for example BG")
    out_path = args.out or default_out_path(colors)

    source = args.source
    if not source:
        cache = args.cache or os.path.join(os.path.dirname(os.path.abspath(out_path)), "combo_cache")
        os.makedirs(cache, exist_ok=True)
        source = os.path.join(cache, "variants.json.gz")
        log("Downloading the Commander Spellbook combo file (large, please wait)...")
        download(BULK_URL, source)

    log("Reading combos...")
    seen, cards, results, combos = build(source, colors)
    if not seen:
        raise RuntimeError("No combos could be read from the file - its layout may have changed. Nothing was written.")
    if not combos:
        raise RuntimeError(f"Read {seen:,} combos but none are within the colours {colors}. Nothing was written.")

    payload = {
        "version": 1,
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {"name": "Commander Spellbook", "url": "https://commanderspellbook.com/", "timestamp": read_head(source)},
        "colors": colors,
        "formats": FORMAT_BITS,
        "fields": FIELDS,
        "cards": cards,
        "results": results,
        "combos": combos,
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with gzip.open(out_path, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    log(f"\nRead {seen:,} combos; kept {len(combos):,} within {colors}, using {len(cards):,} different cards.")
    log(f"Wrote {out_path}  ({size_mb:.1f} MB)")
    log("\nMost played:")
    for combo in combos[:5]:
        names = " + ".join(cards[i][0] for i, _, _ in combo[2])
        does = ", ".join(results[i] for i in combo[4][:3]) or "?"
        log(f"  {names}  ->  {does}")
    if size_mb > 25:
        log("\nNote: the file is over 25 MB, GitHub's browser-upload limit. Upload it with GitHub Desktop instead.")
    log(f"\nUpload {os.path.basename(out_path)} next to golgari.html in your repo.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, urllib.error.URLError) as e:
        print(f"\nStopped: {e}", file=sys.stderr)
        sys.exit(1)

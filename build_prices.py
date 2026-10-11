#!/usr/bin/env python3
"""
build_prices.py - daily card price history for 悪知恵

Once a day this reads Scryfall's free 'default_cards' export (every printing,
with today's TCGplayer US-dollar prices), adds today's price of every printing
to the stored history, and writes:

    index.json         the list of dates in the history
    h/00.json.gz ...   the history itself, split into 256 files by card id
                       (the card page only loads the one file it needs)
    movers.json        biggest risers and fallers over 1, 7 and 30 days

Scryfall only ever gives today's price. So that charts and price movers work
from the start, a young history (under 60 days) is filled in with the last
90 days of TCGplayer prices from MTGJSON's free price archive
(https://mtgjson.com/downloads/all-files/) - a one-off download of a few
hundred MB; once the history is long enough this step is skipped. Daily
values are kept for the last 120 days; older history keeps one value a week
(Mondays), so the files stay small for years.

Usage (normally run by GitHub Actions - see update-prices.yml):
    python3 build_prices.py --out site --previous https://luminarc7.github.io/akuchie-prices/
    python3 build_prices.py --out site --previous <url> --allow-fresh   # very first run
    python3 build_prices.py --out site --previous site            # previous data in a folder
    python3 build_prices.py --out site --bulk cards.jsonl.gz      # test with a saved export
    python3 build_prices.py ... --backfill always    # fill in past prices from MTGJSON now
    python3 build_prices.py ... --backfill never     # never download MTGJSON's archive

Data: Scryfall (https://scryfall.com/docs/api/bulk-data). Prices are
TCGplayer market prices supplied through Scryfall; earlier days come from
MTGJSON's TCGplayer prices.
"""
import argparse
import gzip
import io
import json
import lzma
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

BULK_DATA_ENDPOINT = "https://api.scryfall.com/bulk-data"
HEADERS = {"User-Agent": "AkuchiePriceHistory/1.0", "Accept": "application/json"}

FORMAT_VERSION = 1
DAILY_DAYS = 120            # keep every day for this long, then weekly
WINDOWS = (1, 7, 30)        # movers: change over this many days
MOVERS_PER_LIST = 50
MIN_PRICE_CENTS = 200       # movers: the card must be worth at least $2 then or now ...
MIN_CHANGE_CENTS = 50       # ... and have moved by at least $0.50 (cheap cards jump around)
SCOPES = {"all": "", "GW": "GW", "BG": "BG"}   # main site, Selesnya and Golgari editions
COLOR_ORDER = "WUBRG"

MTGJSON_BASE = os.environ.get("AKUCHIE_MTGJSON_BASE", "https://mtgjson.com/api/v5/")
BACKFILL_IF_FEWER = 60      # auto: fill in past prices while the history has fewer dates than this
BACKFILL_DAYS = 90          # MTGJSON keeps 90 days
BACKFILL_RETRY_DAYS = 7     # auto: after a failed attempt, wait this long before downloading again

EXCLUDED_LAYOUTS = {"token", "double_faced_token", "emblem", "art_series", "vanguard", "planar", "scheme"}
EXCLUDED_SET_TYPES = {"token", "memorabilia", "minigame", "alchemy"}


# ------------------------------------------------------------------ download
def http_get(url, tries=4):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            return urllib.request.urlopen(req, timeout=120)
        except urllib.error.HTTPError as err:
            if err.code == 404:
                raise
            last = err
        except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
            last = err
        time.sleep(5 * (attempt + 1))
    raise last


def bulk_url():
    with http_get(BULK_DATA_ENDPOINT) as resp:
        manifest = json.load(resp)
    for entry in manifest.get("data", []):
        if entry.get("type") == "default_cards":
            if entry.get("jsonl_download_uri"):
                return entry["jsonl_download_uri"]
            if entry.get("download_uri"):
                return entry["download_uri"]
    raise RuntimeError("Scryfall's bulk-data list has no 'default_cards' download")


def iter_cards_from_stream(stream, name):
    """Cards from a JSON array or JSON Lines export, gzipped or not."""
    head = stream.peek(2)[:2] if hasattr(stream, "peek") else b""
    if head == b"\x1f\x8b" or name.endswith(".gz"):
        stream = gzip.GzipFile(fileobj=stream)
    text = io.TextIOWrapper(stream, encoding="utf-8")
    first = text.read(1)
    while first and first.isspace():
        first = text.read(1)
    if first == "[":
        for card in json.loads(first + text.read()):
            yield card
        return
    pending = first
    for line in text:
        line = (pending + line).strip()
        pending = ""
        if line:
            yield json.loads(line)


def iter_cards(source):
    if os.path.exists(source):
        with open(source, "rb") as fh:
            yield from iter_cards_from_stream(io.BufferedReader(fh), source)
    else:
        with http_get(source) as resp:
            yield from iter_cards_from_stream(io.BufferedReader(resp), source)


# ------------------------------------------------------------------ previous history
def read_previous(source, allow_fresh):
    """Returns (dates, {shard: {id: [usd, foil]}}, index). An empty history when
    nothing has been published yet. Any other failure stops the run, so a
    network hiccup can never wipe out the collected history."""
    def load(rel):
        if source.startswith(("http://", "https://")):
            url = source.rstrip("/") + "/" + rel
            try:
                with http_get(url) as resp:
                    raw = resp.read()
            except urllib.error.HTTPError as err:
                if err.code == 404:
                    return None
                raise
        else:
            path = os.path.join(source, rel)
            if not os.path.exists(path):
                return None
            with open(path, "rb") as fh:
                raw = fh.read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))

    if not source:
        return [], {}, {}
    index = load("index.json")
    if index is None:
        if not allow_fresh:
            raise SystemExit(f"No index.json at {source} - stopping so a published history is never replaced by an "
                             "empty one. On the very first run, pass --allow-fresh.")
        print("No earlier history found - starting a new one.")
        return [], {}, {}
    dates = index.get("dates", [])
    shards = {}
    for key in index.get("shards") or [f"{i:02x}" for i in range(256)]:
        data = load(f"h/{key}.json.gz")
        if data is None:
            print(f"  warning: h/{key}.json.gz is missing - that part starts again")
            continue
        # line the series up with the index's dates (they always match unless
        # an upload was interrupted half-way)
        own = data.get("dates", dates)
        if own == dates:
            shards[key] = data.get("p", {})
        else:
            pos = {d: n for n, d in enumerate(own)}
            shards[key] = {
                cid: [[s[pos[d]] if d in pos and pos[d] < len(s) else None for d in dates] for s in series]
                for cid, series in data.get("p", {}).items()
            }
    print(f"Earlier history: {len(dates)} dates, {sum(len(s) for s in shards.values())} printings")
    return dates, shards, index


# ------------------------------------------------------------------ past prices from MTGJSON
class _JsonStream:
    """Reads a huge JSON file piece by piece: the MTGJSON files are gigabytes
    once unpacked, far too big to load at once."""

    def __init__(self, text):
        self.text, self.buf, self.pos, self.eof = text, "", 0, False
        self.dec = json.JSONDecoder()

    def more(self):
        chunk = self.text.read(1 << 20)
        if not chunk:
            self.eof = True
            return False
        self.buf = self.buf[self.pos:] + chunk
        self.pos = 0
        return True

    def peek(self):
        while True:
            while self.pos < len(self.buf) and self.buf[self.pos] in " \t\r\n":
                self.pos += 1
            if self.pos < len(self.buf):
                return self.buf[self.pos]
            if not self.more():
                return ""

    def expect(self, ch):
        if self.peek() != ch:
            raise ValueError(f"unexpected content in the MTGJSON file (wanted {ch!r})")
        self.pos += 1

    def value(self):
        self.peek()
        while True:
            try:
                val, end = self.dec.raw_decode(self.buf, self.pos)
            except json.JSONDecodeError:
                if self.eof or not self.more():
                    raise
                continue
            if end >= len(self.buf) and not self.eof and self.more():
                continue   # a number at the very end might continue in the next piece
            self.pos = end
            return val


def mtgjson_items(source):
    """(key, value) for every entry of the top-level "data" object of an
    MTGJSON file (.json, .json.gz or .json.xz; a path or a URL)."""
    if source.startswith(("http://", "https://")):
        raw = http_get(source)
    else:
        raw = open(source, "rb")
    with raw:
        if source.endswith(".xz"):
            stream = lzma.open(raw)
        elif source.endswith(".gz"):
            stream = gzip.GzipFile(fileobj=raw)
        else:
            stream = raw
        reader = _JsonStream(io.TextIOWrapper(stream, encoding="utf-8"))
        reader.expect("{")
        while True:
            ch = reader.peek()
            if ch in ("}", ""):
                return
            if ch == ",":
                reader.pos += 1
                continue
            key = reader.value()
            reader.expect(":")
            if key != "data":
                reader.value()   # "meta": not needed
                continue
            reader.expect("{")
            while True:
                ch = reader.peek()
                if ch == "}":
                    reader.pos += 1
                    break
                if ch == ",":
                    reader.pos += 1
                    continue
                if ch == "":
                    raise ValueError("the MTGJSON file ended early")
                k = reader.value()
                reader.expect(":")
                yield k, reader.value()


def backfill(dates, shards, today, prices_src, ids_src):
    """Adds the days before the stored history (up to BACKFILL_DAYS back) from
    MTGJSON's TCGplayer prices. Stored values are never replaced."""
    print("Filling in past prices from MTGJSON...")
    scryfall_id = {}
    for uuid, card in mtgjson_items(ids_src):
        sid = ((card or {}).get("identifiers") or {}).get("scryfallId")
        if sid:
            scryfall_id[uuid] = sid
    print(f"  {len(scryfall_id)} MTGJSON printings matched to Scryfall")
    if not scryfall_id:
        raise ValueError("no Scryfall ids in MTGJSON's identifier file")

    have = set(dates)
    first = (date.fromisoformat(today) - timedelta(days=BACKFILL_DAYS)).isoformat()
    col = {}          # date -> column in the arrays below
    past = {}         # scryfall id -> [normal prices by column, foil prices by column]
    for uuid, formats in mtgjson_items(prices_src):
        sid = scryfall_id.get(uuid)
        if not sid:
            continue
        tcg = (((formats or {}).get("paper") or {}).get("tcgplayer") or {})
        if tcg.get("currency", "USD") != "USD":
            continue
        retail = tcg.get("retail") or {}
        for which, points in ((0, retail.get("normal")), (1, retail.get("foil") or retail.get("etched"))):
            for d, price in (points or {}).items():
                if d in have or d >= today or d < first:
                    continue
                c = cents(price)
                if c is None:
                    continue
                k = col.get(d)
                if k is None:
                    k = col[d] = len(col)
                series = past.get(sid)
                if series is None:
                    series = past[sid] = [[], []]
                row = series[which]
                if len(row) <= k:
                    row.extend([None] * (k + 1 - len(row)))
                if row[k] is None:
                    row[k] = c
    if not col:
        print("  MTGJSON had no earlier days to add.")
        return dates, shards

    merged = sorted(have | set(col))
    old_pos = {d: i for i, d in enumerate(dates)}
    n = len(merged)
    for shard in shards.values():
        for cid, series in shard.items():
            shard[cid] = [[s[old_pos[d]] if d in old_pos and old_pos[d] < len(s) else None for d in merged] for s in series]
    where = [(merged.index(d), k) for d, k in col.items()]
    added = 0
    for sid, (normal, foil) in past.items():
        shard = shards.setdefault(sid[:2], {})
        series = shard.get(sid)
        if series is None:
            series = shard[sid] = [[None] * n, [None] * n]
            added += 1
        for m, k in where:
            if k < len(normal) and normal[k] is not None and series[0][m] is None:
                series[0][m] = normal[k]
            if k < len(foil) and foil[k] is not None and series[1][m] is None:
                series[1][m] = foil[k]
    print(f"  added {len(col)} earlier days ({min(col)} - {max(col)}) for {len(past)} printings ({added} new)")
    return merged, shards


# ------------------------------------------------------------------ cards
def faces(card):
    return card.get("card_faces") or []


def excluded(card):
    if card.get("layout") in EXCLUDED_LAYOUTS or card.get("set_type") in EXCLUDED_SET_TYPES:
        return True
    if card.get("digital") or "paper" not in (card.get("games") or ["paper"]):
        return True
    return card.get("type_line", "").startswith("Token")


def cents(value):
    try:
        return int(round(float(value) * 100)) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def colors_of(card):
    cols = set(card.get("colors") or [])
    for f in faces(card):
        cols.update(f.get("colors") or [])
    return "".join(c for c in COLOR_ORDER if c in cols)


def small_image(card):
    if card.get("image_uris"):
        return card["image_uris"].get("small", "")
    for f in faces(card):
        if f.get("image_uris"):
            return f["image_uris"].get("small", "")
    return ""


# ------------------------------------------------------------------ main work
def build(args):
    today = args.date or datetime.now(timezone.utc).date().isoformat()
    dates, shards, index = read_previous(args.previous, args.allow_fresh)

    # a young history: fill in the days before it from MTGJSON (once)
    tried = index.get("backfill_tried", "")
    sources = list(index.get("sources") or ["Scryfall (TCGplayer market prices, USD)"])
    wait_over = not tried or (date.fromisoformat(today) - date.fromisoformat(tried)).days >= BACKFILL_RETRY_DAYS
    if args.backfill == "always" or (args.backfill == "auto" and len(dates) < BACKFILL_IF_FEWER and wait_over):
        tried = today
        try:
            dates, shards = backfill(dates, shards, today,
                                     args.mtgjson_prices or MTGJSON_BASE + "AllPrices.json.xz",
                                     args.mtgjson_ids or MTGJSON_BASE + "AllIdentifiers.json.xz")
            mtgjson = "MTGJSON (TCGplayer prices, USD; earlier days)"
            if mtgjson not in sources:
                sources.append(mtgjson)
        except Exception as err:   # the daily update must go on without it
            print(f"  note: past prices could not be added from MTGJSON ({err}); carrying on without them.")

    if today in dates:
        idx = dates.index(today)
        print(f"{today} is already in the history - replacing that day's prices.")
    else:
        if dates and today < dates[-1]:
            raise SystemExit(f"Today ({today}) is earlier than the newest stored date ({dates[-1]}).")
        dates.append(today)
        idx = len(dates) - 1
        for shard in shards.values():
            for series in shard.values():
                for s in series:
                    s.append(None)
    n_dates = len(dates)
    for shard in shards.values():   # every series exactly as long as the date list
        for series in shard.values():
            for s in series:
                del s[n_dates:]
                s.extend([None] * (n_dates - len(s)))

    source = args.bulk or bulk_url()
    print("Reading", source)
    info = {}
    seen = priced = 0
    for card in iter_cards(source):
        seen += 1
        if card.get("lang", "en") != "en":
            continue
        p = card.get("prices") or {}
        usd = cents(p.get("usd"))
        foil = cents(p.get("usd_foil"))
        if foil is None:
            foil = cents(p.get("usd_etched"))
        if usd is None and foil is None:
            continue
        cid = card["id"]
        shard = shards.setdefault(cid[:2], {})
        series = shard.get(cid)
        if series is None:
            series = shard[cid] = [[None] * n_dates, [None] * n_dates]
        series[0][idx] = usd
        series[1][idx] = foil
        priced += 1
        if not excluded(card):
            info[cid] = {
                "o": card.get("oracle_id") or (faces(card)[0].get("oracle_id") if faces(card) else ""),
                "n": card.get("name", ""),
                "s": card.get("set", ""),
                "sn": card.get("set_name", ""),
                "c": card.get("collector_number", ""),
                "r": card.get("rarity", ""),
                "col": colors_of(card),
                "img": small_image(card),
            }
    print(f"{seen} printings read, {priced} with a price")
    if priced < args.min_cards:
        raise SystemExit(f"Only {priced} priced printings - Scryfall's export looks incomplete, so nothing was changed.")

    # older than DAILY_DAYS: keep Mondays only
    cutoff = (date.fromisoformat(today) - timedelta(days=DAILY_DAYS)).isoformat()
    keep = [i for i, d in enumerate(dates) if d >= cutoff or date.fromisoformat(d).weekday() == 0]
    if len(keep) < len(dates):
        dates = [dates[i] for i in keep]
        for shard in shards.values():
            for cid, series in shard.items():
                shard[cid] = [[s[i] for i in keep] for s in series]
        idx = len(dates) - 1
    # printings with no price on any stored date are dropped
    for shard in shards.values():
        for cid in [cid for cid, series in shard.items() if all(v is None for s in series for v in s)]:
            del shard[cid]

    write_output(args.out, today, dates, shards, movers(today, dates, shards, info), sources, tried)


def movers(today, dates, shards, info):
    idx = len(dates) - 1
    t = date.fromisoformat(today)
    result = {}
    for days in WINDOWS:
        target = t - timedelta(days=days)
        slack = timedelta(days=days // 2 + 2)
        j = None
        for k in range(idx - 1, -1, -1):
            d = date.fromisoformat(dates[k])
            if d <= target:
                if d >= target - slack:
                    j = k
                break
        if j is None:
            continue
        best = {}   # oracle id -> entry (one printing per card: the biggest move)
        for shard in shards.values():
            for cid, (usd, foil) in shard.items():
                meta = info.get(cid)
                if not meta:
                    continue
                series, is_foil = (usd, 0) if usd[idx] is not None else (foil, 1)
                now, then = series[idx], series[j]
                if now is None or then is None or then <= 0:
                    continue
                if max(now, then) < MIN_PRICE_CENTS or abs(now - then) < MIN_CHANGE_CENTS:
                    continue
                pct = (now - then) / then * 100
                key = meta["o"] or cid
                old = best.get(key)
                if old is None or abs(pct) > abs(old["pct"]):
                    best[key] = dict(meta, id=cid, f=is_foil, now=now, then=then, pct=round(pct, 1))
        entries = list(best.values())
        block = {"from": dates[j]}
        for scope, colors in SCOPES.items():
            inside = [e for e in entries if not colors or (e["col"] and all(c in colors for c in e["col"]))]
            up = sorted((e for e in inside if e["pct"] > 0), key=lambda e: (-e["pct"], -e["now"]))[:MOVERS_PER_LIST]
            down = sorted((e for e in inside if e["pct"] < 0), key=lambda e: (e["pct"], -e["then"]))[:MOVERS_PER_LIST]
            block[scope] = {"up": up, "down": down}
        result[str(days)] = block
    return result


def write_output(out, today, dates, shards, mover_data, sources=None, backfill_tried=""):
    os.makedirs(os.path.join(out, "h"), exist_ok=True)
    total = 0
    keys = sorted(set(f"{i:02x}" for i in range(256)) | set(shards))   # Scryfall ids are hex, so normally just the 256
    for key in keys:
        payload = json.dumps({"dates": dates, "p": shards.get(key, {})}, separators=(",", ":")).encode("utf-8")
        with open(os.path.join(out, "h", f"{key}.json.gz"), "wb") as fh:
            with gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
                gz.write(payload)
        total += os.path.getsize(os.path.join(out, "h", f"{key}.json.gz"))
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as fh:
        meta = {"version": FORMAT_VERSION, "updated": stamp, "today": today, "dates": dates, "shards": keys,
                "source": "Scryfall (TCGplayer market prices, USD)",
                "sources": sources or ["Scryfall (TCGplayer market prices, USD)"]}
        if backfill_tried:
            meta["backfill_tried"] = backfill_tried
        json.dump(meta, fh, separators=(",", ":"))
    with open(os.path.join(out, "movers.json"), "w", encoding="utf-8") as fh:
        json.dump({"version": FORMAT_VERSION, "updated": stamp, "today": today, "windows": mover_data},
                  fh, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(out, ".nojekyll"), "w") as fh:
        fh.write("")
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write("<!doctype html><meta charset='utf-8'><title>悪知恵 price data</title>"
                 "<p>Price history data for 悪知恵. Prices: TCGplayer via "
                 "<a href='https://scryfall.com'>Scryfall</a>; earlier days via "
                 "<a href='https://mtgjson.com'>MTGJSON</a>.</p>")
    print(f"Wrote {len(dates)} dates, {sum(len(s) for s in shards.values())} printings, "
          f"{total / 1e6:.1f} MB of history; movers for {', '.join(mover_data) or 'no windows yet'} day(s)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="folder to write the published files into")
    ap.add_argument("--previous", default="", help="URL or folder of the currently published data")
    ap.add_argument("--bulk", default="", help="a saved Scryfall export to read instead of downloading")
    ap.add_argument("--date", default="", help="the date to store prices under (YYYY-MM-DD, default today UTC)")
    ap.add_argument("--allow-fresh", action="store_true", help="start a new history if none is published yet (first run)")
    ap.add_argument("--min-cards", type=int, default=20000, help="refuse to save if fewer priced printings than this")
    ap.add_argument("--backfill", choices=("auto", "always", "never"), default="auto",
                    help="fill in past prices from MTGJSON: auto = while the history is under 60 days")
    ap.add_argument("--mtgjson-prices", default="", help="a saved AllPrices.json(.xz/.gz) to use instead of downloading")
    ap.add_argument("--mtgjson-ids", default="", help="a saved AllIdentifiers.json(.xz/.gz) to use instead of downloading")
    build(ap.parse_args())


if __name__ == "__main__":
    main()

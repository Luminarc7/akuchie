#!/usr/bin/env python3
"""
build_meta.py

Builds `meta.json` - the data behind the metagame tab of the 悪知恵 site:
for each format, which decks are being played (share of the field) and how
they are doing (match win rate) - and `meta_decks.json`, the deck lists
behind each deck's own page (one real list per deck, the best finish in the
period, with how often each card is played across all lists of that deck).

WHERE THE NUMBERS COME FROM
---------------------------
* Tournament results: the community-maintained MTGODecklistCache archive
  (https://github.com/Jiliac/MTGODecklistCache) - decklists and match results
  from Magic Online events and paper events run on Melee.
* Deck names: the community archetype rules in MTGOFormatData
  (https://github.com/Badaro/MTGOFormatData), applied the same way the
  MTGOArchetypeParser tool applies them.

Nothing is scraped from any website by this script; it only reads those two
public GitHub repositories.

HOW THE NUMBERS ARE WORKED OUT
------------------------------
* Share = decks of that archetype / all decks, in events of the last N days
  (Magic Online leagues are left out: they only publish 5-0 lists).
* Win rate = match wins / (wins + losses), counted only from events that
  publish every match (mostly Melee events, plus Magic Online top-8 matches).
  Mirror matches, byes and draws are left out. An archetype's win rate is only
  as reliable as its number of matches, which is stored next to it.
* Decks the rules do not recognise are grouped by colour and flagged as
  unclassified.

USAGE
-----
    python build_meta.py

The first run downloads a few months of tournament files (100-200 MB) into a
cache folder; later runs only fetch what is new. Then upload meta.json and
meta_decks.json next to index.html. Run it again whenever you want fresher
numbers - or let GitHub run it for you every day with the workflow file that
comes with this script.

Options (all optional):
    --out PATH          where to write meta.json
    --decks-out PATH    where to write meta_decks.json (default: next to meta.json)
    --cache DIR         where downloaded files are kept
    --days 30,90        time windows to calculate
    --decklists DIR     use an existing copy of MTGODecklistCache
    --formatdata DIR    use an existing copy of MTGOFormatData
    --cards PATH        the site's card database (ja_cards.json.gz), used to
                        keep lands out of each deck's "key cards"; found
                        automatically when it sits next to meta.json
    --no-git            download over plain HTTPS even if git is installed
"""

import argparse
import collections
import concurrent.futures
import datetime
import gzip
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

DECKLIST_REPO = "Jiliac/MTGODecklistCache"
FORMATDATA_REPO = "Badaro/MTGOFormatData"

# Base addresses (overridable for testing).
GITHUB_BASE = os.environ.get("AKUCHIE_GITHUB_BASE", "https://github.com")
API_BASE = os.environ.get("AKUCHIE_API_BASE", "https://api.github.com")
RAW_BASE = os.environ.get("AKUCHIE_RAW_BASE", "https://raw.githubusercontent.com")
CODELOAD_BASE = os.environ.get("AKUCHIE_CODELOAD_BASE", "https://codeload.github.com")

HEADERS = {"User-Agent": "AkuchieMetaBuilder/1.0", "Accept": "application/json"}

FORMATS = ["Standard", "Pioneer", "Modern", "Legacy", "Vintage", "Pauper"]
SOURCES = ["melee.gg", "mtgo.com_limited_data"]
DEFAULT_WINDOWS = [30, 90]

MIN_DECKS_PER_EVENT = 8      # ignore tiny events
MIN_MAINBOARD = 60           # ignore incomplete decklists
MAX_ARCHETYPES = 40          # per format; the rest is summed into one line
KEY_CARDS = 8                # with the card database (lands filtered out here)
KEY_CARDS_NO_DB = 14         # without it: send more, the site filters lands itself
KEY_CARD_PRESENCE = 0.4      # a key card is in at least 40% of the lists
MORE_PRESENCE = 0.25         # deck page: other cards played in at least 25% of the lists...
MORE_CARDS = 12              # ...at most this many of them


# ---------------------------------------------------------------- utilities

def log(msg=""):
    print(msg, flush=True)


def loads_lenient(text):
    """The archetype files are hand-written and a few have trailing commas or
    unquoted keys, which the original (C#) tool accepts. Accept them too."""
    text = text.lstrip("\ufeff")
    try:
        return json.loads(text)
    except ValueError:
        pass
    fixed = re.sub(r",(\s*[}\]])", r"\1", text)
    try:
        return json.loads(fixed)
    except ValueError:
        pass
    fixed = re.sub(r'([{,]\s*)([A-Za-z_]\w*)(\s*:)', r'\1"\2"\3', fixed)
    return json.loads(fixed)


def http_get(url, accept=None, token=None, retries=5):
    """GET with polite retries. Returns bytes."""
    headers = dict(HEADERS)
    if accept:
        headers["Accept"] = accept
    host = urllib.parse.urlparse(url).netloc.lower()
    if token and (host.endswith("github.com") or host.endswith("githubusercontent.com")):
        headers["Authorization"] = "Bearer " + token
    delay = 2.0
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and e.headers.get("X-RateLimit-Remaining") == "0":
                reset = int(e.headers.get("X-RateLimit-Reset") or 0)
                wait_min = max(1, int((reset - time.time()) / 60) + 1)
                raise RuntimeError(
                    "GitHub's hourly limit for anonymous downloads was reached. "
                    f"Run the script again in about {wait_min} minutes - files already "
                    "downloaded are kept, so it continues where it stopped."
                ) from e
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                wait = float(e.headers.get("Retry-After") or delay)
                time.sleep(min(wait, 120))
                delay *= 2
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise


def month_list(start, end):
    """(year, month) pairs covering start..end inclusive."""
    out = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


# ------------------------------------------------------ download: with git

def git_available():
    try:
        subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def run_git(args, cwd=None):
    env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1", GIT_TERMINAL_PROMPT="0")
    # core.longpaths: some tournament file names are long enough to trip Windows' 260-character limit
    proc = subprocess.run(["git", "-c", "core.longpaths=true"] + args, cwd=cwd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:3])} failed:\n{proc.stdout[-1500:]}")
    return proc.stdout


def is_our_clone(path, repo):
    if not os.path.isdir(os.path.join(path, ".git")):
        return False
    try:
        url = run_git(["remote", "get-url", "origin"], cwd=path).strip().lower()
    except RuntimeError:
        return False
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url.endswith("/" + repo.lower())


def git_sync(repo, dest, sparse_dirs=None):
    """Shallow clone (or update) of a public repo. With sparse_dirs, only
    those folders' files are downloaded."""
    url = f"{GITHUB_BASE}/{repo}"
    if os.path.exists(dest) and not is_our_clone(dest, repo):
        if os.listdir(dest):
            raise RuntimeError(f"{dest} exists but is not a copy of {repo}; move it away or pick another --cache folder.")
        os.rmdir(dest)
    if not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        args = ["clone", "--depth", "1"]
        if sparse_dirs is not None:
            args += ["--filter=blob:none", "--sparse"]
        run_git(args + [url, dest])
    else:
        run_git(["fetch", "--depth", "1", "origin", "HEAD"], cwd=dest)
        run_git(["reset", "--hard", "FETCH_HEAD"], cwd=dest)
    if sparse_dirs is not None:
        run_git(["sparse-checkout", "set"] + list(sparse_dirs), cwd=dest)


def fetch_with_git(cache, months):
    decklists = os.path.join(cache, "git", "MTGODecklistCache")
    formatdata = os.path.join(cache, "git", "MTGOFormatData")
    dirs = [f"Tournaments/{src}/{y:04d}/{m:02d}" for src in SOURCES for (y, m) in months]
    log("Downloading tournament results with git (first run takes a few minutes)...")
    git_sync(DECKLIST_REPO, decklists, dirs)
    log("Downloading archetype rules...")
    git_sync(FORMATDATA_REPO, formatdata)
    return decklists, formatdata


# ---------------------------------------------- download: plain HTTPS

def git_blob_sha(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def cache_path(root, rel, sha):
    """Where a tournament file is kept locally: same date folders, but a short
    file name (Windows limits whole paths to 260 characters)."""
    folder, name = rel.rsplit("/", 1)
    stem = name[:-5] if name.endswith(".json") else name
    short = re.sub(r"[^A-Za-z0-9._-]+", "_", stem)[:40]
    return os.path.join(root, *folder.split("/"), f"{short}-{sha[:10]}.json")


def api_json(path, token):
    return json.loads(http_get(f"{API_BASE}{path}", accept="application/vnd.github+json", token=token))


def tree_children(repo, sha, token, recursive=False):
    data = api_json(f"/repos/{repo}/git/trees/{sha}" + ("?recursive=1" if recursive else ""), token)
    if data.get("truncated"):
        log("  note: GitHub shortened a file listing; some events may be missing.")
    return data.get("tree") or []


def fetch_with_http(cache, months, token):
    root = os.path.join(cache, "http")
    decklists = os.path.join(root, "MTGODecklistCache")
    formatdata = os.path.join(root, "MTGOFormatData")

    # --- archetype rules: one zip download
    log("Downloading archetype rules...")
    branch = api_json(f"/repos/{FORMATDATA_REPO}", token).get("default_branch") or "main"
    blob = http_get(f"{CODELOAD_BASE}/{FORMATDATA_REPO}/zip/refs/heads/{branch}", accept="application/zip", token=token)
    tmp = formatdata + ".new"
    shutil.rmtree(tmp, ignore_errors=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        for info in zf.infolist():
            parts = info.filename.split("/", 1)
            if len(parts) < 2 or not parts[1] or info.is_dir():
                continue
            target = os.path.normpath(os.path.join(tmp, parts[1]))
            if not target.startswith(os.path.normpath(tmp) + os.sep):
                continue  # never write outside the folder
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as f:
                f.write(zf.read(info))
    shutil.rmtree(formatdata, ignore_errors=True)
    os.replace(tmp, formatdata)

    # --- tournament files: list the months we need, download what is missing
    log("Listing tournament files...")
    branch = api_json(f"/repos/{DECKLIST_REPO}", token).get("default_branch") or "master"

    def child(entries, name):
        for e in entries:
            if e.get("path") == name and e.get("type") == "tree":
                return e["sha"]
        return None

    top = tree_children(DECKLIST_REPO, branch, token)
    tournaments_sha = child(top, "Tournaments")
    if not tournaments_sha:
        raise RuntimeError("The tournament archive no longer has a 'Tournaments' folder - its layout has changed.")
    source_entries = tree_children(DECKLIST_REPO, tournaments_sha, token)
    wanted = []  # (relative path, sha)
    for src in SOURCES:
        src_sha = child(source_entries, src)
        if not src_sha:
            log(f"  note: source '{src}' is missing from the archive.")
            continue
        year_entries = tree_children(DECKLIST_REPO, src_sha, token)
        month_cache = {}
        for (y, m) in months:
            y_sha = child(year_entries, f"{y:04d}")
            if not y_sha:
                continue
            if y not in month_cache:
                month_cache[y] = tree_children(DECKLIST_REPO, y_sha, token)
            m_sha = child(month_cache[y], f"{m:02d}")
            if not m_sha:
                continue
            for e in tree_children(DECKLIST_REPO, m_sha, token, recursive=True):
                if e.get("type") == "blob" and e["path"].endswith(".json"):
                    wanted.append((f"Tournaments/{src}/{y:04d}/{m:02d}/{e['path']}", e["sha"]))

    def needs_download(item):
        rel, sha = item
        path = cache_path(decklists, rel, sha)
        if not os.path.exists(path):
            return True
        with open(path, "rb") as f:
            return git_blob_sha(f.read()) != sha

    todo = [w for w in wanted if needs_download(w)]
    log(f"  {len(wanted):,} tournament files in range, {len(todo):,} to download.")

    def download(item):
        rel, sha = item
        url = f"{RAW_BASE}/{DECKLIST_REPO}/{branch}/" + urllib.parse.quote(rel)
        data = http_get(url, accept="*/*", token=token)
        path = cache_path(decklists, rel, sha)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + ".part", "wb") as f:
            f.write(data)
        os.replace(path + ".part", path)

    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for _ in pool.map(download, todo):
            done += 1
            if done % 100 == 0:
                log(f"  ...{done:,} / {len(todo):,}")

    # Forget cached files that are no longer listed (renamed or removed upstream).
    keep = {os.path.normpath(cache_path(decklists, rel, sha)) for rel, sha in wanted}
    wanted_months = {(src, f"{y:04d}", f"{m:02d}") for src in SOURCES for (y, m) in months}
    for src, y, m in wanted_months:
        folder = os.path.join(decklists, "Tournaments", src, y, m)
        for dirpath, _, files in os.walk(folder):
            for name in files:
                full = os.path.normpath(os.path.join(dirpath, name))
                if name.endswith(".json") and full not in keep:
                    os.remove(full)
    return decklists, formatdata


# ------------------------------------------------------- archetype rules

COLOR_NAMES = {
    "W": "MonoWhite", "U": "MonoBlue", "B": "MonoBlack", "R": "MonoRed", "G": "MonoGreen",
    "WU": "Azorius", "WB": "Orzhov", "WR": "Boros", "WG": "Selesnya", "UB": "Dimir",
    "UR": "Izzet", "UG": "Simic", "BR": "Rakdos", "BG": "Golgari", "RG": "Gruul",
    "WUB": "Esper", "WUR": "Jeskai", "WUG": "Bant", "WBR": "Mardu", "WBG": "Abzan",
    "WRG": "Naya", "UBR": "Grixis", "UBG": "Sultai", "URG": "Temur", "BRG": "Jund",
    "WUBR": "WUBR", "WBRG": "WBRG", "WUBG": "WUBG", "WURG": "WURG", "UBRG": "UBRG",
    "WUBRG": "5Color",
}
_PASCAL_SPLIT = re.compile(r"(?<=[A-Z])(?=[A-Z][a-z])|(?<=[^A-Z])(?=[A-Z])|(?<=[A-Za-z])(?=[^A-Za-z])")


def spaced(name):
    return re.sub(r"\s+", " ", _PASCAL_SPLIT.sub(" ", name)).strip()


def archetype_name(arch, color):
    name = (arch.get("Name") or "").replace("Generic", "")
    if arch.get("IncludeColorInName"):
        name = COLOR_NAMES.get(color, "") + name
    return spaced(name)


def color_label(color):
    return spaced(COLOR_NAMES.get(color, "")) or "Colorless"


class FormatRules:
    def __init__(self, formats_dir, name):
        self.name = name
        self.lands, self.nonlands = {}, {}
        for path in (os.path.join(formats_dir, "card_colors.json"),
                     os.path.join(formats_dir, name, "color_overrides.json")):
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8-sig") as f:
                data = loads_lenient(f.read())
            for card in data.get("Lands") or []:
                self.lands[card["Name"]] = card["Color"]
            for card in data.get("NonLands") or []:
                self.nonlands[card["Name"]] = card["Color"]
        self.specific = self._load_folder(os.path.join(formats_dir, name, "Archetypes"), "Conditions")
        self.fallbacks = self._load_folder(os.path.join(formats_dir, name, "Fallbacks"), "CommonCards")
        for fb in self.fallbacks:
            fb["_set"] = set(fb["CommonCards"])

    @staticmethod
    def _load_folder(folder, required_key):
        out = []
        if not os.path.isdir(folder):
            return out
        for fname in sorted(os.listdir(folder)):
            if not fname.lower().endswith(".json"):
                continue
            try:
                with open(os.path.join(folder, fname), encoding="utf-8-sig") as f:
                    data = loads_lenient(f.read())
            except ValueError:
                log(f"  note: could not read archetype file {fname}; skipped.")
                continue
            if data.get(required_key):
                out.append(data)
        return out

    def colors(self, main, side):
        in_lands, in_spells = collections.Counter(), collections.Counter()
        for board in (main, side):
            for name, count in board.items():
                for c in self.lands.get(name, ""):
                    in_lands[c] += count
                for c in self.nonlands.get(name, ""):
                    in_spells[c] += count
        return "".join(c for c in "WUBRG" if in_lands[c] > 0 and in_spells[c] > 0) or "C"

    @staticmethod
    def _matches(main, side, arch):
        for cond in arch.get("Conditions") or []:
            cards = cond.get("Cards") or []
            if not cards:
                continue
            kind = (cond.get("Type") or "").lower()
            first = cards[0]
            distinct = set(cards)
            if kind == "inmainboard":
                ok = first in main
            elif kind == "insideboard":
                ok = first in side
            elif kind == "inmainorsideboard":
                ok = first in main or first in side
            elif kind == "oneormoreinmainboard":
                ok = any(c in main for c in distinct)
            elif kind == "oneormoreinsideboard":
                ok = any(c in side for c in distinct)
            elif kind == "oneormoreinmainorsideboard":
                ok = any(c in main or c in side for c in distinct)
            elif kind == "twoormoreinmainboard":
                ok = sum(1 for c in distinct if c in main) >= 2
            elif kind == "twoormoreinsideboard":
                ok = sum(1 for c in distinct if c in side) >= 2
            elif kind == "twoormoreinmainorsideboard":
                ok = sum(1 for c in distinct if c in main) + sum(1 for c in distinct if c in side) >= 2
            elif kind == "doesnotcontain":
                ok = first not in main and first not in side
            elif kind == "doesnotcontainmainboard":
                ok = first not in main
            elif kind == "doesnotcontainsideboard":
                ok = first not in side
            else:
                ok = True  # unknown rule type: ignore it rather than fail
            if not ok:
                return False
        return True

    def detect(self, main, side):
        """Returns (archetype name, colour string, classified?)."""
        color = self.colors(main, side)
        hits = []
        for arch in self.specific:
            if not self._matches(main, side, arch):
                continue
            variant_hit = False
            for variant in arch.get("Variants") or []:
                if variant.get("Conditions") and self._matches(main, side, variant):
                    variant_hit = True
                    complexity = len(arch["Conditions"]) + len(variant["Conditions"])
                    hits.append((complexity, archetype_name(variant, color)))
            if not variant_hit:
                hits.append((len(arch["Conditions"]), archetype_name(arch, color)))
        if hits:
            hits.sort(key=lambda h: h[0])  # several rules matched: prefer the simpler one
            return hits[0][1], color, True

        best = None
        for fb in self.fallbacks:
            weight = sum(n for card, n in main.items() if card in fb["_set"]) + \
                     sum(n for card, n in side.items() if card in fb["_set"])
            if weight and (best is None or weight > best[0] or
                           (weight == best[0] and len(fb["CommonCards"]) < len(best[1]["CommonCards"]))):
                best = (weight, fb)
        entries = len(main) + len(side)
        if best and entries and best[0] / entries > 0.1:
            return archetype_name(best[1], color), color, True
        return color_label(color), color, False


# ------------------------------------------------------- card database

def find_card_database(explicit, out_path):
    if explicit:
        return explicit if os.path.exists(explicit) else None
    folders = [os.path.dirname(os.path.abspath(out_path)), os.getcwd()]
    for folder in folders:
        for name in ("ja_cards.json.gz", "ja_cards.json"):
            path = os.path.join(folder, name)
            if os.path.exists(path):
                return path
    return None


def load_land_names(path):
    """English names of all land cards, from the site's card database."""
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    data = json.loads(raw.decode("utf-8"))
    if isinstance(data, dict):
        fields, rows = data.get("fields") or [], data.get("cards") or []
    else:  # version 1: a bare list in the default field order
        fields, rows = ["id", "oracle_id", "name_en", "name_ja", "type_en"], data
    i_name, i_type = fields.index("name_en"), fields.index("type_en")
    lands = set()
    for row in rows:
        name, type_line = row[i_name] or "", row[i_type] or ""
        front_type = type_line.split(" // ")[0]
        if re.search(r"\bLand\b", front_type):
            lands.add(name)
            lands.add(name.split(" // ")[0])
    return lands


# ------------------------------------------------------------ statistics

def wilson_interval(wins, total, z=1.96):
    if total == 0:
        return None
    p = wins / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return [round(100 * max(0.0, centre - half), 1), round(100 * min(1.0, centre + half), 1)]


def place_of(result):
    m = re.match(r"\s*(\d+)(?:st|nd|rd|th)\b", result or "")
    return int(m.group(1)) if m else None


class ArchetypeStats:
    __slots__ = ("name", "unclassified", "decks", "colors", "wins", "losses", "draws", "cards", "copies", "best",
                 "main_in", "main_copies", "side_in", "list_best")

    def __init__(self, name, unclassified):
        self.name, self.unclassified = name, unclassified
        self.decks = 0
        self.colors = collections.Counter()
        self.wins = self.losses = self.draws = 0
        self.cards = collections.Counter()   # decks containing the card (main deck, non-land)
        self.copies = collections.Counter()
        self.best = None                     # (sort key, sample dict)
        self.main_in = collections.Counter()      # decks with the card in the main deck (lands too)
        self.main_copies = collections.Counter()  # copies of it in those main decks
        self.side_in = collections.Counter()      # decks with the card in the sideboard
        self.list_best = None                # (sort key, deck, event): the list shown on the deck page


def load_tournaments(decklists_dir, start, end):
    """Yields (date, source, tournament dict) for files dated start..end."""
    base = os.path.join(decklists_dir, "Tournaments")
    seen = set()
    for src in SOURCES:
        for (y, m) in month_list(start, end):
            month_dir = os.path.join(base, src, f"{y:04d}", f"{m:02d}")
            if not os.path.isdir(month_dir):
                continue
            for day in sorted(os.listdir(month_dir)):
                if not day.isdigit():
                    continue
                try:
                    date = datetime.date(y, m, int(day))
                except ValueError:
                    continue
                if not (start <= date <= end):
                    continue
                day_dir = os.path.join(month_dir, day)
                for fname in sorted(os.listdir(day_dir)):
                    if not fname.endswith(".json"):
                        continue
                    try:
                        with open(os.path.join(day_dir, fname), encoding="utf-8") as f:
                            data = json.load(f)
                    except (ValueError, OSError):
                        continue
                    info = data.get("Tournament") or {}
                    key = info.get("Uri") or fname
                    if key in seen:
                        continue  # multi-day events can be listed twice
                    seen.add(key)
                    yield date, src, data


def board(cards):
    out = collections.Counter()
    for c in cards or []:
        name = c.get("CardName") or c.get("Card")
        if name:
            out[name] += int(c.get("Count") or 0)
    return out


def analyse(tournaments, rules, start, end, max_key_cards=KEY_CARDS):
    """Statistics for one format and one window. `tournaments` is a list of
    pre-classified events (see classify_event)."""
    stats = {}
    events = decks_total = matches = 0
    first = last = None
    for ev in tournaments:
        if not (start <= ev["date"] <= end):
            continue
        events += 1
        first = ev["date"] if first is None or ev["date"] < first else first
        last = ev["date"] if last is None or ev["date"] > last else last
        for deck in ev["decks"]:
            key = (deck["name"], deck["classified"])
            st = stats.get(key)
            if st is None:
                st = stats[key] = ArchetypeStats(deck["name"], not deck["classified"])
            st.decks += 1
            decks_total += 1
            st.colors[deck["color"]] += 1
            for card, count in deck["spells"].items():
                st.cards[card] += 1
                st.copies[card] += count
            for card, count in deck["main"].items():
                st.main_in[card] += 1
                st.main_copies[card] += count
            for card in deck["side"]:
                st.side_in[card] += 1
            place = deck["place"] if deck["place"] is not None else 10 ** 6
            sort_key = (place, -ev["size"], -ev["date"].toordinal())
            if deck["url"]:
                if st.best is None or sort_key < st.best[0]:
                    st.best = (sort_key, {"url": deck["url"], "event": ev["name"],
                                          "date": ev["date"].isoformat(), "result": deck["result"]})
            # the deck page shows the best finish too (a list with a link to its source first)
            list_key = (0 if deck["url"] else 1,) + sort_key
            if st.list_best is None or list_key < st.list_best[0]:
                st.list_best = (list_key, deck, ev)
        for a, b, outcome in ev["matches"]:
            if a == b:
                continue  # mirror match
            sa, sb = stats.get(a), stats.get(b)
            if sa is None or sb is None:
                continue
            if outcome == 0:
                sa.draws += 1
                sb.draws += 1
                continue
            matches += 1
            winner, loser = (sa, sb) if outcome > 0 else (sb, sa)
            winner.wins += 1
            loser.losses += 1

    ordered = sorted(stats.values(), key=lambda s: (-s.decks, s.name))
    shown, rest = ordered[:MAX_ARCHETYPES], ordered[MAX_ARCHETYPES:]
    out = []
    for st in shown:
        played = st.wins + st.losses
        key_cards = [card for card, n in sorted(st.cards.items(), key=lambda kv: (-kv[1], -st.copies[kv[0]], kv[0]))
                     if n / st.decks >= KEY_CARD_PRESENCE][:max_key_cards]
        colors = st.colors.most_common(1)[0][0]
        row = {
            "name": st.name,
            "colors": "" if colors == "C" else colors,
            "decks": st.decks,
            "share": round(100 * st.decks / decks_total, 2),
            "wins": st.wins, "losses": st.losses, "draws": st.draws,
            "winrate": round(100 * st.wins / played, 1) if played else None,
            "ci": wilson_interval(st.wins, played),
            "cards": key_cards,
        }
        if st.unclassified:
            row["unclassified"] = True
        if st.best:
            row["sample"] = st.best[1]
        if st.list_best:
            row["_deck"] = deck_entry(st)   # moved to meta_decks.json by main()
        out.append(row)
    result = {
        "events": events, "decks": decks_total, "matches": matches,
        "first_event": first.isoformat() if first else None,
        "last_event": last.isoformat() if last else None,
        "archetypes": out,
    }
    if rest:
        n = sum(s.decks for s in rest)
        result["rest"] = {"archetypes": len(rest), "decks": n, "share": round(100 * n / decks_total, 2)}
    return result


def deck_entry(st):
    """The deck page's data for one archetype: its best-finishing list (every
    card with its count and the share of all this archetype's lists that play
    it) and other cards many of its lists play that this one does not."""
    _, deck, ev = st.list_best
    n = st.decks
    by_count = lambda board: sorted(board.items(), key=lambda kv: (-kv[1], kv[0]))
    entry = {
        "list": {"url": deck["url"], "event": ev["name"], "date": ev["date"].isoformat(), "result": deck["result"]},
        "main": [[count, card, round(100 * st.main_in[card] / n)] for card, count in by_count(deck["main"])],
        "side": [[count, card, round(100 * st.side_in[card] / n)] for card, count in by_count(deck["side"])],
    }
    more = [(card, k) for card, k in st.main_in.items() if card not in deck["main"] and k / n >= MORE_PRESENCE]
    more.sort(key=lambda kv: (-kv[1], kv[0]))
    entry["more"] = [[card, round(100 * k / n), round(st.main_copies[card] / k, 1)] for card, k in more[:MORE_CARDS]]
    return entry


def deck_key(row):
    """How meta_decks.json names an archetype: its name, plus |u when it is an
    unclassified colour group (which could share a name with a real deck)."""
    return row["name"] + ("|u" if row.get("unclassified") else "")


def classify_event(date, src, data, rules, land_names=frozenset()):
    """Turns one tournament file into the compact form `analyse` works on."""
    info = data.get("Tournament") or {}
    name = info.get("Name") or ""
    if src.startswith("mtgo") and "league" in name.lower():
        return None  # leagues only publish 5-0 lists
    raw_decks = data.get("Decks") or []
    if len(raw_decks) < MIN_DECKS_PER_EVENT:
        return None

    name_counts = collections.Counter(d.get("Player") for d in raw_decks)
    ranks = {s.get("Player"): s.get("Rank") for s in data.get("Standings") or []}
    decks, by_player = [], {}
    for d in raw_decks:
        main, side = board(d.get("Mainboard")), board(d.get("Sideboard"))
        if sum(main.values()) < MIN_MAINBOARD:
            continue
        arch, color, classified = rules.detect(main, side)
        player = d.get("Player")
        place = place_of(d.get("Result"))
        if place is None and isinstance(ranks.get(player), int):
            place = ranks[player]
        decks.append({
            "name": arch, "color": color, "classified": classified,
            "spells": {c: n for c, n in main.items() if c not in rules.lands and c not in land_names},
            "main": dict(main), "side": dict(side),
            "url": d.get("AnchorUri") or "", "result": d.get("Result") or "", "place": place,
        })
        # A name used by several players (e.g. anonymised accounts) cannot be
        # matched to a deck, so its matches are not counted.
        if player and player != "-" and name_counts[player] == 1:
            by_player[player] = (arch, classified)
    if len(decks) < MIN_DECKS_PER_EVENT:
        return None

    matches = []
    for rnd in data.get("Rounds") or []:
        for m in rnd.get("Matches") or []:
            a, b = by_player.get(m.get("Player1")), by_player.get(m.get("Player2"))
            if a is None or b is None:
                continue
            parts = str(m.get("Result") or "").split("-")
            if len(parts) != 3:
                continue
            try:
                g1, g2 = int(parts[0]), int(parts[1])
            except ValueError:
                continue
            if g1 == g2 == 0:
                continue  # intentional draw or no result
            matches.append((a, b, (g1 > g2) - (g1 < g2)))
    return {"date": date, "name": name, "size": len(raw_decks), "decks": decks, "matches": matches}


# ------------------------------------------------------------------ main

def default_out_path():
    folder = r"A:\Akuchie"
    return os.path.join(folder, "meta.json") if os.path.isdir(folder) else "meta.json"


def main():
    ap = argparse.ArgumentParser(description="Build meta.json for the 悪知恵 metagame tab.")
    ap.add_argument("--out", default=None)
    ap.add_argument("--decks-out", default=None)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--days", default=",".join(str(d) for d in DEFAULT_WINDOWS))
    ap.add_argument("--decklists", default=None)
    ap.add_argument("--formatdata", default=None)
    ap.add_argument("--cards", default=None)
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument("--today", default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()

    out_path = args.out or default_out_path()
    cache = args.cache or os.path.join(os.path.dirname(os.path.abspath(out_path)), "meta_cache")
    windows = sorted({int(d) for d in args.days.split(",") if d.strip()})
    if not windows or min(windows) < 1:
        ap.error("--days needs one or more positive numbers, e.g. 30,90")
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.datetime.now(datetime.timezone.utc).date()
    earliest = today - datetime.timedelta(days=max(windows) - 1)
    months = month_list(earliest, today)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    decklists, formatdata = args.decklists, args.formatdata
    if not (decklists and formatdata):
        got = None
        if not args.no_git and git_available():
            try:
                got = fetch_with_git(cache, months)
            except RuntimeError as e:
                log(f"git download did not work ({str(e).splitlines()[0]}); using plain HTTPS instead.")
        if got is None:
            got = fetch_with_http(cache, months, token)
        decklists, formatdata = decklists or got[0], formatdata or got[1]

    formats_dir = os.path.join(formatdata, "Formats")
    if not os.path.isdir(formats_dir):
        raise RuntimeError(f"No 'Formats' folder in {formatdata}.")
    rules = {f: FormatRules(formats_dir, f) for f in FORMATS if os.path.isdir(os.path.join(formats_dir, f))}

    land_names = frozenset()
    cards_path = find_card_database(args.cards, out_path)
    if cards_path:
        try:
            land_names = frozenset(load_land_names(cards_path))
        except (ValueError, OSError, IndexError):
            log(f"  note: could not read the card database at {cards_path}.")
    if not land_names:
        log("  note: card database (ja_cards.json.gz) not found here - the site will filter lands out of the key cards itself.")
    key_cards = KEY_CARDS if land_names else KEY_CARDS_NO_DB

    log("Reading tournaments and naming decks...")
    events = {f: [] for f in rules}
    data_through = None
    files = 0
    for date, src, data in load_tournaments(decklists, earliest, today):
        files += 1
        fmt = (data.get("Tournament") or {}).get("Formats")
        if fmt not in rules:
            continue
        ev = classify_event(date, src, data, rules[fmt], land_names)
        if ev:
            events[fmt].append(ev)
            data_through = date if data_through is None or date > data_through else data_through
    if not any(events.values()):
        raise RuntimeError("No tournaments found in the chosen period - nothing was written.")

    payload = {
        "version": 1,
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_through": data_through.isoformat(),
        "sources": [
            {"name": "MTGODecklistCache", "url": f"https://github.com/{DECKLIST_REPO}"},
            {"name": "MTGOFormatData", "url": f"https://github.com/{FORMATDATA_REPO}"},
        ],
        "windows": {},
    }
    for days in windows:
        start = today - datetime.timedelta(days=days - 1)
        payload["windows"][str(days)] = {
            "from": start.isoformat(), "to": today.isoformat(),
            "formats": {f.lower(): analyse(events[f], rules[f], start, today, key_cards) for f in FORMATS if f in rules},
        }

    # deck lists go to their own file: only a deck's page needs them
    decks_payload = {
        "version": 1,
        "generated": payload["generated"],
        "data_through": payload["data_through"],
        "windows": {},
    }
    for days, win in payload["windows"].items():
        per_format = decks_payload["windows"][days] = {}
        for fmt, block in win["formats"].items():
            per_format[fmt] = {}
            for row in block["archetypes"]:
                entry = row.pop("_deck", None)
                if entry:
                    per_format[fmt][deck_key(row)] = entry
    decks_path = args.decks_out or os.path.join(os.path.dirname(os.path.abspath(out_path)), "meta_decks.json")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.makedirs(os.path.dirname(os.path.abspath(decks_path)), exist_ok=True)
    with open(decks_path, "w", encoding="utf-8") as f:
        json.dump(decks_payload, f, ensure_ascii=False, separators=(",", ":"))

    log(f"\nRead {files:,} tournament files. Wrote {out_path} "
        f"({os.path.getsize(out_path) / 1024:.0f} KB) and {decks_path} "
        f"({os.path.getsize(decks_path) / 1024:.0f} KB), data through {payload['data_through']}.")
    show = str(windows[0])
    for fmt, block in payload["windows"][show]["formats"].items():
        unclassified = sum(a["decks"] for a in block["archetypes"] if a.get("unclassified"))
        pct = 100 * unclassified / block["decks"] if block["decks"] else 0
        log(f"\n{fmt.capitalize()} - last {show} days: {block['events']} events, {block['decks']:,} decks, "
            f"{block['matches']:,} matches with results, {pct:.0f}% of decks unclassified")
        for a in block["archetypes"][:5]:
            wr = f"{a['winrate']:.1f}% over {a['wins'] + a['losses']} matches" if a["winrate"] is not None else "no match data"
            tag = " (unclassified)" if a.get("unclassified") else ""
            log(f"  {a['share']:5.1f}%  {a['name']}{tag}  -  win rate {wr}")
    log("\nUpload meta.json and meta_decks.json next to index.html in your repo.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, urllib.error.URLError) as e:
        print(f"\nStopped: {e}", file=sys.stderr)
        sys.exit(1)

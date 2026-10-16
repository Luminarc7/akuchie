#!/usr/bin/env python3
"""Checks a freshly built card database against the one the site has now, refuses it
when something looks lost, and writes a "what's new" note.

usage: python3 tools/check_database.py OLD_ja_cards.json.gz NEW_ja_cards.json.gz
           [--old-printings OLD] [--new-printings NEW] [--note note.md]

Exit code 0: the new files are fine (the note says what changed); 1: refused (the note
and the output say why). tools/update_database.py runs it before a rebuild replaces
anything, so a bad Scryfall day never reaches the site.
"""
import argparse
import collections
import gzip
import json
import sys

# How much may go missing before a rebuild is refused. Scryfall merges or drops a few
# cards now and then; more than this means a broken download or a builder bug.
MAX_LOST_CARDS = 30
MAX_LOST_JA_NAMES = 30
MAX_LOST_JA_TEXT = 60
MAX_RARITY_DROP = 0.03        # per rarity, as a share of the old count
MAX_NAME_CHANGES = 0.02       # Japanese names changed, as a share of the cards
MAX_LOST_PRINTINGS = 0.01
MIN_READINGS = 0.95           # cards with a Japanese name that have a reading
# Well-known cards that must keep their Japanese name.
SPOT_CHECKS = ["Lightning Bolt", "Counterspell", "Llanowar Elves", "Sol Ring", "Swords to Plowshares",
               "Ragavan, Nimble Pilferer", "Sheoldred, the Apocalypse", "The One Ring", "Orcish Bowmasters",
               "Brainstorm", "Dark Ritual", "Thoughtseize", "Solitude", "Shivan Dragon", "Serra Angel"]
RARITY_LETTERS = "curmsb"
SHOW = 60                     # names listed per section of the note


def load(path):
    data = json.load(gzip.open(path))
    fields = data["fields"]
    rows = [dict(zip(fields, r)) for r in data["cards"]]
    return data, fields, rows


def label(row):
    ja, en = row.get("name_ja") or "", row.get("name_en") or ""
    return f"{ja} / {en}" if ja else en


def printing_count(path):
    if not path:
        return None
    data = json.load(gzip.open(path))
    return sum(len(numbers) for numbers in data["sets"].values())


def check(old_path, new_path, old_printings=None, new_printings=None):
    """Returns (problems, note lines)."""
    old_data, old_fields, old_rows = load(old_path)
    new_data, new_fields, new_rows = load(new_path)
    problems = []
    old_by = {r["oracle_id"]: r for r in old_rows}
    new_by = {r["oracle_id"]: r for r in new_rows}

    if len(new_by) != len(new_rows):
        problems.append(f"{len(new_rows) - len(new_by)} cards share an oracle_id with another")
    ids = collections.Counter(r["id"] for r in new_rows)
    dup = [i for i, n in ids.items() if n > 1]
    if dup:
        problems.append(f"{len(dup)} printing ids are used by more than one card")
    missing_fields = [f for f in old_fields if f not in new_fields]
    if missing_fields:
        problems.append("fields missing from the new database: " + ", ".join(missing_fields))
    empty = [r for r in new_rows if not r.get("name_en") or not r.get("oracle_id") or not r.get("id")]
    if empty:
        problems.append(f"{len(empty)} cards have no English name, oracle_id or printing id")

    lost = [old_by[o] for o in old_by if o not in new_by]
    added = [new_by[o] for o in new_by if o not in old_by]
    if len(lost) > MAX_LOST_CARDS:
        problems.append(f"{len(lost)} cards would disappear (at most {MAX_LOST_CARDS} allowed)")

    def count(rows, key):
        return sum(1 for r in rows if r.get(key))
    for key, most, what in (("name_ja", MAX_LOST_JA_NAMES, "Japanese names"), ("oracle_ja", MAX_LOST_JA_TEXT, "Japanese rules texts")):
        before, after = count(old_rows, key), count(new_rows, key)
        if after < before - most:
            problems.append(f"{before - after} {what} would be lost (at most {most} allowed)")

    if "name_kana" in new_fields:
        named = [r for r in new_rows if r.get("name_ja")]
        read = sum(1 for r in named if r.get("name_kana"))
        if named and read / len(named) < MIN_READINGS:
            problems.append(f"only {read:,} of {len(named):,} Japanese names have a reading")

    def rarity_counts(rows):
        out = collections.Counter()
        for r in rows:
            for letter in r.get("rarities") or {"common": "c", "uncommon": "u", "rare": "r", "mythic": "m"}.get(r.get("rarity"), ""):
                out[letter] += 1
        return out
    old_rar, new_rar = rarity_counts(old_rows), rarity_counts(new_rows)
    for letter in "curm":
        if old_rar[letter] and new_rar[letter] < old_rar[letter] * (1 - MAX_RARITY_DROP):
            problems.append(f"rarity {letter}: {old_rar[letter]:,} cards before, {new_rar[letter]:,} now")

    spot_lost = [n for n in SPOT_CHECKS
                 if any(r["name_en"] == n and r.get("name_ja") for r in old_rows)
                 and not any(r["name_en"] == n and r.get("name_ja") for r in new_rows)]
    if spot_lost:
        problems.append("well-known cards lost their Japanese name: " + ", ".join(spot_lost))

    both = [o for o in new_by if o in old_by]
    renamed = [(old_by[o], new_by[o]) for o in both
               if old_by[o].get("name_ja") and new_by[o].get("name_ja") and old_by[o]["name_ja"] != new_by[o]["name_ja"]]
    if both and len(renamed) > MAX_NAME_CHANGES * len(both):
        problems.append(f"{len(renamed):,} Japanese names changed (at most {MAX_NAME_CHANGES:.0%} allowed)")
    got_name = [new_by[o] for o in both if not old_by[o].get("name_ja") and new_by[o].get("name_ja")]
    got_text = [new_by[o] for o in both if not old_by[o].get("oracle_ja") and new_by[o].get("oracle_ja")]

    old_p, new_p = printing_count(old_printings), printing_count(new_printings)
    if new_printings and old_p and new_p < old_p * (1 - MAX_LOST_PRINTINGS):
        problems.append(f"printings: {old_p:,} before, {new_p:,} now")

    changed = collections.Counter()
    for o in both:
        for f in new_fields:
            if f in old_fields and old_by[o].get(f) != new_by[o].get(f):
                changed[f] += 1

    note = [f"## Card database update {new_data.get('generated', '')}", ""]
    note.append(f"- Cards: {len(old_rows):,} → {len(new_rows):,} ({len(added):,} new, {len(lost):,} gone)")
    note.append(f"- With a Japanese name: {count(old_rows, 'name_ja'):,} → {count(new_rows, 'name_ja'):,}")
    note.append(f"- With Japanese rules text: {count(old_rows, 'oracle_ja'):,} → {count(new_rows, 'oracle_ja'):,}")
    if new_p is not None:
        note.append(f"- Printings: {old_p:,} → {new_p:,}" if old_p else f"- Printings: {new_p:,}")
    note.append("- Per rarity (c u r m): " + " ".join(f"{old_rar[l]:,}→{new_rar[l]:,}" for l in "curm"))

    def section(title, rows, show=lambda r: f"{label(r)} ({r.get('set', '').upper()})"):
        if not rows:
            return
        note.extend(["", f"### {title} ({len(rows):,})"])
        for r in sorted(rows, key=lambda r: (r.get("released_at") or "", r.get("name_en") or ""), reverse=True)[:SHOW]:
            note.append("- " + show(r))
        if len(rows) > SHOW:
            note.append(f"- … and {len(rows) - SHOW:,} more")
    section("New cards", added)
    section("Now with a Japanese name", got_name)
    section("Now with Japanese rules text", got_text)
    if renamed:
        note.extend(["", f"### Japanese name changed ({len(renamed):,})"])
        note.extend(f"- {o['name_ja']} → {n['name_ja']} ({n['name_en']})" for o, n in renamed[:SHOW])
    section("No longer in the database", lost)
    if changed:
        note.extend(["", "### Fields changed on existing cards", ""])
        note.append(", ".join(f"{f} {n:,}" for f, n in changed.most_common()))
    if problems:
        note[1:1] = ["", "**Refused:**", ""] + [f"- {p}" for p in problems]
    return problems, note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--old-printings")
    ap.add_argument("--new-printings")
    ap.add_argument("--note", help="write the what's-new note (Markdown) here")
    a = ap.parse_args()
    problems, note = check(a.old, a.new, a.old_printings, a.new_printings)
    text = "\n".join(note) + "\n"
    if a.note:
        with open(a.note, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)
    if problems:
        print("REFUSED:\n  " + "\n  ".join(problems), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

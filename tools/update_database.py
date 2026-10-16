#!/usr/bin/env python3
"""Rebuilds the card database and the printings file from Scryfall, checks them and,
when they pass, puts them in place of the old ones. GitHub runs it every week
(.github/workflows/update-cards.yml); it can also be run by hand.

    pip install sudachipy sudachidict_full pykakasi
    python3 tools/update_database.py [--work DIR] [--note note.md]

Steps:
  1. tools/build_ja_database.py builds both files from Scryfall's bulk data (in DIR);
  2. tools/fix_names.py puts in the Japanese names Scryfall has wrong;
  3. tools/name_readings.py adds the readings (name_kana);
  4. tools/check_database.py compares with the files in the repository and refuses a
     build that lost cards, Japanese names, texts or printings;
  5. the files replace the old ones only when their cards changed (the date alone
     is not a change).

Exit code: 0 replaced, 3 nothing changed, 1 refused or failed. The note
(Markdown) says what changed or why it was refused.
"""
import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, "ja_cards.json.gz")
PRINTINGS = os.path.join(ROOT, "printings.json.gz")


def run(*args):
    print("+", " ".join(args), flush=True)
    subprocess.run([sys.executable, *args], check=True)


def content(path, key):
    """The file's data without its build date, to tell a real change from a new date."""
    if not os.path.exists(path):
        return None
    data = json.load(gzip.open(path))
    return [data.get("fields"), data.get(key)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", help="folder for the new files (default: a temporary one)")
    ap.add_argument("--note", default="db_note.md", help="where to write the what's-new note")
    a = ap.parse_args()
    work = a.work or tempfile.mkdtemp(prefix="cards-")
    os.makedirs(work, exist_ok=True)
    new_db = os.path.join(work, "ja_cards.json.gz")
    new_pr = os.path.join(work, "printings.json.gz")

    run(os.path.join(HERE, "build_ja_database.py"), "--out", new_db, "--printings", new_pr)
    run(os.path.join(HERE, "fix_names.py"), new_db)
    run(os.path.join(HERE, "name_readings.py"), new_db)
    check = [os.path.join(HERE, "check_database.py"), DB, new_db, "--new-printings", new_pr, "--note", a.note]
    if os.path.exists(PRINTINGS):
        check += ["--old-printings", PRINTINGS]
    print("+", " ".join(check), flush=True)
    if subprocess.run([sys.executable, *check]).returncode != 0:
        print("The new card database was refused; the old one stays.", file=sys.stderr)
        sys.exit(1)

    changed = False
    for new, old, key in ((new_db, DB, "cards"), (new_pr, PRINTINGS, "sets")):
        if content(new, key) != content(old, key):
            shutil.copyfile(new, old)
            changed = True
            print(f"replaced {os.path.relpath(old, ROOT)}")
    if not changed:
        print("Nothing changed since the last build.")
        sys.exit(3)


if __name__ == "__main__":
    main()

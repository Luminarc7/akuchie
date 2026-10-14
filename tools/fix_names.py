#!/usr/bin/env python3
"""Puts the right Japanese names into the card database where Scryfall's Japanese
data has them wrong or missing (tools/name_fixes_ja.json, English name -> Japanese).

Scryfall's Japanese printings of many two-part cards (adventures, split cards,
rooms, Secrets of Strixhaven's "prepare" cards...) carry the English name on a
face, or no name at all, so the database had names like
"Spellscorn Coven // お返し". The fixes were read off the Japanese cards themselves.

usage: python3 tools/fix_names.py ja_cards.json.gz
It runs before the name readings (.github/workflows/name-readings.yml); when every
name is already right it changes nothing.
"""
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    path = sys.argv[1]
    fixes = json.load(open(os.path.join(HERE, 'name_fixes_ja.json'), encoding='utf-8'))
    original = gzip.open(path).read()
    data = json.loads(original)
    f = data['fields']
    i_en, i_ja = f.index('name_en'), f.index('name_ja')
    changed = 0
    for row in data['cards']:
        want = fixes.get(row[i_en])
        if want and row[i_ja] != want:
            row[i_ja] = want
            changed += 1
    if not changed:
        print('every name is already right: nothing to change')
        return
    out = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    with open(path, 'wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', compresslevel=9, mtime=0) as g:
            g.write(out)
    print(f'{changed} names corrected')


if __name__ == '__main__':
    main()

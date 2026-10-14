#!/usr/bin/env python3
"""Writes preview.html from index.html. Run it after every change to index.html.

preview.html is the same page with two differences:
- <meta name="robots" content="noindex">: search engines leave it out;
- data-combos="1" on <html>: the Commander combo suggestions are switched on there
  (they are off on the main page).

usage: python3 tools/make_preview.py            (in the repository folder)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHOR = '<meta charset="UTF-8">'
TAG = '<html lang="ja" data-theme="dark" data-site="main" data-home="true">'


def main():
    src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    if src.count(ANCHOR) != 1 or src.count(TAG) != 1:
        sys.exit('index.html: the <meta charset> or <html ...> line changed; update tools/make_preview.py')
    prev = src.replace(ANCHOR, ANCHOR + '\n<meta name="robots" content="noindex">', 1)
    prev = prev.replace(TAG, TAG.replace('data-home="true"', 'data-home="true" data-combos="1"'), 1)
    open(os.path.join(ROOT, 'preview.html'), 'w', encoding='utf-8').write(prev)
    print('preview.html written')


if __name__ == '__main__':
    main()

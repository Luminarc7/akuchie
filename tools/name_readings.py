#!/usr/bin/env python3
"""Adds name_kana to the card database: the reading of each Japanese card name,
in hiragana, used to sort search results in あいうえお order in Japanese mode.
It is never shown and never searched; the card names stay as they are.

Where Scryfall has the name printed with furigana (吹（ふ）きさらしの要（よう）塞（さい）),
that printed reading is used. Every other name is read with the Sudachi
dictionary (SudachiDict full), which gets almost all card names right.

usage: pip install sudachipy sudachidict_full
       python3 tools/name_readings.py ja_cards.json.gz [out.json.gz]

It runs by itself on GitHub (.github/workflows/name-readings.yml) whenever
ja_cards.json.gz changes; when every reading is already in place it changes nothing.
"""
import gzip
import json
import re
import sys

KANJI = '㐀-鿿豈-﫿々〆ヶ'
RUBY = re.compile(r'([' + KANJI + r']+)[（(]([ぁ-ゖー]+)[）)]')
HAS_KANJI = re.compile('[' + KANJI + ']')
DROP = re.compile(r'[\s、。・，,.!！?？:：;；\'"’“”「」『』（）()\[\]【】〈〉《》/／\-–—~〜&＆+＋]')
VOWEL = {}
for vowel, row in (('あ', 'あかさたなはまやらわがざだばぱぁゃゎ'), ('い', 'いきしちにひみりぎじぢびぴぃゐ'),
                   ('う', 'うくすつぬふむゆるぐずづぶぷぅゅゔっ'), ('え', 'えけせてねへめれげぜでべぺぇゑ'),
                   ('お', 'おこそとのほもよろをごぞどぼぽぉょ'), ('ん', 'ん')):
    for ch in row:
        VOWEL[ch] = vowel


def hira(s):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in s)


def sort_key(reading):
    """hiragana, punctuation left out, ー read as the vowel before it (ラー -> らあ)"""
    out = []
    for c in DROP.sub('', hira(reading)):
        if c == 'ー' and out and out[-1] in VOWEL:
            c = VOWEL[out[-1]]
        out.append(c)
    return ''.join(out)


def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else src
    original = gzip.open(src).read()
    data = json.loads(original)
    fields = data['fields']
    i_name, i_alt = fields.index('name_ja'), fields.index('alt_names_ja')
    if 'name_kana' not in fields:
        fields.append('name_kana')
        for row in data['cards']:
            row.append('')
    i_kana = fields.index('name_kana')
    while any(len(r) < len(fields) for r in data['cards']):
        for r in data['cards']:
            if len(r) < len(fields):
                r.append('')

    from sudachipy import Dictionary, SplitMode
    tok = Dictionary(dict='full').tokenizer()

    def dictionary_reading(name):
        parts = []
        for m in tok.tokenize(name, SplitMode.C):
            surface = m.surface()
            r = m.reading_form()
            parts.append(surface if (m.is_oov() or not r or r == '*') else r)
        return ''.join(parts)

    done = printed = read = 0
    cache = {}
    for row in data['cards']:
        name = row[i_name] or ''
        if not name:
            row[i_kana] = ''
            continue
        if name in cache:
            row[i_kana] = cache[name]
            continue
        # the printed furigana: the name itself or an older printing of the same name
        with_ruby = name if RUBY.search(name) else next(
            (a for a in (row[i_alt] or '').split('|') if RUBY.search(a) and RUBY.sub(r'\1', a) == RUBY.sub(r'\1', name)), '')
        plain = RUBY.sub(r'\1', name)
        reading = ''
        if with_ruby:
            r = RUBY.sub(r'\2', with_ruby)
            if not HAS_KANJI.search(r):
                reading = r
                printed += 1
        if not reading:
            reading = dictionary_reading(plain) if HAS_KANJI.search(plain) else plain
            read += 1
        key = sort_key(reading)
        row[i_kana] = key
        cache[name] = key
        done += 1
    data['fields'] = fields
    out = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if dst == src and json.loads(original) == data:
        print('every name already has its reading: nothing to change')
        return
    with open(dst, 'wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', compresslevel=9, mtime=0) as f:   # mtime 0: same input, same bytes
            f.write(out)
    left = sum(1 for r in data['cards'] if r[i_kana] and HAS_KANJI.search(r[i_kana]))
    print(f'{done} names: {printed} from printed furigana, {read} from the dictionary; {left} still have a kanji the dictionary did not know')


if __name__ == '__main__':
    main()

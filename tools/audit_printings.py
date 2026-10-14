"""Audit, over Scryfall's all_cards bulk file (every printing in every language):
1. printings whose languages are split over different set codes (Japanese 4th Edition
   is set 4bb, English 4th Edition is 4ed): which set pairs, matched how.
2. two-part cards (adventure, split, MDFC...) whose Japanese printing lacks a face's
   printed_name, and whether another Japanese printing or the text supplies it.
3. the site's database rows: how many names still contain an English face."""
import gzip, json, sys, collections, re, ijson

bulk, sets_path, db_path, out_path = sys.argv[1:5]
sets = {s['code']: s for s in json.load(open(sets_path))['data']}


def oid(c):
    return c.get('oracle_id') or ((c.get('card_faces') or [{}])[0].get('oracle_id'))


keys = collections.defaultdict(dict)            # (set, cn) -> {lang: oracle}
by_oracle_en = collections.defaultdict(list)    # oracle -> [(set, cn)] English printings
ja_faces = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))  # oracle -> face index -> Counter(names)
ja_top = collections.defaultdict(collections.Counter)
missing = []                                    # Japanese multi-face printings lacking a face name
n = 0
def cards_of(path):
    with (gzip.open(path) if path.endswith('.gz') else open(path, 'rb')) as f:
        if '.jsonl' in path:
            for line in f:
                if line.strip():
                    yield json.loads(line)
        else:
            yield from ijson.items(f, 'item')


if True:
    for c in cards_of(bulk):
        n += 1
        o = oid(c)
        k = (c['set'], c['collector_number'])
        keys[k].setdefault(c['lang'], o)
        if c['lang'] == 'en':
            by_oracle_en[o].append(k)
        if c['lang'] == 'ja':
            faces = c.get('card_faces') or []
            if c.get('printed_name'):
                ja_top[o][c['printed_name']] += 1
            if len(faces) > 1:
                for i, fc in enumerate(faces):
                    if fc.get('printed_name'):
                        ja_faces[o][i][fc['printed_name']] += 1
                if any(not fc.get('printed_name') for fc in faces):
                    missing.append({'id': c['id'], 'set': c['set'], 'cn': c['collector_number'], 'oracle': o, 'layout': c.get('layout'),
                                    'name': c.get('name'), 'printed_name': c.get('printed_name'),
                                    'faces': [{'name': fc.get('name'), 'printed_name': fc.get('printed_name'),
                                               'printed_text': (fc.get('printed_text') or '')[:200]} for fc in faces]})
print('cards', n, file=sys.stderr)


def set_info(code):
    x = sets.get(code, {})
    return {'name': x.get('name'), 'type': x.get('set_type'), 'parent': x.get('parent_set_code'), 'released': x.get('released_at'), 'count': x.get('card_count')}


out = {'cards': n}
# 1. non-English printings with no English printing at the same set + number
no_en = collections.Counter()                  # set -> printings without English
langs_of = collections.defaultdict(collections.Counter)
pair_same = collections.Counter()              # (set, en set) same oracle, same number
pair_unique = collections.Counter()            # (set, en set) same oracle, the only English printing of it in that set
pair_any = collections.Counter()
for (s, cn), langs in keys.items():
    if 'en' in langs:
        continue
    o = next(iter(langs.values()))
    no_en[s] += 1
    for l in langs:
        langs_of[s][l] += 1
    en = by_oracle_en.get(o, [])
    per_set = collections.Counter(s2 for s2, _ in en)
    for s2 in {s2 for s2, cn2 in en if cn2 == cn}:
        pair_same[(s, s2)] += 1
    for s2 in {s2 for s2, _ in en}:
        pair_any[(s, s2)] += 1
        if per_set[s2] == 1:
            pair_unique[(s, s2)] += 1
out['sets_without_en'] = sorted([{'set': s, 'without_en': k, 'langs': dict(langs_of[s]), **set_info(s)} for s, k in no_en.items()],
                                key=lambda r: -r['without_en'])
out['pairs'] = [{'set': a, 'en_set': b, 'same_number': k, 'unique_in_en_set': pair_unique[(a, b)], 'any': pair_any[(a, b)], 'of': no_en[a],
                 'name': set_info(a)['name'], 'en_name': set_info(b)['name'], 'type': set_info(a)['type'], 'en_type': set_info(b)['type'],
                 'released': set_info(a)['released'], 'en_released': set_info(b)['released']}
                for (a, b), k in sorted(pair_same.items(), key=lambda x: -x[1]) if k >= 3]
out['pairs_unique_not_same_number'] = [{'set': a, 'en_set': b, 'unique': k, 'same_number': pair_same[(a, b)], 'of': no_en[a],
                                        'name': set_info(a)['name'], 'en_name': set_info(b)['name']}
                                       for (a, b), k in sorted(pair_unique.items(), key=lambda x: -x[1])
                                       if k >= 10 and pair_same[(a, b)] < k / 2][:80]

# 2. Japanese face names
fixable_other = 0
fixable_text = 0
unfixed = []
for m in missing:
    o = m['oracle']
    names = []
    for i, fc in enumerate(m['faces']):
        nm = fc['printed_name'] or (ja_faces[o][i].most_common(1)[0][0] if ja_faces[o][i] else None)
        names.append(nm)
    if all(names):
        fixable_other += 1
        m['fix'] = names
        continue
    unfixed.append(m)
out['ja_multiface_missing_face_name'] = len(missing)
out['fixable_from_other_ja_printing'] = fixable_other
out['unfixed_count'] = len(unfixed)
out['unfixed'] = unfixed
out['fixed_examples'] = [m for m in missing if 'fix' in m][:40]
out['missing_by_set'] = collections.Counter(m['set'] for m in missing).most_common()
out['missing_by_layout'] = collections.Counter(m['layout'] for m in missing).most_common()

# 3. the site's database
db = json.load(gzip.open(db_path))
f = db['fields']
i_name, i_en, i_oid, i_id = f.index('name_ja'), f.index('name_en'), f.index('oracle_id'), f.index('id')
latin_face = []
for r in db['cards']:
    ja, en = r[i_name] or '', r[i_en] or ''
    if ' // ' in en and ja:
        jf, ef = ja.split(' // '), en.split(' // ')
        if any(j.strip() == e.strip() for j, e in zip(jf, ef)) or len(jf) != len(ef):
            latin_face.append({'id': r[i_id], 'oracle': r[i_oid], 'en': en, 'ja': ja,
                               'other_ja_faces': {i: dict(c) for i, c in ja_faces.get(r[i_oid], {}).items()},
                               'top': dict(ja_top.get(r[i_oid], {}))})
out['db_rows'] = len(db['cards'])
out['db_multiface_with_english_face'] = len(latin_face)
out['db_multiface_examples'] = latin_face
json.dump(out, open(out_path, 'w'), ensure_ascii=False, indent=1, default=str)
print('done', file=sys.stderr)

"""Audit: for every Japanese printing, is its English counterpart the same set + number?
Reads Scryfall's all_cards bulk file (every printing in every language) and sets.json."""
import gzip, json, sys, collections, ijson

bulk, sets_path, db_path, out_path = sys.argv[1:5]
sets = {s['code']: s for s in json.load(open(sets_path))['data']}

def oid(c):
    return c.get('oracle_id') or ((c.get('card_faces') or [{}])[0].get('oracle_id'))

keys = collections.defaultdict(dict)          # (set, cn) -> {lang: (id, oracle)}
by_id = {}
by_oracle = collections.defaultdict(list)     # oracle -> [(set, cn, lang)]
n = 0
with (gzip.open(bulk) if bulk.endswith('.gz') else open(bulk, 'rb')) as f:
    for c in ijson.items(f, 'item'):
        n += 1
        o = oid(c)
        k = (c['set'], c['collector_number'])
        keys[k].setdefault(c['lang'], (c['id'], o))
        by_id[c['id']] = (c['set'], c['collector_number'], c['lang'], o)
        if c['lang'] in ('en', 'ja'):
            by_oracle[o].append((c['set'], c['collector_number'], c['lang']))
print('cards', n, file=sys.stderr)

out = {}
# 1. Japanese printings with no English printing at the same set + number
ja_no_en = collections.Counter()
ja_total = collections.Counter()
pair_same_cn = collections.Counter()   # (ja set, en set) where the same oracle has the same number
pair_any = collections.Counter()       # (ja set, en set) same oracle, any number
for (s, cn), langs in keys.items():
    if 'ja' not in langs: continue
    ja_total[s] += 1
    if 'en' in langs: continue
    ja_no_en[s] += 1
    o = langs['ja'][1]
    others = [(s2, cn2) for s2, cn2, l in by_oracle.get(o, []) if l == 'en' and s2 != s]
    for s2 in {s2 for s2, cn2 in others if cn2 == cn}: pair_same_cn[(s, s2)] += 1
    for s2 in {s2 for s2, cn2 in others}: pair_any[(s, s2)] += 1

def set_info(code):
    x = sets.get(code, {})
    return {'name': x.get('name'), 'type': x.get('set_type'), 'parent': x.get('parent_set_code'), 'released': x.get('released_at'), 'count': x.get('card_count')}

out['ja_sets_without_en'] = sorted(
    [{'set': s, 'ja_printings': ja_total[s], 'without_en': ja_no_en[s], **set_info(s)} for s in ja_no_en],
    key=lambda r: -r['without_en'])
out['ja_to_en_pairs_same_number'] = [{'ja_set': a, 'en_set': b, 'n': k, 'of': ja_no_en[a], 'ja': set_info(a)['name'], 'en': set_info(b)['name'], 'ja_parent': set_info(a)['parent'], 'en_parent': set_info(b)['parent']}
                                     for (a, b), k in pair_same_cn.most_common(150)]
# 2. English printings whose card has Japanese printings, but none at this set + number
en_no_ja = collections.Counter(); en_total = collections.Counter()
pair_rev = collections.Counter()
for (s, cn), langs in keys.items():
    if 'en' not in langs: continue
    en_total[s] += 1
    if 'ja' in langs: continue
    o = langs['en'][1]
    js = [(s2, cn2) for s2, cn2, l in by_oracle.get(o, []) if l == 'ja']
    if not js: continue
    en_no_ja[s] += 1
    for s2 in {s2 for s2, cn2 in js if cn2 == cn}: pair_rev[(s, s2)] += 1
out['en_to_ja_pairs_same_number'] = [{'en_set': a, 'ja_set': b, 'n': k, 'en_total': en_total[a], 'en': set_info(a)['name'], 'ja': set_info(b)['name']}
                                     for (a, b), k in pair_rev.most_common(150)]
# 3. The site's database: each row is a Japanese printing
db = json.load(gzip.open(db_path))
f = db['fields']; i_id = f.index('id')
rows = [r[i_id] for r in db['cards']]
stat = collections.Counter(); no_en_sets = collections.Counter(); langs_count = collections.Counter()
examples = collections.defaultdict(list)
for rid in rows:
    if rid not in by_id: stat['id not in Scryfall'] += 1; continue
    s, cn, lang, o = by_id[rid]
    stat['lang ' + lang] += 1
    ls = keys[(s, cn)]
    langs_count[len(ls)] += 1
    if 'en' in ls: stat['English at same set+number'] += 1
    else:
        stat['no English at same set+number'] += 1
        no_en_sets[s] += 1
        if len(examples[s]) < 3: examples[s].append(rid)
out['db'] = {'rows': len(rows), 'stat': stat, 'languages_per_printing': dict(sorted(langs_count.items())),
             'no_en_by_set': [{'set': s, 'n': k, **set_info(s), 'examples': examples[s]} for s, k in no_en_sets.most_common()]}
# 4. collector numbers that are not plain (for the search query)
odd = collections.Counter()
for (s, cn) in keys:
    if not cn.replace('-', '').isalnum(): odd[cn[-1]] += 1
out['odd_number_chars'] = odd.most_common(30)
json.dump(out, open(out_path, 'w'), ensure_ascii=False, indent=1, default=str)
print('done', file=sys.stderr)

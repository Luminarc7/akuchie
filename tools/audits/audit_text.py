"""1. every printing (all languages) of a few cards, as Scryfall has them;
2. database rows whose Japanese text, type or picture could come from another
   Japanese printing of the same card."""
import gzip, json, sys, collections, re
bulk, db_path, outdir = sys.argv[1:4]
db = json.load(gzip.open(db_path)); f = db['fields']
rows = [dict(zip(f, r)) for r in db['cards']]
row_by_oracle = {r['oracle_id']: r for r in rows}
WANT = {'Spite // Malice', 'Fire // Ice', 'Armageddon', 'Lightning Bolt'}
want_oracles = {r['oracle_id'] for r in rows if r['name_en'] in WANT}
dump = collections.defaultdict(list)
ja = collections.defaultdict(list)
langs_at = collections.defaultdict(set)
def oid(c): return c.get('oracle_id') or ((c.get('card_faces') or [{}])[0].get('oracle_id'))
def text_of(c, k):
    if c.get(k): return c[k]
    fs = [x.get(k) for x in (c.get('card_faces') or [])]
    return ' // '.join(x for x in fs if x) if any(fs) else ''
for line in gzip.open(bulk):
    if not line.strip(): continue
    c = json.loads(line); o = oid(c)
    langs_at[(c['set'], c['collector_number'])].add(c['lang'])
    if o in want_oracles: dump[c['name']].append(c)
    if c['lang'] == 'ja' and o in row_by_oracle:
        ja[o].append({'id': c['id'], 'set': c['set'], 'cn': c['collector_number'], 'img': c.get('image_status'),
                      'name': text_of(c, 'printed_name'), 'type': text_of(c, 'printed_type_line'), 'text': text_of(c, 'printed_text'),
                      'released': c.get('released_at'), 'promo': c.get('promo'), 'digital': c.get('digital'), 'lang_count': 0})
json.dump(dump, open(outdir + '/cards_dump.json', 'w'), ensure_ascii=False)
stat = collections.Counter(); ex = collections.defaultdict(list)
plan = {}
for r in rows:
    if not r['name_ja']: continue
    ps = ja.get(r['oracle_id'], [])
    if not ps: stat['row has name_ja but no ja printing in scryfall'] += 1; continue
    cur = next((p for p in ps if p['id'] == r['id']), None)
    if not cur: stat['row id is not a ja printing'] += 1
    has_text = [p for p in ps if p['text']]
    has_type = [p for p in ps if p['type']]
    hi = [p for p in ps if p['img'] == 'highres_scan']
    if not r['oracle_ja']:
        if has_text: stat['oracle_ja empty, other ja printing has text'] += 1; ex['text'].append(r['name_en'])
        else: stat['oracle_ja empty, no ja text anywhere'] += 1
    if not r['type_ja']:
        if has_type: stat['type_ja empty, other ja printing has type'] += 1
        else: stat['type_ja empty, no ja type anywhere'] += 1
    if cur and cur['img'] != 'highres_scan':
        if hi: stat['row picture not highres, other ja printing highres'] += 1; ex['img'].append(r['name_en'])
        else: stat['row picture not highres, no ja highres'] += 1
    # the printing the site should use: a Japanese one with a real picture and its text
    best = sorted(ps, key=lambda p: (p['digital'] is True, p['img'] != 'highres_scan', not p['text'], p['img'] not in ('highres_scan', 'lowres'), bool(p['promo']), p['released'] or ''))[0]
    plan[r['id']] = {'oracle': r['oracle_id'], 'best': best['id'], 'best_set': best['set'], 'img': best['img'],
                     'text': best['text'] if not r['oracle_ja'] else None, 'type': best['type'] if not r['type_ja'] else None,
                     'text_any': (has_text[0]['text'] if has_text else None), 'type_any': (has_type[0]['type'] if has_type else None)}
out = {'stat': stat, 'examples': {k: v[:60] for k, v in ex.items()}}
json.dump(out, open(outdir + '/audit_text.json', 'w'), ensure_ascii=False, indent=1)
json.dump(plan, open(outdir + '/plan.json', 'w'), ensure_ascii=False)
# languages per (set, number) with ja: how many are image-less
print(json.dumps(stat, ensure_ascii=False, indent=1))

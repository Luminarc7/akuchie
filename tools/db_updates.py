"""Updates for the card database from every Japanese printing in Scryfall:
- type_ja where the row has none but another Japanese printing has it;
- the row's printing (id, set, rarity) when it has no real picture but another
  Japanese printing of the card has a sharp scan (a regular one preferred)."""
import gzip, json, sys, re, collections
bulk, db_path, out_path = sys.argv[1:4]
JA = re.compile('[぀-ヿ㐀-鿿]')
db = json.load(gzip.open(db_path)); f = db['fields']
rows = [dict(zip(f, r)) for r in db['cards']]
want = {r['oracle_id'] for r in rows if r['name_ja']}
ja = collections.defaultdict(list)
def oid(c): return c.get('oracle_id') or ((c.get('card_faces') or [{}])[0].get('oracle_id'))
def joined(c, k):
    if c.get(k): return c[k]
    fs = [x.get(k) for x in (c.get('card_faces') or [])]
    return ' // '.join(x for x in fs if x) if all(fs) and fs else ''
for line in gzip.open(bulk):
    if not line.strip(): continue
    c = json.loads(line)
    if c.get('lang') != 'ja': continue
    o = oid(c)
    if o in want:
        ja[o].append({'id': c['id'], 'set': c['set'], 'rarity': c.get('rarity'), 'img': c.get('image_status'), 'type': joined(c, 'printed_type_line'),
                      'promo': bool(c.get('promo')), 'digital': bool(c.get('digital')), 'fx': bool(set(c.get('frame_effects') or []) & {'showcase', 'extendedart', 'inverted', 'etched'}),
                      'full': bool(c.get('full_art')), 'border': c.get('border_color'), 'released': c.get('released_at') or '', 'oversized': bool(c.get('oversized'))})
upd = {}
n_type = n_pic = 0
for r in rows:
    ps = ja.get(r['oracle_id'], [])
    if not ps: continue
    u = {}
    if not r['type_ja']:
        t = next((p['type'] for p in ps if p['type'] and JA.search(p['type'])), '')
        if t: u['type_ja'] = t; n_type += 1
    cur = next((p for p in ps if p['id'] == r['id']), None)
    if cur and cur['img'] != 'highres_scan':
        good = [p for p in ps if p['img'] == 'highres_scan' and not p['digital'] and not p['oversized']]
        if good:
            good.sort(key=lambda p: (p['promo'], p['fx'], p['full'], p['border'] not in ('black', None), [-ord(ch) for ch in p['released']]))
            b = good[0]
            u.update({'id': b['id'], 'set': b['set'], 'rarity': b['rarity']}); n_pic += 1
    if u: upd[r['id']] = u
json.dump(upd, open(out_path, 'w'), ensure_ascii=False)
print('type_ja', n_type, 'picture', n_pic)

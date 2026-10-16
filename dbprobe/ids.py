"""Details of the printings behind every id that differs between the current database and fresh builds."""
import gzip, json, sys
sys.path.insert(0, 'b23'); import build_ja_database as B23
paths = {'old': 'old_ja_cards.json.gz', 'b23': '../probe_out/db3/b23.json.gz', 'b24': '../probe_out/db2/new/ja_cards.json.gz'}
rows = {}
for k, p in paths.items():
    d = json.load(gzip.open(p)); F = d['fields']
    rows[k] = {r[F.index('oracle_id')]: dict(zip(F, r)) for r in d['cards']}
want = set()
for o, r in rows['old'].items():
    ids = {rows[k][o]['id'] for k in rows if o in rows[k]}
    if len(ids) > 1: want |= ids
url, jl = B23.get_bulk_cards_url()
info = {}
for c in B23.iter_cards(url, jl):
    if c['id'] in want:
        info[c['id']] = {k: c.get(k) for k in ('lang', 'set', 'set_type', 'collector_number', 'image_status', 'rarity', 'promo', 'variation', 'full_art',
                                               'border_color', 'frame_effects', 'released_at', 'textless', 'promo_types')}
out = []
for o, r in rows['old'].items():
    ids = [rows[k][o]['id'] if o in rows[k] else None for k in ('old', 'b23', 'b24')]
    if len(set(ids)) > 1:
        out.append({'name': r['name_en'], 'old': info.get(ids[0]), 'b23': info.get(ids[1]) if ids[1] != ids[0] else 'same as old',
                    'b24': info.get(ids[2]) if ids[2] != ids[1] else 'same as b23'})
json.dump(out, open('../probe_out/db3/ids.json', 'w'), ensure_ascii=False, indent=0)
print(len(out), 'changed;', sum(1 for x in out if x['b23'] != 'same as old'), 'by data/2.3,', sum(1 for x in out if x['b24'] != 'same as b23'), 'by 2.4')

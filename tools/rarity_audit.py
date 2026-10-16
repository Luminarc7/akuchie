"""Card database audit: how the site's per-rarity counts compare with Scryfall's.

    python tools/rarity_audit.py <current ja_cards.json.gz> <builder dir> <out dir>

1. Scryfall search API: total_cards for r:<rarity> (and with game:paper, -is:digital), plus
   the full oracle-id list for each plain r:<rarity> (paged, 150 ms apart, real User-Agent).
2. Scryfall's all_cards bulk file: for every card, which rarities it was printed at, split by
   kind of printing (kept by the builder / excluded set type or layout / digital), and the
   rarity + set of every printing the current database shows (to catch wrong rarities).
3. A fresh build with the builder's own code, to find cards missing from the database.
"""
import collections, gzip, json, os, sys, time, urllib.error, urllib.parse, urllib.request

db_path, builder_dir, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
sys.path.insert(0, builder_dir)
import build_ja_database as B  # noqa: E402

UA = {'User-Agent': 'WarujieDbAudit/1.0 (+https://warujie.jp)', 'Accept': 'application/json'}
RARITIES = ['common', 'uncommon', 'rare', 'mythic', 'special', 'bonus']

_last = [0.0]
def scry(url):
    for attempt in range(5):
        wait = 0.15 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429:
                time.sleep(5)
                continue
            raise
        except urllib.error.URLError:
            time.sleep(3)
    raise RuntimeError('gave up on ' + url)

def search_url(q, page=1):
    return 'https://api.scryfall.com/cards/search?' + urllib.parse.urlencode({'q': q, 'unique': 'cards', 'page': page})

def oid_of(c):
    return c.get('oracle_id') or ((c.get('card_faces') or [{}])[0].get('oracle_id'))

# ---- 1. Scryfall search API ----
api = {'counts': {}, 'lists': {}}
SKIP_API = os.environ.get('SKIP_API') == '1'
for r in ([] if SKIP_API else RARITIES):
    for q in (f'r:{r}', f'r:{r} game:paper', f'r:{r} -is:digital', f'r:{r} include:extras'):
        res = scry(search_url(q))
        api['counts'][q] = res['total_cards'] if res else 0
        print(q, api['counts'][q], flush=True)
for q in ([] if SKIP_API else ['game:paper', 'cmc>=0', 'cmc>=0 -is:digital']):
    res = scry(search_url(q))
    api['counts'][q] = res['total_cards'] if res else 0
    print(q, api['counts'][q], flush=True)
for r in ([] if SKIP_API else RARITIES):
    q = f'r:{r}'
    ids, page = [], 1
    while True:
        res = scry(search_url(q, page))
        if not res:
            break
        ids += [[oid_of(c), c.get('name'), c.get('set'), bool(c.get('digital'))] for c in res['data']]
        if not res.get('has_more'):
            break
        page += 1
    api['lists'][q] = ids
    print('listed', q, len(ids), flush=True)
if not SKIP_API:
    with gzip.open(os.path.join(out, 'api.json.gz'), 'wt', encoding='utf-8') as f:
        json.dump(api, f, ensure_ascii=False)

# ---- 2 + 3. Bulk file ----
db = json.load(gzip.open(db_path))
F = db['fields']
db_ids = {row[F.index('id')] for row in db['cards']}
url, is_jsonl = B.get_bulk_cards_url()
print('bulk', url, flush=True)
rar = collections.defaultdict(dict)       # oid -> rarity -> {kind: example}
names = {}
shown = {}                                # printing id shown by the DB -> facts
what = collections.defaultdict(set)       # oid -> set types, promo types, stamps of kept printings
entries = {}
scanned = 0
for card in B.iter_cards(url, is_jsonl):
    scanned += 1
    oid = B.oracle_id_of(card)
    if not oid:
        continue
    names.setdefault(oid, card.get('name'))
    if card.get('digital'):
        kind = 'digital'
    elif B.is_excluded(card):
        kind = 'excluded:' + (card.get('set_type') or '') + '/' + (card.get('layout') or '')
    else:
        special = bool(card.get('promo')) or card.get('set_type') in B.SPECIAL_SET_TYPES
        kind = 'kept_special' if special else 'kept'
    r = card.get('rarity') or ''
    rar[oid].setdefault(r, {}).setdefault(kind, f"{card.get('set')}/{card.get('collector_number')}/{card.get('lang')}")
    if card.get('id') in db_ids:
        shown[card['id']] = {'rarity': r, 'set': card.get('set'), 'set_type': card.get('set_type'),
                             'lang': card.get('lang'), 'promo': bool(card.get('promo')), 'oid': oid}
    if not B.is_excluded(card):
        what[oid].update(['st:' + (card.get('set_type') or ''), 'stamp:' + (card.get('security_stamp') or ''),
                          'border:' + (card.get('border_color') or '')] + ['pt:' + p for p in card.get('promo_types') or []]
                         + ['games:' + '+'.join(sorted(card.get('games') or []))])
        entries.setdefault(oid, B.CardEntry()).add(card)
print('scanned', scanned, 'cards', len(rar), flush=True)

with gzip.open(os.path.join(out, 'rarities.json.gz'), 'wt', encoding='utf-8') as f:
    json.dump({'rar': rar, 'names': names, 'shown': shown, 'what': {o: sorted(v) for o, v in what.items()}}, f, ensure_ascii=False)

rows = [e.to_row() for e in entries.values() if (e.ja or e.en)]
rows.sort(key=lambda r: r[B.FIELD_ORDER.index('name_en')])
with gzip.GzipFile(os.path.join(out, 'fresh_ja_cards.json.gz'), 'wb', compresslevel=9, mtime=0) as f:
    f.write(json.dumps({'version': 2, 'generated': time.strftime('%Y-%m-%d'), 'fields': B.FIELD_ORDER,
                        'cards': rows}, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
print('fresh rows', len(rows), flush=True)

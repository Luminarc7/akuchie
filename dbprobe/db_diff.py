"""How a fresh build differs from the current database, field by field, with examples."""
import collections, gzip, json, sys
old = json.load(gzip.open(sys.argv[1])); new = json.load(gzip.open(sys.argv[2]))
O = {r[old['fields'].index('oracle_id')]: dict(zip(old['fields'], r)) for r in old['cards']}
N = {r[new['fields'].index('oracle_id')]: dict(zip(new['fields'], r)) for r in new['cards']}
print('old', len(O), 'new', len(N), 'fields old', old['fields'], '\nfields new', new['fields'])
both = [o for o in N if o in O]
diff = collections.Counter(); ex = collections.defaultdict(list)
for o in both:
    a, b = O[o], N[o]
    for f in new['fields']:
        if f in a and a[f] != b[f]:
            kind = f
            if f == 'type_ja':
                kind = 'type_ja ' + ('lost' if a[f] and not b[f] else 'gained' if b[f] and not a[f] else 'changed')
            if f == 'oracle_ja':
                kind = 'oracle_ja ' + ('lost' if a[f] and not b[f] else 'gained' if b[f] and not a[f] else 'changed')
            if f == 'name_ja':
                kind = 'name_ja ' + ('lost' if a[f] and not b[f] else 'gained' if b[f] and not a[f] else 'changed')
            diff[kind] += 1
            if len(ex[kind]) < 25:
                ex[kind].append((a['name_en'], str(a[f])[:70], str(b[f])[:70], a.get('set'), b.get('set'), a.get('rarity'), b.get('rarity')))
for k, n in diff.most_common():
    print(f'\n== {k}: {n}')
    for e in ex[k]: print('   ', e)
print('\nadded', len([o for o in N if o not in O]), [N[o]['name_en'] for o in N if o not in O][:40])
print('lost', len([o for o in O if o not in N]), [O[o]['name_en'] for o in O if o not in N][:40])
sets = [len(N[o]['sets'].split()) for o in N]
print('sets per card avg', sum(sets) / len(sets), 'max', max(sets))
tr = collections.Counter(ch for o in N for ch in N[o]['treatments'])
print('treatments', tr)
F = new['fields']
for f in F:
    b = json.dumps([c[F.index(f)] for c in new['cards']], ensure_ascii=False).encode()
    print(f'{f:14} {len(gzip.compress(b, 9))/1e6:6.3f} MB gz')

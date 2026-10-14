"""English printings whose set was printed in Japanese but which have no Japanese
printing at the same number: is the Japanese one in the same set under another
number (pairable), or not in Scryfall at all?"""
import gzip, json, sys, collections
at = collections.defaultdict(dict)        # (set, cn) -> {lang: card summary}
for line in gzip.open(sys.argv[1]):
    if not line.strip(): continue
    c = json.loads(line)
    o = c.get('oracle_id') or ((c.get('card_faces') or [{}])[0].get('oracle_id'))
    at[(c['set'], c['collector_number'])][c['lang']] = {'id': c['id'], 'oracle': o, 'name': c['name'], 'img': c.get('image_status'),
        'promo': c.get('promo'), 'digital': c.get('digital'), 'fx': c.get('frame_effects'), 'border': c.get('border_color'), 'full': c.get('full_art')}
per_set = collections.defaultdict(collections.Counter)
for (s, cn), L in at.items():
    for l in L: per_set[s][l] += 1
ja_in_set = collections.defaultdict(lambda: collections.defaultdict(list))   # set -> oracle -> [(cn, card)]
for (s, cn), L in at.items():
    if 'ja' in L: ja_in_set[s][L['ja']['oracle']].append((cn, L))
out = {'other_number': [], 'not_in_scryfall': collections.Counter(), 'examples': collections.defaultdict(list)}
pairs = collections.Counter()
for (s, cn), L in at.items():
    if 'en' not in L or 'ja' in L: continue
    if per_set[s]['ja'] < 0.5 * per_set[s]['en']: continue
    o = L['en']['oracle']
    cands = [(cn2, L2) for cn2, L2 in ja_in_set[s].get(o, []) if 'en' not in L2]
    if cands:
        out['other_number'].append({'set': s, 'cn': cn, 'name': L['en']['name'], 'ja_cn': [c[0] for c in cands]})
        pairs[s] += 1
    else:
        out['not_in_scryfall'][s] += 1
        if len(out['examples'][s]) < 12: out['examples'][s].append(f"{cn} {L['en']['name']}")
out['pairs_by_set'] = pairs.most_common()
out['not_in_scryfall'] = out['not_in_scryfall'].most_common()
print('other number', len(out['other_number']), 'not in scryfall', sum(n for _, n in out['not_in_scryfall']))
json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False, indent=0)

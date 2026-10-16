set -x
U=https://staging-warujie.warujie-mtg.workers.dev
curl -sS --compressed -A "warujie.jp-probe/1.0" -o probe_out/staging_index.html $U/
grep -c "rarity.alsoTip" probe_out/staging_index.html
grep -c "function hasRarity" probe_out/staging_index.html
curl -sS --compressed -A "warujie.jp-probe/1.0" -o /tmp/db.json $U/ja_cards.json
python3 -c "
import json; d = json.load(open('/tmp/db.json')); F = d['fields']; print(F[-3:], len(d['cards']))
i = F.index('rarities'); r = F.index('rarity'); n = F.index('name_en')
print('mythic rows', sum('m' in c[i] for c in d['cards']), 'Amnesia', [c[r] for c in d['cards'] if c[n] == 'Amnesia'])
"

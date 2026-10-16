set -x
U=https://warujie.warujie-mtg.workers.dev
sleep 170   # let the Workers build of the main push finish
for i in 1 2 3 4; do
  curl -sS --compressed -A "warujie.jp-probe/1.0" -o probe_out/live_index.html "$U/?v=$i$RANDOM"
  if cmp -s probe_out/live_index.html probe_out/expected_index.html; then echo LIVE_MATCH; break; fi
  echo not yet; sleep 60
done
sha256sum probe_out/live_index.html probe_out/expected_index.html
grep -c "function wantedRarities" probe_out/live_index.html
curl -sS --compressed -A "warujie.jp-probe/1.0" -o /tmp/db.json $U/ja_cards.json
python3 -c "
import json; d = json.load(open('/tmp/db.json')); F = d['fields']; print(F[-3:], len(d['cards']))
i = F.index('rarities'); r = F.index('rarity'); n = F.index('name_en')
print('mythic rows', sum('m' in c[i] for c in d['cards']), 'Amnesia', [c[r] for c in d['cards'] if c[n] == 'Amnesia'])
"

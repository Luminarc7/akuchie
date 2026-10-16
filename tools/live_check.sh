set -x
U=https://staging-warujie.warujie-mtg.workers.dev
sleep 150   # let the Workers build of the latest staging push finish
curl -sS --compressed -A "warujie.jp-probe/1.0" -o probe_out/staging_index.html $U/
grep -c "function wantedRarities" probe_out/staging_index.html
grep -c "shift-icon" probe_out/staging_index.html
grep -c "rarity: new Set(), format" probe_out/staging_index.html
grep -c "rarity.also'" probe_out/staging_index.html
curl -sS --compressed -A "warujie.jp-probe/1.0" -o probe_out/staging_preview.html $U/preview.html
grep -c "function wantedRarities" probe_out/staging_preview.html

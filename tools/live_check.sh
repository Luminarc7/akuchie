set -x
curl -sS --compressed -A "warujie.jp-probe/1.0" -o probe_out/live_index.html https://warujie.warujie-mtg.workers.dev/
sha256sum probe_out/live_index.html
grep -c -- 'rar-chip' probe_out/live_index.html
# check 2026-10-16T06:44:03Z

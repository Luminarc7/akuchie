#!/bin/bash
o=probe_out; UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'
for u in https://warujie.jp/ https://warujie.warujie-mtg.workers.dev/; do
  curl -sS --compressed -A "$UA" -o page.html -w "$u %{http_code} " "$u"; sha256sum page.html | cut -c1-16
done > $o/live18.txt 2>&1

#!/bin/bash
# What link-preview bots get from warujie.jp and the workers.dev addresses (same Worker).
CARD='?card=89ea9a01-a4e9-43c5-bdd7-3a0e4dcec0f3'
META='?view=meta&format=modern'
declare -a UAS=(
  'Twitterbot/1.0'
  'facebookexternalhit/1.1;line-poker/1.0'
  'Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)'
  'Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)'
  'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)'
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
)
echo "runner ip: $(curl -s -m 10 https://api.ipify.org)"
for host in https://warujie.jp https://www.warujie.jp https://warujie.warujie-mtg.workers.dev https://staging-warujie.warujie-mtg.workers.dev; do
  for path in "/$CARD" "/$META" "/robots.txt"; do
    for ua in "${UAS[@]}"; do
      [ "$path" = "/robots.txt" ] && [ "$ua" != 'Twitterbot/1.0' ] && continue
      curl -s -m 25 --compressed -A "$ua" -D h.txt -o b.txt "$host$path"
      st=$(head -1 h.txt | tr -d '\r')
      echo "=== $host$path"
      echo "UA: $ua"
      echo "status: $st"
      grep -i -E '^(cf-mitigated|server|content-type|location|cf-ray|x-robots-tag):' h.txt | tr -d '\r' | sed 's/^/  /'
      if [ "$path" = "/robots.txt" ]; then head -c 1500 b.txt; echo; continue; fi
      grep -o -i -E '<title>[^<]*</title>|<meta (property|name)="(og:title|og:description|og:image|twitter:card)" content="[^"]*"' b.txt | sed 's/^/  /' | cut -c1-220
      grep -q -i 'just a moment\|challenge-platform\|cf-chl' b.txt && echo "  ** Cloudflare challenge page **"
    done
  done
done

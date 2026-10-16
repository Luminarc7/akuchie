#!/bin/bash
o=probe_out/fonts; mkdir -p $o
for f in yujiboku/YujiBoku-Regular.ttf yujisyuku/YujiSyuku-Regular.ttf yujimai/YujiMai-Regular.ttf kaiseitokumin/KaiseiTokumin-ExtraBold.ttf zenantique/ZenAntique-Regular.ttf; do
  curl -sSL -o $o/$(basename $f) -w "$f %{http_code} %{size_download}\n" "https://raw.githubusercontent.com/google/fonts/main/ofl/$f"
done > probe_out/fonts_log.txt 2>&1

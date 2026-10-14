#!/bin/bash
UA='Mozilla/5.0 (compatible; Warujie/1.0; +https://warujie.jp)'
o=probe_out/terms; mkdir -p $o
get() { curl -sSL -A "$UA" --max-time 40 -o "$o/$1" -w "$1 %{http_code} %{url_effective}\n" "$2" || echo "$1 FAIL"; sleep 3; }
get mtgwiki_about.html "http://mtgwiki.com/index.php?title=MTG_Wiki:MTG_Wiki%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6"
get mtgwiki_disclaimer.html "http://mtgwiki.com/index.php?title=MTG_Wiki:%E5%85%8D%E8%B2%AC%E4%BA%8B%E9%A0%85"
get mtgwiki_yobikake.html "http://mtgwiki.com/index.php?title=MTG_Wiki:%E5%88%A9%E7%94%A8%E8%80%85%E3%81%B8%E3%81%AE%E5%91%BC%E3%81%B3%E3%81%8B%E3%81%91"
get mtgwiki_spite.html "http://mtgwiki.com/index.php?search=Spite+Malice&title=%E7%89%B9%E5%88%A5:%E6%A4%9C%E7%B4%A2"
get gatherer_dmr208_ja.html "https://gatherer.wizards.com/DMR/ja-jp/208"
get gatherer_inv293_ja.html "https://gatherer.wizards.com/INV/ja-jp/293"
get gatherer_dmr208_en.html "https://gatherer.wizards.com/DMR/en-us/208"

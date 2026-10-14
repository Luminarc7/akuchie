#!/bin/bash
UA='Mozilla/5.0 (compatible; Warujie/1.0; +https://warujie.jp)'
o=probe_out/terms; mkdir -p $o
get() { curl -sSL -A "$UA" --max-time 40 -o "$o/$1" -w "$1 %{http_code} %{url_effective}\n" "$2" || echo "$1 FAIL"; sleep 2; }
get mtgwiki_robots.txt "http://mtgwiki.com/robots.txt"
get mtgwiki_copyright.html "http://mtgwiki.com/wiki/MTG_Wiki:%E8%91%97%E4%BD%9C%E6%A8%A9"
get mtgwiki_about.html "http://mtgwiki.com/wiki/MTG_Wiki:MTG_Wiki%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6"
get mtgwiki_disclaimer.html "http://mtgwiki.com/wiki/MTG_Wiki:%E5%85%8D%E8%B2%AC%E4%BA%8B%E9%A0%85"
get mtgwiki_spite.html "http://mtgwiki.com/wiki/%E6%82%AA%E6%84%8F%EF%BC%8F%E6%95%B5%E6%84%8F"
get mtgwiki_main.html "http://mtgwiki.com/"
get gatherer_robots.txt "https://gatherer.wizards.com/robots.txt"
get gatherer_home.html "https://gatherer.wizards.com/"
get wizards_terms.html "https://company.wizards.com/en/legal/terms"
get wizards_terms_ja.html "https://company.wizards.com/ja/legal/terms"
get gatherer_spite_search.html "https://gatherer.wizards.com/search?name=Spite"

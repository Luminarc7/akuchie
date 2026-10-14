#!/bin/bash
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'
o=probe_out/support; mkdir -p $o
get() { curl -sSL -A "$UA" --max-time 40 -o "$o/$1" -w "$1 %{http_code} %{url_effective}\n" "$2" || echo "$1 FAIL"; sleep 2; }
get magic_new.html "https://magic-support.wizards.com/hc/en-us/requests/new"
get magic_forms.json "https://magic-support.wizards.com/api/v2/ticket_forms.json"
get support_new.html "https://support.wizards.com/hc/en-us/requests/new"
get support_forms.json "https://support.wizards.com/api/v2/ticket_forms.json"
get support_home.html "https://support.wizards.com/hc/en-us"

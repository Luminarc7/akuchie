"""One-off: how each Japanese MTG shop's product search works (form action and
field names, and which search URL answers with results for a card name)."""
import json, re, urllib.request, urllib.parse, html
H = {"User-Agent": "Mozilla/5.0 (warujie.jp link check)", "Accept-Language": "ja"}
SHOPS = """singlestar.jp cardshop-serra.com dorasuta.jp enndalgames.com blackfrog.jp johnnymagic.jp eternal-blue.jp bigredmtg.com
amenitydream.com ka-nabell.com mtg-guild.com arcana-tcg.com cantripmtg.com hasuya.jp pinocchio-mtg.jp azumayamtg.com cardshophamaya.com
toretoku.jp fullcomp.jp suruga-ya.jp c-labo-online.jp yellowsubmarine.co.jp cardrush-mtg.jp hareruyamtg.com mtg.bigweb.co.jp tokyomtg.com
mtgnage.jp playfirstgames.jp shikanotsunomtg.com advantagemtg.jp cardshopsatopin.net""".split()
TRY = ["/product-list?keyword={q}", "/search?q={q}", "/?mode=srh&keyword={q}", "/products/search?product={q}", "/shop/shopbrand.html?search={q}",
       "/search?keyword={q}", "/products?keyword={q}", "/search.php?keyword={q}"]
def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=10) as r:
            b = r.read(800000)
            enc = r.headers.get_content_charset() or "utf-8"
            try: t = b.decode(enc, "replace")
            except LookupError: t = b.decode("utf-8", "replace")
            return r.status, r.geturl(), t
    except Exception as e:
        return getattr(e, "code", None) or str(e)[:80], url, ""
from concurrent.futures import ThreadPoolExecutor
def probe(d):
    rec = {}
    for base in (f"https://www.{d}", f"https://{d}"):
        st, final, t = get(base + "/")
        if t:
            rec["home"] = [st, final]
            forms = []
            for m in re.finditer(r"<form\b([^>]*)>(.*?)</form>", t, re.S | re.I):
                attrs, body = m.group(1), m.group(2)
                act = re.search(r'action=["\']([^"\']*)', attrs)
                names = re.findall(r'<(?:input|select)\b[^>]*name=["\']([^"\']+)', body, re.I)
                if act and (re.search(r"search|keyword|srh|find|query", (act.group(1) + " ".join(names)), re.I)):
                    forms.append({"action": html.unescape(act.group(1)), "method": (re.search(r'method=["\'](\w+)', attrs) or [None, "get"])[1], "names": names[:8]})
            rec["forms"] = forms[:4]
            rec["title"] = html.unescape((re.search(r"<title>(.*?)</title>", t, re.S | re.I) or [None, ""])[1].strip())[:80]
            rec["base"] = base
            break
    else:
        rec["home"] = [st, base]
    base = rec.get("base")
    if base:
        tries = []
        acts = [f["action"] for f in rec.get("forms", [])]
        for pat in TRY:
            url = base + pat.format(q=urllib.parse.quote("稲妻"))
            st, final, t = get(url)
            tries.append({"url": url, "status": st, "final": final if final != url else "", "hits": t.count("稲妻")})
            if t.count("稲妻") >= 3: break
        rec["tries"] = tries
    print(d, rec.get("home"), rec.get("forms"), flush=True)
    return d, rec
with ThreadPoolExecutor(12) as ex:
    out = dict(ex.map(probe, SHOPS))
json.dump(out, open("tools/shops.json", "w"), ensure_ascii=False, indent=1)

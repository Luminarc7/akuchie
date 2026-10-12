"""One-off (2): Single Star's search, Dragon Star, and shops whose search may
need EUC-JP (Color Me Shop) or English names."""
import json, re, urllib.request, urllib.parse, html
from concurrent.futures import ThreadPoolExecutor
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36", "Accept-Language": "ja,en;q=0.8"}
def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=12) as r:
            b = r.read(1500000)
            enc = r.headers.get_content_charset()
            if not enc:
                m = re.search(rb'charset=["\']?([\w-]+)', b[:3000]); enc = m.group(1).decode() if m else "utf-8"
            try: t = b.decode(enc, "replace")
            except LookupError: t = b.decode("utf-8", "replace")
            return r.status, r.geturl(), t, enc
    except Exception as e:
        return getattr(e, "code", None) or str(e)[:80], url, "", ""
def snip(t, word, n=3, w=160):
    out = []
    for m in re.finditer(re.escape(word), t):
        out.append(re.sub(r"\s+", " ", t[max(0, m.start() - w):m.end() + w]))
        if len(out) >= n: break
    return out
Q = "稲妻"
E = urllib.parse.quote(Q.encode("euc-jp")); S = urllib.parse.quote(Q.encode("shift_jis")); U = urllib.parse.quote(Q)
EN = urllib.parse.quote("Lightning Bolt")
URLS = {
 "singlestar_home": "https://www.singlestar.jp/",
 "singlestar_pl": f"https://www.singlestar.jp/product-list?keyword={U}",
 "singlestar_pl_submit": f"https://www.singlestar.jp/product-list?keyword={U}&Submit=",
 "singlestar_en": f"https://www.singlestar.jp/product-list?keyword={EN}",
 "dorasuta_mtg": "https://dorasuta.jp/mtg/",
 "dorasuta_search": f"https://dorasuta.jp/mtg/product-list?kw={U}",
 "mtgguild_utf8": f"https://mtg-guild.com/?mode=srh&keyword={U}",
 "mtgguild_euc": f"https://mtg-guild.com/?mode=srh&keyword={E}",
 "mtgguild_en": f"https://mtg-guild.com/?mode=srh&keyword={EN}",
 "enndal_home": "https://www.enndalgames.com/",
 "enndal_euc": f"https://www.enndalgames.com/?mode=srh&keyword={E}",
 "arcana_home": "https://www.arcana-tcg.com/",
 "arcana_euc": f"https://www.arcana-tcg.com/?mode=srh&keyword={E}",
 "hasuya_home": "https://www.hasuya.jp/",
 "hasuya_euc": f"https://www.hasuya.jp/?mode=srh&keyword={E}",
 "azumaya_home": "https://azumayamtg.com/",
 "azumaya_euc": f"https://azumayamtg.com/?mode=srh&keyword={E}",
 "toretoku_home": "https://www.toretoku.jp/",
 "fullcomp_home": "https://www.fullcomp.jp/",
 "yellow_home": "https://www.yellowsubmarine.co.jp/",
 "blackfrog_euc": f"https://blackfrog.jp/shop/shopbrand.html?search={E}",
 "blackfrog_utf8": f"https://blackfrog.jp/shop/shopbrand.html?search={U}",
 "cardrush_en": f"https://www.cardrush-mtg.jp/product-list?keyword={EN}",
 "serra_en": f"https://cardshop-serra.com/search?q={EN}",
 "cantrip_en": f"https://cantripmtg.com/search?q={EN}",
 "hamaya_en": f"https://www.cardshophamaya.com/product-list?keyword={EN}",
}
def probe(item):
    k, url = item
    st, final, t, enc = get(url)
    forms = []
    for m in re.finditer(r"<form\b([^>]*)>(.*?)</form>", t, re.S | re.I):
        act = re.search(r'action=["\']([^"\']*)', m.group(1))
        names = re.findall(r'name=["\']([^"\']+)["\'](?:[^>]*value=["\']([^"\']*))?', m.group(2))
        forms.append({"action": html.unescape(act.group(1)) if act else "", "fields": names[:6]})
    return k, {"url": url, "status": st, "final": final, "enc": enc, "len": len(t),
               "title": html.unescape((re.search(r"<title>(.*?)</title>", t, re.S | re.I) or [None, ""])[1].strip())[:90],
               "hits_ja": t.count(Q), "hits_en": t.count("Lightning Bolt"), "forms": forms[:6],
               "kw": snip(t, "keyword", 4) + snip(t, "検索", 2), "result_snip": snip(t, Q, 2)}
with ThreadPoolExecutor(10) as ex:
    out = dict(ex.map(probe, URLS.items()))
json.dump(out, open("tools/shops2.json", "w"), ensure_ascii=False, indent=1)

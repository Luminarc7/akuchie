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
 "enndal": f"https://www.enndalgames.com/products/list.php?mode=search&name={U}",
 "enndal_en": f"https://www.enndalgames.com/products/list.php?mode=search&name={EN}",
 "hasuya": f"https://www.hasuya.jp/products/list?name={U}",
 "hasuya_en": f"https://www.hasuya.jp/products/list?name={EN}",
 "azumaya": f"https://azumayamtg.com/products/list?name={U}",
 "azumaya_en": f"https://azumayamtg.com/products/list?name={EN}",
 "blackfrog_other": f"https://blackfrog.jp/shop/shopbrand.html?search={urllib.parse.quote('ゼロ除算'.encode('euc-jp'))}",
 "singlestar": f"https://www.singlestar.jp/product-list?keyword={U}",
 "mtgguild_en": f"https://mtg-guild.com/?mode=srh&keyword={EN}",
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
json.dump(out, open("tools/shops3.json", "w"), ensure_ascii=False, indent=1)

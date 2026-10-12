"""One-off: is the live warujie.jp the version just pushed?"""
import json, urllib.request, hashlib
out = {}
for path in ("", "preview.html"):
    req = urllib.request.Request("https://warujie.jp/" + path + "?v=ae06c50", headers={"User-Agent": "Mozilla/5.0 warujie deploy check"})
    with urllib.request.urlopen(req, timeout=30) as r:
        b = r.read(); t = b.decode("utf-8", "replace")
    out[path or "index"] = {"status": r.status, "bytes": len(b), "sha1": hashlib.sha1(b).hexdigest(),
        "markers": {k: k in t for k in ['class="meta-bar"', "JP_SHOP_SEARCH", "シングルスター", "HERO_SLANG", "similarBox", "meta-illus\"", "noindex"]}}
json.dump(out, open("tools/shops_live.json", "w"), indent=1, ensure_ascii=False)
req = urllib.request.Request("https://warujie.jp/?v=ae06c50b", headers={"User-Agent": "Mozilla/5.0 warujie deploy check"})
with urllib.request.urlopen(req, timeout=30) as r:
    open("tools/live_index.html", "wb").write(r.read())
    open("tools/live_headers.txt", "w").write(str(r.headers))

import json, os, time, urllib.request
UA = {"User-Agent": "warujie.jp-probe/1.0 (+https://warujie.jp)", "Accept": "application/json"}
os.makedirs("probe_out/symbols", exist_ok=True)
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read()
data = json.loads(get("https://api.scryfall.com/symbology"))["data"]
json.dump(data, open("probe_out/symbology.json", "w"), ensure_ascii=False)
for s in data:
    u = s.get("svg_uri")
    if not u: continue
    name = u.rsplit("/", 1)[1]
    try:
        open("probe_out/symbols/" + name, "wb").write(get(u))
    except Exception as e:
        print("fail", u, e)
    time.sleep(0.12)
print("done", len(data))

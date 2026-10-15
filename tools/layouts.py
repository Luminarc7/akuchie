#!/usr/bin/env python3
"""Probe: each oracle card's Scryfall layout (split, transform, modal_dfc,
adventure, flip, meld, ...) from the oracle_cards bulk file. Writes
probe_out/layouts.json {oracle_id: layout} for every non-"normal" layout and
probe_out/layouts_stats.txt with counts and examples."""
import gzip, io, json, collections, urllib.request
H = {"User-Agent": "WarujieLayoutProbe/1.0 (warujie.jp)", "Accept": "application/json"}
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=600)
bulk = json.load(get("https://api.scryfall.com/bulk-data"))
entry = next(b for b in bulk["data"] if b["type"] == "oracle_cards")
url = entry.get("jsonl_download_uri") or entry["download_uri"]
print("downloading", url)
raw = get(url).read()
if raw[:2] == b"\x1f\x8b":
    raw = gzip.decompress(raw)
text = raw.decode("utf-8")
cards = [json.loads(l) for l in text.splitlines() if l.strip()] if url.endswith(("jsonl", "jsonl.gz")) or not text.lstrip().startswith("[") else json.loads(text)
out, count, ex = {}, collections.Counter(), collections.defaultdict(list)
for c in cards:
    oid = c.get("oracle_id") or ((c.get("card_faces") or [{}])[0].get("oracle_id"))
    lay = c.get("layout", "")
    count[lay] += 1
    if len(ex[lay]) < 8:
        ex[lay].append(c.get("name"))
    if oid and lay and lay != "normal":
        out[oid] = lay
json.dump(out, open("probe_out/layouts.json", "w"), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
with open("probe_out/layouts_stats.txt", "w") as f:
    f.write(f"{len(cards)} oracle cards, {len(out)} non-normal\n")
    for lay, n in count.most_common():
        f.write(f"{lay}\t{n}\t{ex[lay]}\n")
print(open("probe_out/layouts_stats.txt").read())

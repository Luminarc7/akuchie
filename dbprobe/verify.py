"""After the 2026-10-17 fixes: the test site in English opens English printings from Japanese links;
the searches that were wrong; the metagame ordinals. Read-only visits to the test site (and Scryfall
through the site's own page, which spaces its requests)."""
import json, time
from playwright.sync_api import sync_playwright
import os, hashlib, gzip, urllib.request
BASE = os.environ.get("BASE", "https://warujie.warujie-mtg.workers.dev/")
IDS = json.load(open("dbprobe/en_ids.json"))
out = {"cards": [], "search": {}, "meta": None, "base": BASE}
def get(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (warujie.jp publish check)", "Accept-Encoding": "gzip"}), timeout=60)
    body = r.read()
    if body[:2] == b"\x1f\x8b": body = gzip.decompress(body)
    return r.status, body
st, html = get(BASE)
out["index_sha256"] = hashlib.sha256(html).hexdigest(); out["index_status"] = st
st, pr = get(BASE + "printings.json.gz"); out["printings"] = [st, len(pr)]
COLLECT = r"""() => ({ url: location.search, name: (document.querySelector('.cp-name') || {}).textContent || '',
  art: [...document.querySelectorAll('div.cp-art img')].map(i => i.currentSrc || i.src).slice(0, 2),
  flavor: (document.querySelector('p.cp-flavor') || {}).textContent || '',
  pressed: [...document.querySelectorAll('#printSlot [aria-pressed=true]')].map(b => b.dataset.print) })"""
with sync_playwright() as p:
    b = p.chromium.launch()
    for lang in ("en", "ja"):
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        ctx.add_init_script(f"try {{ localStorage.setItem('akuchie-lang', '{lang}'); }} catch (e) {{}}")
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)[:200]))
        for cid, name in IDS:
            page.goto(BASE + "?card=" + cid)
            try:
                page.wait_for_selector(".cp-name", timeout=30000); page.wait_for_selector("#printSlot .print-lang", timeout=15000)
            except Exception as e: errs.append("wait " + name)
            page.wait_for_timeout(1500)
            out["cards"].append(dict(page.evaluate(COLLECT), lang=lang, asked=cid, card=name))
        if lang == "en":
            page.goto(BASE + "?card=" + IDS[-1][0]); page.wait_for_timeout(3500)
            page.screenshot(path="probe_out/verify/en-card.png")
            page.goto(BASE + "?view=meta"); page.wait_for_timeout(5000)
            out["meta"] = page.evaluate("[...document.querySelectorAll('.meta-sample a')].map(a => a.textContent).slice(0, 12)")
            page.screenshot(path="probe_out/verify/en-meta.png")
        else:
            page.goto(BASE); page.wait_for_function("typeof dbState !== 'undefined' && dbState !== 'loading'", timeout=60000)
            out["search"] = page.evaluate("""() => { const st = Object.assign({}, state, { colors: new Set(), types: new Set(), creatureTypes: new Set(), keywords: new Set(),
              manaCosts: new Set(), roles: new Set(), rarity: new Set(), format: '', sort: '', showLoose: false });
              const r = q => searchRows(q, st);
              return Object.fromEntries(['到達', 'ボーダーレス版', 'ボーダーレスのドラゴン', '日本語版のカード', 'シリアル番号', 'セット:イニストラード', 'e:mid', 'e:vow', '日本語版 ボーダーレス', '追放'].map(q => {
                const x = r(q); return [q, { n: x.rows.length, top: x.rows.slice(0, 8).map(y => y.name_ja || y.name_en), last: x.rows.slice(-4).map(y => y.name_ja || y.name_en),
                  note: (x.info.aliases || []).map(a => a.from + '>' + a.to) }]; })); }""")
            page.fill("#heroInput", "ボーダーレスのドラゴン"); page.press("#heroInput", "Enter"); page.wait_for_timeout(4000)
            page.screenshot(path="probe_out/verify/ja-search.png")
        out["errors_" + lang] = errs
        ctx.close()
    b.close()
json.dump(out, open("probe_out/verify/result.json", "w"), ensure_ascii=False, indent=1)
print("done", len(out["cards"]))

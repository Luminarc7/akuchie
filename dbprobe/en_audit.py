"""English-mode audit of the test site (and the live Worker for comparison): Japanese text and
Japanese card pictures shown while the site is in English, page errors, on every kind of page."""
import json, re, sys, time, urllib.parse, urllib.request
from playwright.sync_api import sync_playwright
UA = {"User-Agent": "warujie.jp site audit (GitHub Actions)", "Accept": "application/json"}
CANDIDATES = {"staging": ["https://staging-warujie.warujie-mtg.workers.dev/"],
              "live": ["https://warujie.warujie-mtg.workers.dev/", "https://main-warujie.warujie-mtg.workers.dev/"]}
IDS = json.load(open("dbprobe/en_ids.json"))
QUERIES = ["lightning bolt", "dragon", "removal", "flying lifelink", "sol ring", "t:goblin c:r", "draw a card", "ragavan",
           "e:mh3", "borderless dragon", "is:showcase", "r:m angel", "counterspell", "wear tear", "delver",
           "稲妻", "除去", "ボーダーレス", "日本語版 ショーケース", "旧枠"]
COLLECT = r"""() => {
  const JA = /[぀-ヿ㐀-鿿]/;
  const vis = el => el && (el.checkVisibility ? el.checkVisibility() : !!el.offsetParent);
  const path = el => { const p = []; for (let e = el, i = 0; e && e !== document.body && i < 4; i++, e = e.parentElement)
    p.push(e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.classList.length ? '.' + [...e.classList].slice(0, 2).join('.') : '')); return p.join(' < '); };
  const ja = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n;
  while ((n = w.nextNode())) { const t = n.textContent.trim(); if (t && JA.test(t) && vis(n.parentElement)) ja.push({ t: t.slice(0, 70), path: path(n.parentElement) }); }
  document.querySelectorAll('[title],[alt],[aria-label],[placeholder]').forEach(el => { if (!vis(el)) return;
    for (const a of ['title', 'alt', 'aria-label', 'placeholder']) { const v = el.getAttribute(a); if (v && JA.test(v)) ja.push({ t: '@' + a + ': ' + v.slice(0, 60), path: path(el) }); } });
  const imgs = [...document.querySelectorAll('img')].filter(vis).map(i => [i.currentSrc || i.src, path(i)]).filter(x => x[0].includes('cards.scryfall.io'));
  const links = [...document.querySelectorAll('a[href*="card="]')].filter(vis).map(a => [new URL(a.href).searchParams.get('card'), path(a)]);
  return { title: document.title, ja, imgs, links, lang: document.documentElement.lang };
}"""
def pick_base(cands):
    for b in cands:
        try:
            html = urllib.request.urlopen(urllib.request.Request(b, headers={"User-Agent": UA["User-Agent"]}), timeout=30).read().decode("utf-8", "replace")
            if "悪知恵" in html and "LANG" in html: return b
            print("not the site:", b, html[:120].replace("\n", " "))
        except Exception as e: print("unreachable:", b, e)
    return None
def audit(p, base, label):
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script("try { localStorage.setItem('akuchie-lang', 'en'); } catch (e) {}")
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(("pageerror", str(e)[:300])))
    page.on("console", lambda m: errs.append(("console", m.text[:300])) if m.type == "error" else None)
    views = {}
    def grab(name, wait=1800):
        page.wait_for_timeout(wait)
        try: views[name] = dict(page.evaluate(COLLECT), errors=list(errs), url=page.url)
        except Exception as e: views[name] = {"fail": str(e)[:300]}
        errs.clear()
    def go(url, ready=None, wait=1800):
        page.goto(base + url)
        try:
            page.wait_for_function("typeof dbState !== 'undefined' && dbState !== 'loading'", timeout=60000)
            if ready: page.wait_for_selector(ready, timeout=30000)
        except Exception as e: errs.append(("wait", str(e)[:200]))
    def search(q):
        sel = "#searchInput" if page.locator("#searchInput").is_visible() else "#heroInput"
        page.fill(sel, q); page.press(sel, "Escape"); page.press(sel, "Enter")
        try: page.wait_for_function("document.querySelector('#resultCount') && /found|result|件/.test(document.querySelector('#resultCount').textContent)", timeout=30000)
        except Exception as e: errs.append(("search", q, str(e)[:120]))
    go("", "#homeHero"); grab("home", 4000)
    for q in QUERIES:
        search(q); grab("search: " + q, 2500)
        if q == "dragon":
            try:
                for i in range(3): page.locator("#cardGrid .want-tog").nth(i).click()
            except Exception as e: errs.append(("want", str(e)[:100]))
    # card pages: from a search's first tiles, then direct links to Japanese printings
    search("dragon"); page.wait_for_timeout(2500)
    hrefs = page.evaluate("[...document.querySelectorAll('#cardGrid .card-tile')].slice(0, 4).map(a => a.getAttribute('href'))")
    for h in hrefs:
        go(h, ".cp-name"); grab("card from tile " + h, 3500)
    for cid, name in IDS:
        go("?card=" + cid, ".cp-name"); grab("card direct " + name, 3500)
    go("?view=sets", None); grab("sets", 3000)
    go("?set=mh3", "#setGrid .card-tile"); grab("set mh3", 3000)
    go("?set=fin", "#setGrid .card-tile"); grab("set fin", 3000)
    go("?view=meta", None); grab("meta", 4000)
    deck = page.evaluate("(() => { const a = document.querySelector('a[href*=\"view=deck\"]'); return a ? a.getAttribute('href') : ''; })()")
    if deck: go(deck, None); grab("deck page", 4000)
    go("?view=prices", None); grab("price movers", 4000)
    go("?view=import&list=" + urllib.parse.quote("4 Lightning Bolt\n4 Ragavan, Nimble Pilferer\n2 Fable of the Mirror-Breaker\n20 Mountain"), None); grab("deck price page", 5000)
    go("?view=want", None); grab("want list", 4000)
    page.screenshot(path=f"probe_out/en/{label}-want.png")
    go("", "#homeHero"); page.wait_for_timeout(3000); page.screenshot(path=f"probe_out/en/{label}-home.png", full_page=True)
    b.close()
    return views
def langs_of(ids):
    out = {}
    ids = sorted(ids)
    for i in range(0, len(ids), 75):
        body = json.dumps({"identifiers": [{"id": x} for x in ids[i:i + 75]]}).encode()
        req = urllib.request.Request("https://api.scryfall.com/cards/collection", data=body, headers=dict(UA, **{"Content-Type": "application/json"}))
        for c in json.load(urllib.request.urlopen(req))["data"]:
            out[c["id"]] = [c.get("lang"), c.get("name"), c.get("set"), c.get("collector_number")]
        time.sleep(0.2)
    return out
result = {}
with sync_playwright() as p:
    for label, cands in CANDIDATES.items():
        base = pick_base(cands)
        print(label, "->", base)
        if base: result[label] = {"base": base, "views": audit(p, base, label)}
ids = set()
for r in result.values():
    for v in r["views"].values():
        for src, _ in v.get("imgs", []):
            m = re.search(r"/([0-9a-f]{8}-[0-9a-f-]{27})\.jpg", src)
            if m: ids.add(m.group(1))
        for cid, _ in v.get("links", []):
            if cid and re.match(r"^[0-9a-f-]{36}$", cid): ids.add(cid)
result["printings"] = langs_of(ids)
json.dump(result, open("probe_out/en/audit.json", "w"), ensure_ascii=False, indent=0)
print("views:", {k: len(v["views"]) for k, v in result.items() if k != "printings"}, "printings looked up:", len(result["printings"]))

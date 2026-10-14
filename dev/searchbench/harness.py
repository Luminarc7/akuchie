"""Search benchmark: the real card database and real role tags, in a real browser.

usage: python3 bench.py <index.html> <out.json> [cpu_throttle]
Scryfall and fonts are stubbed (instant), so the numbers are the site's own work.
"""
import gzip, json, sys, time, urllib.parse
from playwright.sync_api import sync_playwright

HTML = None
import os as _os
D = _os.path.dirname(_os.path.abspath(__file__)) + "/"
REPO = _os.path.abspath(_os.path.join(D, "..", "..")) + "/"
DB = open(REPO + "ja_cards.json.gz", "rb").read()
TAGS = open(D + "tags_real.json.gz", "rb").read()
PIDX = open(D + "price_index.json", "rb").read()
SITE = "https://warujie.jp/"

_db = json.loads(gzip.decompress(DB))
ROWS = {r[0]: dict(zip(_db["fields"], r)) for r in _db["cards"]}
BY_ORACLE = {r["oracle_id"]: r for r in ROWS.values()}


def sf_card(r):
    return {"object": "card", "id": r["id"], "oracle_id": r["oracle_id"], "lang": "ja" if r["name_ja"] else "en", "set": r["set"],
            "collector_number": "1", "name": r["name_en"], "printed_name": r["name_ja"] or None, "type_line": r["type_en"],
            "printed_type_line": r["type_ja"] or None, "oracle_text": r["oracle_en"], "printed_text": r["oracle_ja"] or None,
            "mana_cost": r["mana_cost"], "colors": list(r["colors"] or ""), "cmc": r["cmc"], "rarity": r["rarity"], "set_name": r["set"].upper(),
            "image_uris": {"small": "https://cards.scryfall.io/small/x.jpg", "normal": "https://cards.scryfall.io/normal/x.jpg"},
            "legalities": {}, "prices": {}}


def handle(route):
    u = urllib.parse.urlparse(route.request.url)
    if u.netloc == "api.scryfall.com":
        if u.path == "/cards/collection":
            out = []
            for ident in json.loads(route.request.post_data)["identifiers"]:
                r = ROWS.get(ident.get("id")) or BY_ORACLE.get(ident.get("oracle_id"))
                if r: out.append(sf_card(r))
            return route.fulfill(status=200, content_type="application/json", body=json.dumps({"object": "list", "data": out}))
        return route.fulfill(status=404, content_type="application/json", body='{"object":"error"}')
    if u.netloc == "cards.scryfall.io":
        return route.fulfill(status=200, content_type="image/svg+xml", body='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 488 680"/>')
    if u.netloc == "warujie.jp":
        p = u.path.lstrip("/")
        if p in ("", "index.html"):
            return route.fulfill(status=200, content_type="text/html; charset=utf-8", body=HTML)
        if p.startswith("meta_lists/") or p in ("manifest.webmanifest", "sw.js") or p.startswith("icons/"):
            import os
            f = REPO + p
            return route.fulfill(status=200, body=open(f, "rb").read()) if os.path.isfile(f) else route.fulfill(status=404, body="")
        if p in ("meta.json", "meta_decks.json", "combo_ja.js"):
            return route.fulfill(status=200, body=open(REPO + p, "rb").read())
        if p == "ja_cards.json.gz":
            return route.fulfill(status=200, content_type="application/gzip", body=DB)
        return route.fulfill(status=404, body="")
    if u.netloc == "warujie.github.io":
        if u.path.endswith("/t/tags.json.gz"):
            return route.fulfill(status=200, content_type="application/gzip", body=TAGS)
        if u.path.endswith("/index.json"):
            return route.fulfill(status=200, content_type="application/json", body=PIDX)
        return route.fulfill(status=404, body="")
    return route.fulfill(status=404, body="")




def open_page(p, html, wait_tags=True):
    global HTML
    HTML = html
    b = p.chromium.launch(args=["--enable-precise-memory-info", "--js-flags=--expose-gc"])
    page = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.route("**/*", handle)
    navs = []
    page.on("framenavigated", lambda f: navs.append(f.url) if f == page.main_frame else None)
    page.goto(SITE)
    page.wait_for_load_state("load")
    page.wait_for_timeout(300)
    page.wait_for_function("typeof dbState !== 'undefined' && dbState === 'ready'", timeout=180000)
    if wait_tags:
        page.evaluate("loadTags().then(() => 1)")
    if len(navs) > 1: print("NAVIGATIONS:", navs)
    return b, page, errs

RUN = """(qs) => {
  const st = Object.assign({}, state, { colors: new Set(), types: new Set(), creatureTypes: new Set(), keywords: new Set(),
    manaCosts: new Set(), roles: new Set(), rarity: '', format: '', sort: '', showLoose: false });
  return qs.map(q => { const t = performance.now(); try { const r = searchRows(q, st);
    return { q, ms: performance.now() - t, n: r.rows.length, top: r.rows.slice(0, 8).map(x => x.name_ja || x.name_en), fixes: (r.info.fixes || []).map(f => f.from + '>' + f.to) };
  } catch (e) { return { q, err: String(e && e.stack || e).slice(0, 400) }; } });
}"""

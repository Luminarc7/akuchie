"""Search checks with the real card database and the real role data (round 13).

usage: python3 search_checks.py <index.html>
"""
import json, sys, time
from playwright.sync_api import sync_playwright
import harness

html = open(sys.argv[1], encoding="utf-8").read()
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "   " + str(detail)[:500]))


# network behaviour: count Scryfall requests, answer some with 429
SCRY = {"calls": [], "fail_next": 0}
orig = harness.handle


def handle(route):
    if route.request.url == "https://api.scryfall.com/cards/collection":
        SCRY["calls"].append(time.time())
        if SCRY["fail_next"] > 0:
            SCRY["fail_next"] -= 1
            return route.fulfill(status=429, content_type="application/json", body='{"object":"error","status":429}')
    return orig(route)


harness.handle = handle

with sync_playwright() as p:
    b, page, errs = harness.open_page(p, html)
    run = lambda qs: {r["q"]: r for r in page.evaluate(harness.RUN, qs)}
    RUN_POP = harness.RUN.replace("sort: ''", "sort: 'popular'")
    run_pop = lambda qs: {r["q"]: r for r in page.evaluate(RUN_POP, qs)}
    R = run(["らがばん", "じぇいす", "lightning", "bolt", "path", "force", "sol", "swords", "flyng", "o:", "t:", "c:", "e:", "-o:", "o:\"\"",
             "%", "🔥", "((", ":", "-", "--", "o: 稲妻", "名前:らがばん", "draw a card", "飛行", "除去", "稲妻", "lightning bolt",
             "sacrifise", "permanants", "t:クリーチャー c:r cmc<=2", "ジェイス", "とげの稲妻", "トゲノイナズマ"])
    top = lambda q, k=5: R[q].get("top", [])[:k]
    check("hiragana finds katakana names: らがばん -> ラガバン", any("ラガバン" in n for n in top("らがばん")), R["らがばん"])
    check("hiragana finds katakana names: じぇいす -> ジェイス cards", R["じぇいす"]["n"] >= 30 and all("ジェイス" in n for n in top("じぇいす")), R["じぇいす"])
    check("名前:らがばん also folds kana", any("ラガバン" in n for n in top("名前:らがばん")), R["名前:らがばん"])
    check("a name with hiragana still matches as typed: とげの稲妻", top("とげの稲妻")[:1] == ["とげの稲妻"], R["とげの稲妻"])
    P = run_pop(["lightning", "bolt", "path", "force", "sol", "swords", "draw a card"])
    ptop = lambda q, k=5: P[q].get("top", [])[:k]
    check("most played order: lightning -> Lightning Greaves, Lightning Bolt", ptop("lightning", 2) == ["稲妻のすね当て", "稲妻"], ptop("lightning"))
    check("most played order: bolt -> Lightning Bolt in the top 3", "稲妻" in ptop("bolt", 3), ptop("bolt"))
    check("most played order: path -> Path to Exile in the top 3", "流刑への道" in ptop("path", 3), ptop("path"))
    check("most played order: force -> Force of Will in the top 5", "意志の力" in ptop("force", 5), ptop("force"))
    check("most played order: sol -> Sol Ring first", ptop("sol")[0] == "太陽の指輪", ptop("sol"))
    check("most played order: swords -> Swords to Plowshares first", ptop("swords")[0] == "剣を鍬に", ptop("swords"))
    check("most played order: draw a card -> Rhystic Study, Mind Stone near the top", "リスティックの研究" in ptop("draw a card", 5) and "精神石" in ptop("draw a card", 5), ptop("draw a card"))
    # the default order: best match, then あいうえお by the name's reading (English-only cards after them)
    prop = page.evaluate("""(qs) => {
      const st = Object.assign({}, state, { colors: new Set(), types: new Set(), creatureTypes: new Set(), keywords: new Set(), manaCosts: new Set(), roles: new Set(), rarity: '', format: '', sort: '', showLoose: false });
      return qs.map(q => {
        const r = searchRows(q, st), rows = r.rows;
        const grp = row => [r.info.grades.has(row) ? r.info.grades.get(row).tier : 1, relevance(row, q), r.info.grades.has(row) ? Math.floor(r.info.grades.get(row).score * 2) / 2 : 0].join('|');
        let bad = 0, firstBad = null;
        for (let i = 1; i < rows.length; i++) {
          if (grp(rows[i]) !== grp(rows[i - 1]) || r.info.roles.length) continue;
          if (jaSortKey(rows[i - 1]) > jaSortKey(rows[i])) { bad++; if (!firstBad) firstBad = [rows[i - 1].name_ja, rows[i].name_ja]; }
        }
        const enOnly = rows.findIndex(x => !x.name_ja), jaAfter = enOnly >= 0 && rows.slice(enOnly).some(x => x.name_ja && grp(x) === grp(rows[enOnly]));
        return { q, n: rows.length, bad, firstBad, jaAfter, head: rows.slice(0, 6).map(x => x.name_ja || x.name_en) };
      });
    }""", ["飛行", "破壊する", "ドラゴン", "トークン"])
    for r in prop:
        check(f"default order: {r['q']} - equal matches in あいうえお order, English-only cards last", r["bad"] == 0 and not r["jaAfter"], r)
    ro = page.evaluate("""() => { const st = Object.assign({}, state, { colors: new Set(), types: new Set(), creatureTypes: new Set(), keywords: new Set(), manaCosts: new Set(), roles: new Set(), rarity: '', format: '', sort: '', showLoose: false });
      const rows = searchRows('除去', st).rows.filter(x => x.name_ja).slice(0, 40); return rows.map(x => x.name_kana); }""")
    check("default order: role search 除去 runs あいうえお (first 40 by reading)", ro == sorted(ro), ro[:10])
    en = page.evaluate("""() => { LANG = 'en'; const st = Object.assign({}, state, { colors: new Set(), types: new Set(), creatureTypes: new Set(), keywords: new Set(), manaCosts: new Set(), roles: new Set(), rarity: '', format: '', sort: '', showLoose: false });
      const rows = searchRows('removal', st).rows.slice(0, 30).map(x => x._nameEn); LANG = 'ja'; return rows; }""")
    check("default order in English: A→Z", en == sorted(en), en[:8])
    kana = page.evaluate("(() => { const by = n => LOCAL_DB.find(r => r.name_ja === n); return ['稲妻','思考囲い','意志の力','ウルザの物語'].map(n => by(n) && by(n).name_kana); })()")
    check("readings are in the database and never shown: 稲妻 いなずま …", kana == ["いなずま", "しこうかこい", "いしのちから", "うるざのものがたり"], kana)
    ex = page.evaluate("['Fire // Ice', 'Delver of Secrets // Insectile Aberration', 'Bonecrusher Giant // Stomp', 'Unholy Annex // Ritual Chamber', 'Lightning Bolt'].map(exportName)")
    check("export names: split cards and Rooms as A // B, double-faced and adventure cards by the front face", ex == ["Fire // Ice", "Delver of Secrets", "Bonecrusher Giant", "Unholy Annex // Ritual Chamber", "Lightning Bolt"], ex)
    check("lightning bolt: the card itself first", top("lightning bolt")[0] == "稲妻", top("lightning bolt"))
    check("sol ring: the card itself first", run(["sol ring"])["sol ring"]["top"][0] == "太陽の指輪")
    check("稲妻: the card named exactly that first", top("稲妻")[0] == "稲妻", top("稲妻"))
    check("flyng is corrected to flying (not fling)", R["flyng"]["fixes"] == ["flyng>flying"] and R["flyng"]["n"] > 3000, R["flyng"])
    check("sacrifise / permanants still corrected", R["sacrifise"]["fixes"] == ["sacrifise>sacrifice"] and R["permanants"]["fixes"] == ["permanants>permanent"], (R["sacrifise"], R["permanants"]))
    allc = R["-"]["n"]
    for q in ("o:", "t:", "c:", "e:", "-o:", 'o:""', "-", "--"):
        check(f"an operator still being typed ({q}) is left out, not searched as a letter", R[q]["n"] == allc, (q, R[q]["n"], allc))
    check("o: 稲妻 = 稲妻 (the empty o: is left out)", R["o: 稲妻"]["n"] == R["稲妻"]["n"], (R["o: 稲妻"]["n"], R["稲妻"]["n"]))
    for q in ("%", "🔥", "(("):
        check(f"symbols only ({q}) are searched as they are (a handful of cards at most, not every card)", R[q]["n"] < 5, R[q])
    check(": finds the names and texts with a colon (not every card)", 0 < R[":"]["n"] < allc, R[":"]["n"])
    check("飛行: still several thousand cards", R["飛行"]["n"] > 4000, R["飛行"]["n"])
    check("除去: the same 6,340 role cards as before", R["除去"]["n"] == 6340, R["除去"]["n"])
    check("operators unchanged: t:クリーチャー c:r cmc<=2 = 1034", R["t:クリーチャー c:r cmc<=2"]["n"] == 1034, R["t:クリーチャー c:r cmc<=2"]["n"])
    check("no search throws", not any("err" in r for r in R.values()), [r for r in R.values() if "err" in r])

    # the same search twice: the second asks Scryfall nothing
    def search(q):
        sel = "#searchInput" if page.locator("#searchInput").is_visible() else "#heroInput"
        page.fill(sel, q); page.press(sel, "Escape"); page.press(sel, "Enter")
    search("稲妻"); page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length >= 20"); page.wait_for_timeout(500)
    search("太陽の指輪"); page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 1"); page.wait_for_timeout(500)
    n1 = len(SCRY["calls"])
    search("稲妻"); page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length >= 20"); page.wait_for_timeout(500)
    check("the same search again: the cards come from memory, no new Scryfall request", len(SCRY["calls"]) == n1, (n1, len(SCRY["calls"])))
    # Scryfall busy (429) twice: the pictures still arrive
    SCRY["fail_next"] = 2
    n2 = len(SCRY["calls"])
    sel = "#searchInput" if page.locator("#searchInput").is_visible() else "#heroInput"
    page.fill(sel, "ジェイス"); page.press(sel, "Escape"); page.press(sel, "Enter")
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile img').length >= 5", timeout=20000)
    check("Scryfall busy twice (429): tried again, the cards arrive with pictures", len(SCRY["calls"]) - n2 >= 3, len(SCRY["calls"]) - n2)
    gaps = [b2 - a for a, b2 in zip(SCRY["calls"], SCRY["calls"][1:])]
    check("Scryfall requests spaced out (100 ms when sent; arrival jitter allowed)", min(gaps) >= 0.05, [round(g, 3) for g in gaps])
    # load more, then a new search before it arrives: no old cards in the new results
    page.evaluate("""() => { const f = window.fetch; window.__slow = true;
      window.fetch = (u, o) => (window.__slow && String(u).includes('cards/collection') ? new Promise(r => setTimeout(r, 1200)).then(() => f(u, o)) : f(u, o)); }""")
    page.fill(sel, "飛行"); page.press(sel, "Escape"); page.press(sel, "Enter")
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length >= 30", timeout=20000)
    page.evaluate("document.getElementById('loadMoreBtn').click()")
    page.wait_for_timeout(100)
    page.evaluate("window.__slow = false")
    page.fill(sel, "太陽の指輪"); page.press(sel, "Escape"); page.press(sel, "Enter")
    page.wait_for_timeout(2500)
    names = page.evaluate("[...document.querySelectorAll('#cardGrid .card-tile')].map(t => t.textContent.trim().slice(0, 30))")
    check("a new search while 'load more' is still loading: only the new search's cards", len(names) == 1 and "太陽の指輪" in names[0], names)
    check("no page errors", not errs, errs)
    b.close()

print("\n%d/%d search checks passed" % (sum(ok for _, ok in results), len(results)))

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

    # ---- round 19: slang and loosely worded effects (each of these found nothing, or the wrong cards, before)
    ALL = """(qs) => {
      const st = Object.assign({}, state, { colors: new Set(), types: new Set(), creatureTypes: new Set(), keywords: new Set(), manaCosts: new Set(), roles: new Set(), rarity: '', format: '', sort: '', showLoose: false });
      return qs.map(q => { try { const r = searchRows(q, st);
        return { q, n: r.rows.length, en: r.rows.map(x => x.name_en), roles: r.info.roles.map(x => x.id || x.tag || '?'), aliases: (r.info.aliases || []).map(a => a.from + '>' + a.to),
                 asRole: (r.info.asRole || []).map(a => a.id + '>' + a.query), derived: r.info.derived, cmc: r.rows.map(x => x._cmc),
                 types: r.rows.map(x => x._typeEn), ja: r.rows.slice(0, 40).map(x => x.oracle_ja || '') };
      } catch (e) { return { q, err: String(e && e.stack || e).slice(0, 400) }; } });
    }"""
    S = {r["q"]: r for r in page.evaluate(ALL, [
        "場に出たとき", "場に出た時", "戦場に出たとき", "戦場に出た時", "死亡したとき", "死んだとき", "確定除去", "追放除去", "疑似除去", "軽量除去", "cheap removal",
        "PW除去", "3点火力", "3ダメージ", "3点ダメージ", "全体火力", "確定カウンター", "ソフトカウンター", "hard counter", "soft counter", "2ドロー", "デッキから探す", "山札から探す",
        "サクる", "宝物トークン", "宝物・トークン", "アンブロッカブル", "unblockable", "フライヤー", "飛行持ち", "flyer", "ストーム", "タップイン", "tapland", "デュアルランド",
        "2色土地", "引いて捨てる", "自分のクリーチャー", "全てのクリーチャーを破壊", "すべてのクリーチャーを破壊", "エンド時", "山札の上", "トップ", "PW", "ピンガー", "pinger",
        "ティム", "カウンター", "青のカウンター", "2マナのカウンター", "ロード", "部族ロード", "lord", "赤のロード", "トークン倍増", "バニラ", "ETBクリーチャー", "ETB持ち",
        "コスト踏み倒し", "タダで唱える", "墓地から手札", "置物", "ライフロス", "ダブルストライク", "ラス", "sac", "マナコスト"])}
    has = lambda q, *names: all(n in S[q]["en"] for n in names)
    has_h = lambda q, *names: all(n in H[q]["en"] for n in names)
    hasnt = lambda q, *names: not any(n in S[q]["en"] for n in names)
    check("slang: no search throws", not any("err" in r for r in S.values()), [r for r in S.values() if "err" in r])
    check("場に出た時 / 戦場に出た時 (時 for とき) = the same cards as とき",
          S["場に出た時"]["n"] >= S["場に出たとき"]["n"] > 3000 and S["戦場に出た時"]["n"] >= S["戦場に出たとき"]["n"], (S["場に出た時"]["n"], S["場に出たとき"]["n"]))
    check("死んだとき = 死亡したとき", S["死んだとき"]["n"] >= S["死亡したとき"]["n"] > 500 and S["死んだとき"]["n"] < 1.1 * S["死亡したとき"]["n"], (S["死んだとき"]["n"], S["死亡したとき"]["n"]))
    check("確定除去: Murder, Swords, Path, Vindicate, Hero's Downfall; not Doom Blade or Lightning Bolt",
          S["確定除去"]["roles"] == ["sure-removal"] and has("確定除去", "Murder", "Swords to Plowshares", "Path to Exile", "Vindicate", "Hero's Downfall")
          and hasnt("確定除去", "Doom Blade", "Lightning Bolt"), S["確定除去"]["en"][:10])
    check("追放除去: Swords and Path, not Murder", has("追放除去", "Swords to Plowshares", "Path to Exile") and hasnt("追放除去", "Murder"), S["追放除去"]["n"])
    check("疑似除去: Pacifism and Arrest, not Murder", has("疑似除去", "Pacifism", "Arrest") and hasnt("疑似除去", "Murder"), S["疑似除去"]["en"][:10])
    check("軽量除去 = cheap removal (2 mana or less)", S["軽量除去"]["n"] == S["cheap removal"]["n"] > 1000 and max(S["軽量除去"]["cmc"]) <= 2, S["軽量除去"]["n"])
    check("PW除去: Hero's Downfall and Lightning Bolt, not Murder", has("PW除去", "Hero's Downfall", "Lightning Bolt") and hasnt("PW除去", "Murder"), S["PW除去"]["n"])
    check("3点火力 / 3ダメージ = 3点ダメージ, Lightning Bolt included", S["3点火力"]["n"] == S["3ダメージ"]["n"] >= S["3点ダメージ"]["n"] > 300 and has("3ダメージ", "Lightning Bolt")
          and "3ダメージ>3点のダメージ" in S["3ダメージ"]["aliases"], (S["3点火力"]["n"], S["3ダメージ"]["n"], S["3点ダメージ"]["n"], S["3ダメージ"]["aliases"]))
    check("全体火力: Pyroclasm, Anger of the Gods; not Wrath of God", has("全体火力", "Pyroclasm", "Anger of the Gods") and hasnt("全体火力", "Wrath of God"), S["全体火力"]["n"])
    check("確定カウンター: Counterspell, not Mana Leak; ソフトカウンター: Mana Leak, not Counterspell",
          has("確定カウンター", "Counterspell") and hasnt("確定カウンター", "Mana Leak") and has("ソフトカウンター", "Mana Leak") and hasnt("ソフトカウンター", "Counterspell")
          and S["hard counter"]["n"] == S["確定カウンター"]["n"] and S["soft counter"]["n"] == S["ソフトカウンター"]["n"], (S["確定カウンター"]["n"], S["ソフトカウンター"]["n"]))
    check("2ドロー: Divination", has("2ドロー", "Divination"), S["2ドロー"]["n"])
    check("デッキから探す / 山札から探す (= ライブラリーから探し): Demonic Tutor", has("デッキから探す", "Demonic Tutor") and S["山札から探す"]["n"] == S["デッキから探す"]["n"] > 500, S["デッキから探す"]["n"])
    check("サクる = 生け贄に捧げる: Viscera Seer", has("サクる", "Viscera Seer") and S["サクる"]["n"] > 2500, S["サクる"]["n"])
    check("宝物トークン (without ・) = 宝物・トークン: Smothering Tithe", S["宝物トークン"]["n"] == S["宝物・トークン"]["n"] > 200 and has("宝物トークン", "Smothering Tithe"), S["宝物トークン"]["n"])
    check("アンブロッカブル / unblockable: Invisible Stalker", has("アンブロッカブル", "Invisible Stalker") and has("unblockable", "Invisible Stalker"), (S["アンブロッカブル"]["n"], S["unblockable"]["n"]))
    check("フライヤー / 飛行持ち / flyer: flying (Serra Angel), thousands", all(has(q, "Serra Angel") and S[q]["n"] > 4000 for q in ("フライヤー", "飛行持ち", "flyer")),
          [S[q]["n"] for q in ("フライヤー", "飛行持ち", "flyer")])
    check("ストーム: the keyword (Grapeshot, Tendrils of Agony)", has("ストーム", "Grapeshot", "Tendrils of Agony"), S["ストーム"]["n"])
    check("タップイン / tapland: Azorius Guildgate; not shock lands or check lands",
          has("タップイン", "Azorius Guildgate") and hasnt("タップイン", "Hallowed Fountain", "Glacial Fortress", "Plains") and S["tapland"]["n"] == S["タップイン"]["n"], S["タップイン"]["n"])
    check("デュアルランド / 2色土地: Tundra, Hallowed Fountain, Adarkar Wastes; not tri-lands or Plains",
          has("デュアルランド", "Tundra", "Hallowed Fountain", "Adarkar Wastes") and hasnt("デュアルランド", "Arcane Sanctum", "Plains") and S["2色土地"]["n"] == S["デュアルランド"]["n"], S["デュアルランド"]["n"])
    check("引いて捨てる: looting (Faithless Looting)", S["引いて捨てる"]["roles"] == ["loot"] and has("引いて捨てる", "Faithless Looting"), S["引いて捨てる"]["roles"])
    check("自分のクリーチャー = あなたがコントロールするクリーチャー: Glorious Anthem", has("自分のクリーチャー", "Glorious Anthem") and S["自分のクリーチャー"]["n"] > 800, S["自分のクリーチャー"]["n"])
    check("全てのクリーチャーを破壊 = すべての…: Wrath of God", S["全てのクリーチャーを破壊"]["n"] == S["すべてのクリーチャーを破壊"]["n"] > 100 and has("全てのクリーチャーを破壊", "Wrath of God"),
          (S["全てのクリーチャーを破壊"]["n"], S["すべてのクリーチャーを破壊"]["n"]))
    check("エンド時 = 終了ステップの開始時", S["エンド時"]["n"] > 500, S["エンド時"]["n"])
    check("山札の上 / トップ = ライブラリーの一番上: Brainstorm", has("山札の上", "Brainstorm") and has("トップ", "Brainstorm"), (S["山札の上"]["n"], S["トップ"]["n"]))
    check("PW: planeswalkers only", S["PW"]["n"] > 300 and all("planeswalker" in t_.lower() for t_ in S["PW"]["types"]), S["PW"]["n"])
    check("ピンガー / pinger: Prodigal Sorcerer", has("ピンガー", "Prodigal Sorcerer") and S["pinger"]["n"] == S["ピンガー"]["n"], S["ピンガー"]["n"])
    check("ティム (also part of names): searched as text, the pinger role offered", S["ティム"]["roles"] == [] and any(a.startswith("pinger>") for a in S["ティム"]["asRole"]), S["ティム"]["asRole"])
    check("カウンター (counters or counterspells): searched as text, 打ち消し offered", S["カウンター"]["n"] > 4000 and "counterspell>打ち消し" in S["カウンター"]["asRole"], S["カウンター"]["asRole"])
    check("青のカウンター: blue counterspells (Counterspell)", S["青のカウンター"]["roles"] == ["counterspell"] and has("青のカウンター", "Counterspell"), S["青のカウンター"]["roles"])
    check("2マナのカウンター: counterspells of mana value 2", S["2マナのカウンター"]["roles"] == ["counterspell"] and set(S["2マナのカウンター"]["cmc"]) == {2} and has("2マナのカウンター", "Counterspell"),
          S["2マナのカウンター"]["n"])
    check("ロード / lord (also in names): searched as names, the lord role offered", S["ロード"]["roles"] == [] and any(a.startswith("lord>") for a in S["ロード"]["asRole"])
          and S["lord"]["roles"] == [] and any(a.startswith("lord>") for a in S["lord"]["asRole"]), (S["ロード"]["asRole"], S["lord"]["asRole"]))
    check("部族ロード: Lord of Atlantis, Goblin King, Elvish Archdruid; not Glorious Anthem",
          has("部族ロード", "Lord of Atlantis", "Goblin King", "Elvish Archdruid") and hasnt("部族ロード", "Glorious Anthem"), S["部族ロード"]["n"])
    check("赤のロード: red lords (Goblin King)", S["赤のロード"]["roles"] == ["lord"] and has("赤のロード", "Goblin King"), S["赤のロード"]["n"])
    check("トークン倍増: Doubling Season, Parallel Lives", has("トークン倍増", "Doubling Season", "Parallel Lives"), S["トークン倍増"]["n"])
    check("バニラ: Grizzly Bears, not Llanowar Elves", has("バニラ", "Grizzly Bears") and hasnt("バニラ", "Llanowar Elves"), S["バニラ"]["n"])
    check("ETBクリーチャー: ETB, creatures only; ETB持ち = ETB", S["ETBクリーチャー"]["roles"] == ["etb"] and all("creature" in t_.lower() for t_ in S["ETBクリーチャー"]["types"])
          and S["ETB持ち"]["roles"] == ["etb"], (S["ETBクリーチャー"]["roles"], S["ETBクリーチャー"]["n"]))
    check("コスト踏み倒し: the cheat role", S["コスト踏み倒し"]["roles"] == ["cheat"], S["コスト踏み倒し"]["roles"])
    check("タダで唱える = マナ・コストを支払うことなく唱える", S["タダで唱える"]["n"] > 30, S["タダで唱える"]["n"])
    check("マナコスト (without ・) finds マナ・コスト", S["マナコスト"]["n"] > 1000, S["マナコスト"]["n"])
    ordered = lambda tx: (tx.find("墓地") >= 0 and tx.find("手札", tx.find("墓地")) >= 0)
    check("墓地から手札: same ability, from the graveyard to the hand first", S["墓地から手札"]["n"] > 300 and has("墓地から手札", "Raise Dead")
          and all(ordered(tx) for tx in S["墓地から手札"]["ja"][:30]), [tx[:40] for tx in S["墓地から手札"]["ja"][:30] if not ordered(tx)][:3])
    check("置物: noncreature artifacts and enchantments (Sol Ring, not Solemn Simulacrum)", has("置物", "Sol Ring") and hasnt("置物", "Solemn Simulacrum"), S["置物"]["n"])
    check("ライフロス = ライフを失う", S["ライフロス"]["n"] > 800, S["ライフロス"]["n"])
    check("ダブルストライク = 二段攻撃", has("ダブルストライク", "Fencing Ace"), S["ダブルストライク"]["n"])
    A2 = {r["q"]: r for r in page.evaluate(ALL, ["攻撃したとき", "攻撃するたび"])}
    check("攻撃したとき also finds 攻撃するたび (the cards' wording), with a note", A2["攻撃したとき"]["n"] >= A2["攻撃するたび"]["n"] > 1000
          and "攻撃したとき>攻撃するたび" in A2["攻撃したとき"]["aliases"], (A2["攻撃したとき"]["n"], A2["攻撃したとき"]["aliases"]))
    # ---- round 20: hiragana game words; Japanese searches reach cards with no Japanese text
    H = {r["q"]: r for r in page.evaluate(ALL, ["はかい", "破壊", "ついほう", "追放", "ひこう", "とらんぷる", "くりーちゃーをはかい", "クリーチャーを破壊", "じょきょ", "ぜんたいじょきょ",
        "あかのかりょく", "かーどを2まいひく", "らいふをえる", "ぼちからてふだ", "墓地から手札", "らがばん", "ライブラリーから土地"])}
    check("hiragana: はかい = 破壊, ついほう = 追放, ひこう = 飛行, とらんぷる = トランプル",
          H["はかい"]["n"] >= H["破壊"]["n"] * 0.9 and H["ついほう"]["n"] >= H["追放"]["n"] * 0.9 and has_h("ひこう", "Serra Angel") and H["とらんぷる"]["n"] > 1000
          and "はかい>破壊" in H["はかい"]["aliases"], [(q, H[q]["n"]) for q in ("はかい", "破壊", "ついほう", "追放", "ひこう", "とらんぷる")])
    check("hiragana: はかい no longer matches おせっかい (は is not dropped as a particle)", "Ertai's Meddling" not in H["はかい"]["en"], H["はかい"]["en"][:5])
    check("hiragana phrases: くりーちゃーをはかい = クリーチャーを破壊", H["くりーちゃーをはかい"]["n"] == H["クリーチャーを破壊"]["n"] > 1000, (H["くりーちゃーをはかい"]["n"], H["クリーチャーを破壊"]["n"]))
    check("hiragana roles: じょきょ, ぜんたいじょきょ, あかのかりょく", H["じょきょ"]["roles"] == ["removal"] and H["ぜんたいじょきょ"]["roles"] == ["boardwipe"]
          and H["あかのかりょく"]["roles"] == ["burn"] and H["あかのかりょく"]["derived"], (H["じょきょ"]["roles"], H["ぜんたいじょきょ"]["roles"], H["あかのかりょく"]))
    check("hiragana: かーどを2まいひく (Divination), らいふをえる, ぼちからてふだ = 墓地から手札",
          has_h("かーどを2まいひく", "Divination") and H["らいふをえる"]["n"] > 1000 and H["ぼちからてふだ"]["n"] == H["墓地から手札"]["n"], (H["かーどを2まいひく"]["n"], H["らいふをえる"]["n"], H["ぼちからてふだ"]["n"]))
    check("hiragana names still work: らがばん -> ラガバン", H["らがばん"]["n"] == 2, H["らがばん"]["en"])
    check("cards with no Japanese text: 墓地から手札 finds Argivian Find, くりーちゃーをはかい finds Urborg Panther, ライブラリーから土地 finds Untamed Wilds",
          has_h("墓地から手札", "Argivian Find") and has_h("くりーちゃーをはかい", "Urborg Panther") and has_h("ライブラリーから土地", "Untamed Wilds"), H["墓地から手札"]["n"])
    check("ラス: names first, the board wipe role offered", any(a.startswith("boardwipe>") for a in S["ラス"]["asRole"]), S["ラス"]["asRole"])
    check("sac = sacrifice (not Sacred...)", has("sac", "Viscera Seer") and hasnt("sac", "Sacred Foundry"), S["sac"]["n"])

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

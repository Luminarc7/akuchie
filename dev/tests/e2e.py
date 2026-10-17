"""End-to-end test of the 悪知恵 site in headless Chromium with all network
traffic answered from fixtures (Scryfall, Frankfurter, the database file)."""
import gzip, io, json, re, sys, urllib.parse
import os as _os
HERE = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.abspath(_os.path.join(HERE, "..", ".."))
# the pages to test: the repository's own, or another folder (WARUJIE_PAGES=/path/with/index.html)
PAGES = _os.environ.get("WARUJIE_PAGES", REPO)
# the site's contact address, built here so it is never written out in this public file
CONTACT = "@".join(["warujie.mtg", "gmail.com"])
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

SITE = "https://warujie.github.io/Warujie/"
INDEX = open(_os.path.join(PAGES, "index.html"), encoding="utf-8").read()
PREVIEW = open(_os.path.join(PAGES, "preview.html"), encoding="utf-8").read()
COMBO_JA_JS = open(_os.path.join(PAGES, "combo_ja.js"), encoding="utf-8").read()
sys.path.insert(0, HERE)
from search_rows import SEARCH_ROWS
REAL_META = open(_os.path.join(HERE, "fixtures", "real_meta.json"), encoding="utf-8").read()
META_MODE = {"mode": "fixture"}   # fixture | real | absent
DB_MODE = {"present": True, "extra": False, "search": False, "variant": None}
DECKS_MODE = {"mode": "absent"}   # fixture | absent
SHOTS = len(sys.argv) > 1 and sys.argv[1] == "shots"
PRICE_SITE = {"dir": None}
PRICES_BASE = "https://warujie.github.io/warujie-prices/"

def png(w, h, top, bottom, label=""):
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / max(h - 1, 1)
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    if label:
        d.ellipse([w * .36, h * .12, w * .64, h * .5], outline=(235, 225, 200), width=4)   # stand-in "face"
        d.arc([w * .43, h * .30, w * .57, h * .42], 20, 160, fill=(235, 225, 200), width=4)
    b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()

CARD_PNG = png(244, 340, (70, 62, 96), (38, 34, 58))
ART_PNG = png(626, 457, (92, 58, 40), (20, 14, 12), "art")

def card(id, oracle, lang, set_, num, name, **kw):
    c = {"object": "card", "id": id, "oracle_id": oracle, "lang": lang, "set": set_,
         "collector_number": num, "name": name, "set_name": kw.pop("set_name", set_.upper()),
         "rarity": kw.pop("rarity", "mythic"), "released_at": kw.pop("released_at", "2021-06-18"),
         "image_uris": {"small": f"https://cards.scryfall.io/small/{id}.jpg",
                        "normal": f"https://cards.scryfall.io/normal/{id}.jpg",
                        "large": f"https://cards.scryfall.io/large/{id}.jpg",
                        "art_crop": f"https://cards.scryfall.io/art_crop/front/{id[0]}/{id[1]}/{id}.jpg?1700000000"},
         "artist": kw.pop("artist", "Artist of " + name),
         "prints_search_uri": f"https://api.scryfall.com/cards/search?order=released&q=oracleid%3A{oracle}&unique=prints",
         "scryfall_uri": f"https://scryfall.com/card/{set_}/{num}",
         "type_line": kw.pop("type_line", "Legendary Creature — Monkey Pirate"),
         "oracle_text": kw.pop("oracle_text", "Whenever Ragavan deals combat damage to a player, create a Treasure token."),
         "mana_cost": kw.pop("mana_cost", "{R}"), "colors": kw.pop("colors", ["R"]), "cmc": 1.0,
         "legalities": {"modern": "legal", "legacy": "banned", "standard": "not_legal", "vintage": "restricted"},
         "prices": kw.pop("prices", {"usd": None, "usd_foil": None}),
         "finishes": kw.pop("finishes", ["nonfoil", "foil"])}
    c.update(kw)
    c.setdefault("image_status", "highres_scan")
    return c

RAG = "rag-oracle"
CARDS = [
    card("rag-en-mh2", RAG, "en", "mh2", "138", "Ragavan, Nimble Pilferer", set_name="Modern Horizons 2",
         prices={"usd": "40.00", "usd_foil": "60.00", "eur": "35.00"}),
    card("rag-ja-mh2", RAG, "ja", "mh2", "138", "Ragavan, Nimble Pilferer", set_name="Modern Horizons 2",
         printed_name="敏捷なこそ泥、ラガバン", printed_type_line="伝説のクリーチャー — 猿・海賊",
         printed_text="敏捷なこそ泥、ラガバンがプレイヤー１人に戦闘ダメージを与えるたび、宝物・トークン１つを生成する。"),
    card("rag-en-mh2-bl", RAG, "en", "mh2", "345", "Ragavan, Nimble Pilferer", set_name="Modern Horizons 2",
         border_color="borderless", frame_effects=["showcase"], prices={"usd": "55.00"}),
    card("rag-en-mul", RAG, "en", "mul", "21", "Ragavan, Nimble Pilferer", set_name="Multiverse Legends",
         released_at="2023-04-21", prices={"usd": "41.00"}),
    card("rag-ja-mul", RAG, "ja", "mul", "21", "Ragavan, Nimble Pilferer", set_name="Multiverse Legends",
         released_at="2023-04-21", printed_name="敏捷なこそ泥、ラガバン"),
    card("bolt-en-m10", "bolt-oracle", "en", "m10", "146", "Lightning Bolt", set_name="Magic 2010",
         rarity="common", released_at="2009-07-17", type_line="Instant",
         oracle_text="Lightning Bolt deals 3 damage to any target.", prices={"usd": "1.20"}),
    card("bolt-ja-m10", "bolt-oracle", "ja", "m10", "146", "Lightning Bolt", set_name="Magic 2010", image_status="placeholder",
         rarity="common", released_at="2009-07-17", type_line="Instant", printed_name="稲妻",
         printed_type_line="インスタント", printed_text="クリーチャー１体かプレイヤー１人を対象とする。稲妻はそれに３点のダメージを与える。"),
    card("saga-en", "saga-oracle", "en", "mh2", "259", "Urza's Saga", set_name="Modern Horizons 2",
         rarity="rare", type_line="Enchantment Land — Urza's Saga", oracle_text="(As this Saga enters…)",
         mana_cost="", colors=[], prices={"usd": "30.00"}),
    card("saga-ja", "saga-oracle", "ja", "mh2", "259", "Urza's Saga", set_name="Modern Horizons 2",
         rarity="rare", type_line="Enchantment Land — Urza's Saga", printed_name="ウルザの物語",
         printed_type_line="エンチャント・土地 — ウルザの・英雄譚", printed_text="（この英雄譚が出た際と…）", mana_cost="", colors=[]),
    card("drag-en", "drag-oracle", "en", "m10", "156", "Shivan Dragon", set_name="Magic 2010", rarity="rare",
         released_at="2009-07-17", type_line="Creature — Dragon", oracle_text="Flying", mana_cost="{4}{R}{R}",
         power="5", toughness="5", prices={"usd": "0.50"}),
    card("drag-ja", "drag-oracle", "ja", "m10", "156", "Shivan Dragon", set_name="Magic 2010", rarity="rare", image_status="lowres",
         released_at="2009-07-17", type_line="Creature — Dragon", printed_name="シヴ山のドラゴン",
         printed_type_line="クリーチャー — ドラゴン", printed_text="飛行", mana_cost="{4}{R}{R}", power="5", toughness="5"),
    card("elf-en", "elf-oracle", "en", "m10", "189", "Llanowar Elves", set_name="Magic 2010", rarity="common",
         released_at="2009-07-17", type_line="Creature — Elf Druid", oracle_text="{T}: Add {G}.", mana_cost="{G}",
         colors=["G"], power="1", toughness="1", prices={"usd": "0.30"}),
    card("elf-ja", "elf-oracle", "ja", "m10", "189", "Llanowar Elves", set_name="Magic 2010", rarity="common",
         released_at="2009-07-17", type_line="Creature — Elf Druid", printed_name="ラノワールのエルフ",
         printed_type_line="クリーチャー — エルフ・ドルイド", printed_text="{T}：{G}を加える。", mana_cost="{G}", colors=["G"], power="1", toughness="1"),
    card("qp-en", "qp-oracle", "en", "m10", "210", "Qasali Pridemage", set_name="Magic 2010", rarity="uncommon",
         released_at="2009-07-17", type_line="Creature — Cat Wizard", oracle_text="Exalted", mana_cost="{G}{W}",
         colors=["G", "W"], power="2", toughness="2", prices={"usd": "0.80"}),
    card("qp-ja", "qp-oracle", "ja", "m10", "210", "Qasali Pridemage", set_name="Magic 2010", rarity="uncommon",
         released_at="2009-07-17", type_line="Creature — Cat Wizard", printed_name="クァーサルの群れ魔道士",
         printed_type_line="クリーチャー — 猫・ウィザード", printed_text="賛美", mana_cost="{G}{W}", colors=["G", "W"], power="2", toughness="2"),
    card("drs-en", "drs-oracle", "en", "gol", "1", "Deathrite Shaman", set_name="Golgari Test Set", rarity="rare", type_line="Creature — Elf Shaman",
         oracle_text="{T}: Exile target land card from a graveyard. Add one mana of any color.", mana_cost="{B/G}", colors=["B", "G"], power="1", toughness="2", prices={"usd": "9.00"}),
    card("drs-ja", "drs-oracle", "ja", "gol", "1", "Deathrite Shaman", set_name="Golgari Test Set", rarity="rare", type_line="Creature — Elf Shaman",
         printed_name="死儀礼のシャーマン", printed_type_line="クリーチャー — エルフ・シャーマン", printed_text="{T}：墓地にある土地カード１枚を対象とし、それを追放する。", mana_cost="{B/G}", colors=["B", "G"], power="1", toughness="2"),
    card("rat-en", "rat-oracle", "en", "gol", "2", "Pack Rat", set_name="Golgari Test Set", rarity="rare", type_line="Creature — Rat",
         oracle_text="Pack Rat's power and toughness are each equal to the number of Rats you control.", mana_cost="{1}{B}", colors=["B"], power="*", toughness="*", prices={"usd": "2.00"}),
    card("rat-ja", "rat-oracle", "ja", "gol", "2", "Pack Rat", set_name="Golgari Test Set", rarity="rare", type_line="Creature — Rat",
         printed_name="群れネズミ", printed_type_line="クリーチャー — ネズミ", printed_text="群れネズミのパワーとタフネスは、それぞれあなたがコントロールするネズミの総数に等しい。", mana_cost="{1}{B}", colors=["B"], power="*", toughness="*"),
    card("altar-en", "altar-oracle", "en", "gol", "3", "Ashnod's Altar", set_name="Golgari Test Set", rarity="uncommon", type_line="Artifact",
         oracle_text="Sacrifice a creature: Add {C}{C}.", mana_cost="{3}", colors=[], prices={"usd": "4.00"}),
    card("altar-ja", "altar-oracle", "ja", "gol", "3", "Ashnod's Altar", set_name="Golgari Test Set", rarity="uncommon", type_line="Artifact",
         printed_name="アシュノッドの供犠台", printed_type_line="アーティファクト", printed_text="クリーチャー１体を生け贄に捧げる：{C}{C}を加える。", mana_cost="{3}", colors=[]),
    card("eo-1", "eo-oracle", "en", "xyz", "1", "English Only Thing", set_name="English Only Set",
         released_at="2025-01-01", rarity="common", type_line="Creature — Bird", oracle_text="Flying",
         mana_cost="{1}{W}", colors=["W"], power="1", toughness="1", prices={"usd": "0.25"}),
]
CARDS += [
    card("abj-en", "abj-oracle", "en", "wth", "27", "Abjure", set_name="Weatherlight", rarity="common", released_at="1997-06-09",
         type_line="Instant", oracle_text="As an additional cost to cast this spell, sacrifice a blue permanent.\nCounter target spell.", mana_cost="{U}", colors=["U"], prices={"usd": "0.40"}),
    card("abj-ja", "abj-oracle", "ja", "wth", "27", "Abjure", set_name="Weatherlight", rarity="common", released_at="1997-06-09",
         type_line="Instant", printed_name="拒絶", mana_cost="{U}", colors=["U"], image_status="placeholder"),
]
BY_ID = {c["id"]: c for c in CARDS}
# other languages of the same printings, only reachable through the multilingual set+number search
MULTI = [
    card("rag-fr-mh2", RAG, "fr", "mh2", "138", "Ragavan, Nimble Pilferer", set_name="Modern Horizons 2",
         printed_name="Ragavan, chapardeur agile", printed_type_line="Créature légendaire : singe et pirate",
         printed_text="À chaque fois que Ragavan inflige des blessures de combat à un joueur, créez un jeton Trésor."),
    card("rag-de-mh2", RAG, "de", "mh2", "138", "Ragavan, Nimble Pilferer", set_name="Modern Horizons 2",
         printed_name="Ragavan, flinker Dieb"),
    card("rag-fr-mul", RAG, "fr", "mul", "21", "Ragavan, Nimble Pilferer", set_name="Multiverse Legends"),
    # the Japanese 4th Edition is its own set code (4bb); its English twin is 4ed, same number
    card("bolt-it-m10", "bolt-oracle", "it", "m10", "146", "Lightning Bolt", set_name="Magic 2010", rarity="common", released_at="2009-07-17",
         type_line="Instant", printed_name="Fulmine", image_status="placeholder"),
    card("arma-ja-4bb", "arma-oracle", "ja", "4bb", "4", "Armageddon", set_name="Fourth Edition Foreign Black Border", rarity="rare",
         type_line="Sorcery", oracle_text="Destroy all lands.", mana_cost="{3}{W}", colors=["W"],
         printed_name="ハルマゲドン", printed_type_line="ソーサリー", printed_text="すべての土地を破壊する。"),
    card("arma-de-4bb", "arma-oracle", "de", "4bb", "4", "Armageddon", set_name="Fourth Edition Foreign Black Border", rarity="rare",
         type_line="Sorcery", oracle_text="Destroy all lands.", printed_name="Armageddon"),
    card("arma-en-4ed", "arma-oracle", "en", "4ed", "4", "Armageddon", set_name="Fourth Edition", rarity="rare",
         type_line="Sorcery", oracle_text="Destroy all lands.", mana_cost="{3}{W}", colors=["W"]),
    card("arma-en-a25", "arma-oracle", "en", "a25", "4", "Armageddon", set_name="Masters 25", rarity="rare",
         type_line="Sorcery", oracle_text="Destroy all lands.", mana_cost="{3}{W}", colors=["W"]),
    card("cove-ja-woe", "cove-oracle", "ja", "woe", "237", "Spellscorn Coven // Take It Back", set_name="Wilds of Eldraine", rarity="uncommon",
         type_line="Creature — Faerie Warlock // Instant — Adventure", oracle_text="", mana_cost="{3}{B} // {2}{U}", colors=["B"],
         card_faces=[{"name": "Spellscorn Coven", "printed_name": "Spellscorn Coven", "type_line": "Creature — Faerie Warlock",
                      "printed_type_line": "クリーチャー — フェアリー・邪術師", "oracle_text": "Flying", "printed_text": "飛行", "mana_cost": "{3}{B}"},
                     {"name": "Take It Back", "printed_name": "お返（かえ）し", "type_line": "Instant — Adventure",
                      "printed_type_line": "インスタント — 出来事", "oracle_text": "Return target spell to its owner's hand.", "printed_text": "呪文１つを対象とする。", "mana_cost": "{2}{U}"}]),
]
for c in MULTI: BY_ID[c["id"]] = c
# found only by name (decks): basic lands
NAME_ONLY = [card("forest-en", "forest-oracle", "en", "m10", "246", "Forest", rarity="common", type_line="Basic Land — Forest", oracle_text="({T}: Add {G}.)", mana_cost="", colors=[], cmc=0.0),
             card("mountain-en", "mountain-oracle", "en", "m10", "242", "Mountain", rarity="common", type_line="Basic Land — Mountain", oracle_text="({T}: Add {R}.)", mana_cost="", colors=[], cmc=0.0)]

# ---- price data, made with build_prices.py (v3) itself over 45 (and 1) simulated days
import os, shutil, subprocess, tempfile
import price_fixtures as PF
# product ids, so the builder can attach the cheapest listings
BY_ID["rag-en-mh2"].update(tcgplayer_id=1001, cardmarket_id=2001)
BY_ID["saga-en"].update(tcgplayer_id=1002)
PRICE_TMP = tempfile.mkdtemp(prefix="prices_")
PRICES_FULL = PF.build_prices(CARDS, 45, "full", PRICE_TMP)
PRICES_ONE = PF.build_prices(CARDS, 1, "one", PRICE_TMP)
import combo_fixture
combo_fixture.build(os.path.join(PRICES_FULL, "c"))
# the same data as published before the euro prices: no "eur" lists in movers.json
# the same data with the role tags (t/tags.json.gz)
PRICES_ROLES = os.path.join(PRICE_TMP, "roles")
shutil.copytree(PRICES_FULL, PRICES_ROLES)
PRICES_NOEU = os.path.join(PRICE_TMP, "noeu")
shutil.copytree(PRICES_FULL, PRICES_NOEU)
_mv = json.load(open(os.path.join(PRICES_NOEU, "movers.json")))
for _w in _mv["windows"].values():
    _w.pop("eur", None)
json.dump(_mv, open(os.path.join(PRICES_NOEU, "movers.json"), "w"))
SETS = [
    {"object": "set", "code": "xyz", "name": "English Only Set", "set_type": "expansion", "released_at": "2025-01-01", "card_count": 1, "digital": False, "icon_svg_uri": "https://svgs.scryfall.io/sets/xyz.svg"},
    {"object": "set", "code": "mul", "name": "Multiverse Legends", "set_type": "masterpiece", "released_at": "2023-04-21", "card_count": 2, "digital": False, "icon_svg_uri": "https://svgs.scryfall.io/sets/mul.svg"},
    {"object": "set", "code": "mh2", "name": "Modern Horizons 2", "set_type": "draft_innovation", "released_at": "2021-06-18", "card_count": 303, "digital": False, "icon_svg_uri": "https://svgs.scryfall.io/sets/mh2.svg"},
    {"object": "set", "code": "m10", "name": "Magic 2010", "set_type": "core", "released_at": "2009-07-17", "card_count": 249, "digital": False, "icon_svg_uri": "https://svgs.scryfall.io/sets/m10.svg"},
    {"object": "set", "code": "ya1", "name": "Arena Only", "set_type": "alchemy", "released_at": "2024-01-01", "card_count": 5, "digital": True, "icon_svg_uri": ""},
]
SYMBOLS = [{"symbol": "{T}", "svg_uri": "https://svgs.scryfall.io/card-symbols/T.svg", "english": "tap this permanent"},
           {"symbol": "{G}", "svg_uri": "https://svgs.scryfall.io/card-symbols/G.svg", "english": "one green mana"},
           {"symbol": "{B}", "svg_uri": "https://svgs.scryfall.io/card-symbols/B.svg", "english": "one black mana"},
           {"symbol": "{B/G}", "svg_uri": "https://svgs.scryfall.io/card-symbols/BG.svg", "english": "one black or green mana"},
           {"symbol": "{R/G}", "svg_uri": "https://svgs.scryfall.io/card-symbols/RG.svg", "english": "one red or green mana"}] + \
          [{"symbol": "{%s/P}" % c, "svg_uri": "https://svgs.scryfall.io/card-symbols/%sP.svg" % c, "english": "one mana or two life"} for c in "WUBRG"]
YAWG = {"object": "card", "name": "Yawgmoth, Thran Physician", "artist": "Mark Winters", "set": "mh1",
        "image_uris": {"art_crop": "https://cards.scryfall.io/art_crop/front/yawgmoth.jpg"}}

FIELDS = ["id","oracle_id","name_en","name_ja","type_en","type_ja","oracle_en","oracle_ja","mana_cost","colors","cmc",
          "power","toughness","rarity","set","keywords","released_at","alt_names_ja"]
DB = {"version": 2, "generated": "2026-10-05", "fields": FIELDS, "cards": [
    ["rag-ja-mh2", RAG, "Ragavan, Nimble Pilferer", "敏捷なこそ泥、ラガバン", "Legendary Creature — Monkey Pirate", "伝説のクリーチャー — 猿・海賊",
     "Whenever Ragavan deals combat damage to a player, create a Treasure token.", "敏捷なこそ泥、ラガバンがプレイヤー１人に戦闘ダメージを与えるたび、宝物・トークン１つを生成する。",
     "{R}", "R", 1, "2", "1", "mythic", "mh2", "Dash", "2021-06-18", ""],
    ["bolt-ja-m10", "bolt-oracle", "Lightning Bolt", "稲妻", "Instant", "インスタント", "Lightning Bolt deals 3 damage to any target.",
     "クリーチャー１体かプレイヤー１人を対象とする。稲妻はそれに３点のダメージを与える。", "{R}", "R", 1, None, None, "common", "m10", "", "1993-08-05", ""],
    ["saga-ja", "saga-oracle", "Urza's Saga", "ウルザの物語", "Enchantment Land — Urza's Saga", "エンチャント・土地 — ウルザの・英雄譚",
     "(As this Saga enters…)", "（この英雄譚が出た際と…）", "", "", 0, None, None, "rare", "mh2", "", "2021-06-18", ""],
    ["drag-ja", "drag-oracle", "Shivan Dragon", "シヴ山のドラゴン", "Creature — Dragon", "クリーチャー — ドラゴン", "Flying", "飛行",
     "{4}{R}{R}", "R", 6, "5", "5", "rare", "m10", "Flying", "1993-08-05", ""],
    ["eo-1", "eo-oracle", "English Only Thing", "", "Creature — Bird", "", "Flying", "", "{1}{W}", "W", 2, "1", "1", "common", "xyz", "Flying", "2025-01-01", ""],
    ["elf-ja", "elf-oracle", "Llanowar Elves", "ラノワールのエルフ", "Creature — Elf Druid", "クリーチャー — エルフ・ドルイド", "{T}: Add {G}.", "{T}：{G}を加える。",
     "{G}", "G", 1, "1", "1", "common", "m10", "", "1993-08-05", ""],
    ["qp-ja", "qp-oracle", "Qasali Pridemage", "クァーサルの群れ魔道士", "Creature — Cat Wizard", "クリーチャー — 猫・ウィザード", "Exalted", "賛美",
     "{G}{W}", "GW", 2, "2", "2", "uncommon", "m10", "Exalted", "2009-04-30", ""],
]}
DB_GZ = gzip.compress(json.dumps(DB, ensure_ascii=False).encode("utf-8"))
DB_EXTRA = dict(DB, cards=DB["cards"] + [
    ["drs-ja", "drs-oracle", "Deathrite Shaman", "死儀礼のシャーマン", "Creature — Elf Shaman", "クリーチャー — エルフ・シャーマン", "{T}: Exile target land card from a graveyard.", "{T}：墓地にある土地カード１枚を対象とし、それを追放する。",
     "{B/G}", "BG", 1, "1", "2", "rare", "gol", "", "2012-10-05", ""],
    ["rat-ja", "rat-oracle", "Pack Rat", "群れネズミ", "Creature — Rat", "クリーチャー — ネズミ", "Pack Rat's power and toughness are each equal to the number of Rats you control.", "群れネズミのパワーとタフネスは…",
     "{1}{B}", "B", 2, "*", "*", "rare", "gol", "", "2012-10-05", ""],
    ["altar-ja", "altar-oracle", "Ashnod's Altar", "アシュノッドの供犠台", "Artifact", "アーティファクト", "Sacrifice a creature: Add {C}{C}.", "クリーチャー１体を生け贄に捧げる：{C}{C}を加える。",
     "{3}", "", 3, None, None, "uncommon", "gol", "", "1994-03-04", ""],
])
DB_EXTRA_GZ = gzip.compress(json.dumps(DB_EXTRA, ensure_ascii=False).encode("utf-8"))
LEGAL = {"rag-ja-mh2": "mv", "bolt-ja-m10": "mlvac", "saga-ja": "mlv", "drag-ja": "lvc", "eo-1": "", "elf-ja": "lvac", "qp-ja": "lvc"}
DB_LEGAL_GZ = gzip.compress(json.dumps(dict(DB, fields=FIELDS + ["legal"], cards=[r + [LEGAL[r[0]]] for r in DB["cards"]]), ensure_ascii=False).encode("utf-8"))
# every rarity each card was printed at: Shivan Dragon (shown rare) also as a mythic, Llanowar Elves also rare
RARITIES = {"rag-ja-mh2": "m", "bolt-ja-m10": "cu", "saga-ja": "r", "drag-ja": "rm", "eo-1": "c", "elf-ja": "cr", "qp-ja": "u"}
DB_RAR_GZ = gzip.compress(json.dumps(dict(DB, fields=FIELDS + ["rarities"], cards=[r + [RARITIES[r[0]]] for r in DB["cards"]]), ensure_ascii=False).encode("utf-8"))
# every set each card was printed in, and its treatments (upper case: a Japanese printing has it)
PRINTS = {"rag-ja-mh2": ("mh2 mul", "bs"), "bolt-ja-m10": ("lea 4bb m10", "oO"), "saga-ja": ("mh2", "x"), "drag-ja": ("lea m10", "obB"),
          "eo-1": ("xyz", "b"), "elf-ja": ("lea m10", "o"), "qp-ja": ("m10", "")}
DB_PRINTS_GZ = gzip.compress(json.dumps(dict(DB, fields=FIELDS + ["sets", "treatments"], cards=[r + list(PRINTS[r[0]]) for r in DB["cards"]]), ensure_ascii=False).encode("utf-8"))
# the printings file (printings.json.gz): languages of each set and number
PRINTINGS_MODE = {"file": False}
PRINTINGS_FILE = {"version": 1, "generated": "2026-10-16", "fields": ["langs", "rarity", "treatments"], "sets": {
    "mh2": {"138": ["en ja fr de", "m", ""], "345": ["en", "m", "bs"]},
    "m10": {"146": ["en ja it", "c", ""]},
    "4bb": {"4": ["ja de en@4ed", "r", ""]}, "4ed": {"4": ["en ja@4bb de@4bb", "r", ""]}}}
DB_ABJ_GZ = gzip.compress(json.dumps(dict(DB, cards=DB["cards"] + [
    ["abj-ja", "abj-oracle", "Abjure", "拒絶", "Instant", "", "As an additional cost to cast this spell, sacrifice a blue permanent.\nCounter target spell.", "",
     "{U}", "U", 1, None, None, "common", "wth", "", "1997-06-09", ""]]), ensure_ascii=False).encode("utf-8"))
DB_MANY_GZ = gzip.compress(json.dumps(dict(DB, cards=DB["cards"] + [
    [f"bear-{i}", f"bear-o-{i}", f"Test Bear {i}", f"テストの熊{i}", "Creature — Bear", "クリーチャー — 熊", "This is a test bear.", "これはテスト用の熊だ。",
     "{1}{G}", "G", 2, "2", "2", "common", "tst", "", "2020-01-01", ""] for i in range(70)]), ensure_ascii=False).encode("utf-8"))
SEARCH_KANA = {"高価な祭壇": "こうかなさいだん", "滅殺の獣": "めっさつのけもの", "散らばった思考": "ちらばったしこう", "対の供物": "ついのくもつ", "マナのエルフ": "まなのえるふ",
    "木立のエルフ": "こだちのえるふ", "空の癒し手": "そらのいやして", "粉砕テスト": "ふんさいてすと", "破壊のゴーレム": "はかいのごおれむ", "入念な研究テスト": "にゅうねんなけんきゅうてすと",
    "物色テスト": "ぶっしょくてすと", "永続の盾": "えいぞくのたて", "タッパーテスト": "たっぱあてすと", "投げ飛ばしテスト": "なげとばしてすと", "先制の兵": "せんせいのへい",
    "敏捷なこそ泥、ラガバン": "びんしょうなこそどろらがばん", "稲妻": "いなずま", "ウルザの物語": "うるざのものがたり", "シヴ山のドラゴン": "しゔざんのどらごん",
    "ラノワールのエルフ": "らのわあるのえるふ", "クァーサルの群れ魔道士": "くぁあさるのむれまどうし"}
DB_SEARCH_GZ = gzip.compress(json.dumps(dict(DB, fields=FIELDS + ["name_kana"], cards=[r + [SEARCH_KANA.get(r[3], "")] for r in DB["cards"] + SEARCH_ROWS]), ensure_ascii=False).encode("utf-8"))
# round 11: cards for the role search and similar cards
def RR(i, en, ja, ten, tja, oen, oja, mana, colors, cmc, pw=None, tg=None, rarity="common", kw=""):
    return [i + "-ja", i + "-oracle", en, ja, ten, tja, oen, oja, mana, colors, cmc, pw, tg, rarity, "rol", kw, "2020-01-01", ""]
ROLE_ROWS = [
    RR("shock", "Shock", "ショック", "Instant", "インスタント", "Shock deals 2 damage to any target.", "１つを対象とする。ショックはそれに２点のダメージを与える。", "{R}", "R", 1),
    RR("ubolt", "Blue Bolt Test", "青い稲妻テスト", "Instant", "インスタント", "Blue Bolt Test deals 3 damage to any target.", "１つを対象とする。青い稲妻テストはそれに３点のダメージを与える。", "{U}", "U", 1),
    RR("bigbolt", "Big Bolt Test", "大きな稲妻テスト", "Instant", "インスタント", "Big Bolt Test deals 4 damage to any target.", "１つを対象とする。大きな稲妻テストはそれに４点のダメージを与える。", "{1}{R}", "R", 2),
    RR("swords", "Swords Test", "剣テスト", "Instant", "インスタント", "Exile target creature. Its controller gains life equal to its power.",
       "クリーチャー１体を対象とし、それを追放する。それのコントローラーは、それのパワーに等しい点数のライフを得る。", "{W}", "W", 1, rarity="uncommon"),
    RR("path", "Path Test", "道テスト", "Instant", "インスタント", "Exile target attacking creature. Its controller may search their library for a basic land card, put that card onto the battlefield tapped, then shuffle.",
       "攻撃クリーチャー１体を対象とし、それを追放する。それのコントローラーは自分のライブラリーから基本土地・カード１枚を探し、タップ状態で戦場に出し、その後ライブラリーを切り直してもよい。", "{W}", "W", 1, rarity="uncommon"),
    RR("stone", "Ramp Stone", "加速の石", "Artifact", "アーティファクト", "{T}: Add {C}{C}.", "{T}：{C}{C}を加える。", "{3}", "", 3),
    RR("tramp", "Trampling Beast", "トランプルの獣", "Creature — Beast", "クリーチャー — ビースト", "Trample", "トランプル", "{3}{G}", "G", 4, "4", "4", kw="Trample"),
    RR("seer", "Seer Test", "予見者テスト", "Creature — Vampire Wizard", "クリーチャー — 吸血鬼・ウィザード", "Sacrifice a creature: Scry 1.", "クリーチャー１体を生け贄に捧げる：占術１を行う。", "{B}", "B", 1, "1", "1"),
    RR("dispute", "Dispute Test", "論争テスト", "Instant", "インスタント", "As an additional cost to cast this spell, sacrifice an artifact or creature.\nDraw two cards and create a Treasure token.",
       "この呪文を唱えるための追加コストとして、アーティファクト１つかクリーチャー１体を生け贄に捧げる。\nカードを２枚引き、宝物・トークン１つを生成する。", "{1}{B}", "B", 2),
    RR("study", "Study Test", "研究テスト", "Enchantment", "エンチャント", "Whenever an opponent casts a spell, you may draw a card unless that player pays {1}.",
       "対戦相手１人が呪文を唱えるたび、そのプレイヤーが{1}を支払わないかぎり、あなたはカードを１枚引いてもよい。", "{2}{U}", "U", 3, rarity="rare"),
    RR("clone", "Clone", "クローン", "Creature — Shapeshifter", "クリーチャー — 多相の戦士", "You may have Clone enter as a copy of any creature on the battlefield.",
       "あなたはクローンを、戦場にあるクリーチャー１体のコピーとして戦場に出してもよい。", "{3}{U}", "U", 4, "0", "0", rarity="rare"),
    RR("drone", "Drone Test", "ドローンテスト", "Creature — Eldrazi Drone", "クリーチャー — エルドラージ・ドローン", "Devoid", "欠色", "{2}{C}", "", 3, "2", "2"),
    RR("fur", "Windswept Fortress Test", "吹（ふ）きさらしの要（よう）塞（さい）テスト", "Land", "土地", "{T}: Add {C}.", "{T}：{C}を加える。", "", "", 0),
    RR("mull", "Mulldrifter Test", "熟考漂いテスト", "Creature — Elemental", "クリーチャー — エレメンタル", "Flying\nWhen Mulldrifter Test enters, draw two cards.",
       "飛行\n熟考漂いテストが戦場に出たとき、カードを２枚引く。", "{4}{U}", "U", 5, "2", "2", kw="Flying"),
    RR("accel", "Accelerate", "加速", "Instant", "インスタント", "Target creature gains haste until end of turn.", "クリーチャー１体を対象とする。それはターン終了時まで速攻を得る。", "{R}", "R", 1),
    RR("crr", "Common Red Removal Test", "赤の除去テスト", "Sorcery", "ソーサリー", "Destroy target artifact.", "アーティファクト１つを対象とし、それを破壊する。", "{2}{R}", "R", 3),
]
for r in ROLE_ROWS:
    c = card(r[0], r[1], "ja", "rol", r[0].split("-")[0], r[2], set_name="Role Test Set", rarity=r[13], type_line=r[4], oracle_text=r[6],
             printed_name=r[3], printed_type_line=r[5], printed_text=r[7], mana_cost=r[8], colors=list(r[9]), released_at="2020-01-01")
    c["cmc"] = float(r[10])
    if r[11] is not None: c.update(power=r[11], toughness=r[12])
    CARDS.append(c); BY_ID[c["id"]] = c
# readings of the Japanese names (name_kana, as tools/name_readings.py writes them): the あいうえお order
KANA = {"敏捷なこそ泥、ラガバン": "びんしょうなこそどろらがばん", "稲妻": "いなずま", "ウルザの物語": "うるざのものがたり", "シヴ山のドラゴン": "しゔざんのどらごん",
        "ラノワールのエルフ": "らのわあるのえるふ", "クァーサルの群れ魔道士": "くぁあさるのむれまどうし", "ショック": "しょっく", "青い稲妻テスト": "あおいいなずまてすと",
        "大きな稲妻テスト": "おおきないなずまてすと", "剣テスト": "けんてすと", "道テスト": "みちてすと", "加速の石": "かそくのいし", "トランプルの獣": "とらんぷるのけもの",
        "予見者テスト": "よけんしゃてすと", "論争テスト": "ろんそうてすと", "研究テスト": "けんきゅうてすと", "クローン": "くろおん", "ドローンテスト": "どろおんてすと",
        "吹（ふ）きさらしの要（よう）塞（さい）テスト": "ふきさらしのようさいてすと", "熟考漂いテスト": "じゅっこうただよいてすと", "加速": "かそく", "赤の除去テスト": "あかのじょきょてすと"}
DB_ROLES_GZ = gzip.compress(json.dumps(dict(DB, fields=FIELDS + ["name_kana"], cards=[r + [KANA.get(r[3], "")] for r in DB["cards"] + ROLE_ROWS]), ensure_ascii=False).encode("utf-8"))
TAG_LIST = ["removal", "creature-removal", "burn", "lifegain", "ramp", "mana-rock", "sacrifice-outlet", "draw", "clone", "mana-dork", "tutor-land", "cantrip"]
def TG(oracle, rank, *tags): return [oracle[:12], rank] + sorted(TAG_LIST.index(t) for t in tags)
TAGS_FIXTURE = {"version": 1, "generated": "2026-10-12", "source": "test", "tags": TAG_LIST, "cards": sorted([
    TG("bolt-oracle", 10, "removal", "creature-removal", "burn"), TG("shock-oracle", 50, "removal", "creature-removal", "burn"),
    TG("ubolt-oracle", 300, "removal", "creature-removal", "burn"), TG("bigbolt-oracle", 200, "removal", "creature-removal", "burn"),
    TG("swords-oracle", 5, "removal", "creature-removal", "lifegain"), TG("path-oracle", 7, "removal", "creature-removal", "ramp", "tutor-land"),
    TG("stone-oracle", 20, "ramp", "mana-rock"), TG("elf-oracle", 30, "ramp", "mana-dork"), TG("seer-oracle", 40, "sacrifice-outlet"),
    TG("dispute-oracle", 15, "sacrifice-outlet", "draw"), TG("study-oracle", 3, "draw"), TG("mull-oracle", 25, "draw"), TG("clone-oracle", 60, "clone"),
])}

def arch(name, colors, decks, share, wins, losses, cards, **kw):
    played = wins + losses
    d = {"name": name, "colors": colors, "decks": decks, "share": share, "wins": wins, "losses": losses, "draws": 0,
         "winrate": round(100 * wins / played, 1) if played else None,
         "ci": [round(100 * wins / played - 5, 1), round(100 * wins / played + 5, 1)] if played else None, "cards": cards}
    d.update(kw)
    return d
META_FIXTURE = {"version": 1, "generated": "2026-10-06T03:00:00Z", "data_through": "2026-10-04",
    "sources": [{"name": "MTGODecklistCache", "url": "https://github.com/Jiliac/MTGODecklistCache"},
                {"name": "MTGOFormatData", "url": "https://github.com/Badaro/MTGOFormatData"}],
    "windows": {
      "30": {"from": "2026-09-07", "to": "2026-10-06", "formats": {
        "standard": {"events": 12, "decks": 400, "matches": 1234, "archetypes": [
            arch("Gruul Dragons", "RG", 100, 25.0, 220, 180, ["Shivan Dragon", "Lightning Bolt", "Urza's Saga", "Llanowar Elves", "Unknown New Card"],
                 sample={"url": "https://melee.gg/Decklist/View/abc", "event": "Big Open", "date": "2026-10-03", "result": "1st Place"}),
            arch("Selesnya Cats", "WG", 50, 12.5, 120, 80, ["Qasali Pridemage", "Llanowar Elves"]),
            arch("Mono Red Burn", "R", 30, 7.5, 10, 12, ["Lightning Bolt"]),
            arch("Orzhov", "WB", 20, 5.0, 40, 60, [], unclassified=True),
          ], "rest": {"archetypes": 7, "decks": 200, "share": 50.0}},
        "modern": {"events": 3, "decks": 40, "matches": 10, "archetypes": [arch("Ragavan Tempo", "UR", 40, 100.0, 5, 5, ["Ragavan, Nimble Pilferer"])]},
        "pioneer": {"events": 0, "decks": 0, "matches": 0, "archetypes": []},
        "legacy": {"events": 9, "decks": 200, "matches": 900, "archetypes": [
            arch("Izzet Delver", "UR", 60, 30.0, 150, 120, ["Lightning Bolt"]),
            arch("Golgari Midrange", "BG", 40, 20.0, 110, 90, ["Deathrite Shaman", "Llanowar Elves", "Ashnod's Altar"], icon="Ashnod's Altar"),
            arch("Sultai Control", "UBG", 30, 15.0, 60, 60, []),
            arch("Mono Black Rats", "B", 20, 10.0, 30, 50, ["Pack Rat"]),
            arch("Eldrazi", "", 16, 8.0, 40, 40, []),
            arch("Mono Green", "G", 10, 5.0, 4, 6, ["Llanowar Elves"], unclassified=True),
          ], "rest": {"archetypes": 5, "decks": 24, "share": 12.0}},
        "vintage": {"events": 2, "decks": 30, "matches": 50, "archetypes": [arch("Jeskai Shops", "WUR", 30, 100.0, 25, 25, [])]},
      }},
      "90": {"from": "2026-07-09", "to": "2026-10-06", "formats": {
        "standard": {"events": 30, "decks": 1000, "matches": 4000, "archetypes": [
            arch("Selesnya Cats", "WG", 300, 30.0, 500, 500, ["Qasali Pridemage"]),
            arch("Gruul Dragons", "RG", 200, 20.0, 450, 400, ["Shivan Dragon"])]},
      }},
    }}

WEEKS = ["2026-07-15", "2026-07-22", "2026-07-29", "2026-08-05", "2026-08-12", "2026-08-19", "2026-08-26", "2026-09-02", "2026-09-09", "2026-09-16", "2026-09-23", "2026-09-30"]
META_FIXTURE["trends"] = {"standard": {"weeks": WEEKS, "decks": [100, 120, 90, 0, 110, 100, 130, 120, 100, 140, 160, 150], "share": {
    "Gruul Dragons": [20, 21, 22, None, 22, 23, 23, 24, 25, 26, 27, 28],
    "Selesnya Cats": [8, 8, 9, None, 9, 10, 10, 11, 14, 16, 18, 20],
    "Mono Red Burn": [12, 11, 11, None, 10, 9, 9, 8, 7, 7, 6, 6],
    "Orzhov|u": [5, 5, 5, None, 5, 5, 5, 5, 5, 5, 5, 5]}}}
LISTS_FIXTURE = {"30-standard": {"version": 1, "decks": {"Gruul Dragons": [
    {"list": {"url": "https://melee.gg/Decklist/View/abc", "event": "Big Open", "date": "2026-10-03", "result": "1st Place"},
     "main": [[4, "Shivan Dragon", 100], [4, "Llanowar Elves", 95], [4, "Ragavan, Nimble Pilferer", 40], [4, "Lightning Bolt", 88],
              [4, "Urza's Saga", 60], [20, "Mountain", 100], [18, "Forest", 100], [2, "Unknown New Card", 12]],
     "side": [[3, "Qasali Pridemage", 50], [2, "Deathrite Shaman", 10]]},
    {"list": {"url": "https://melee.gg/Decklist/View/def", "event": "Second Open", "date": "2026-09-27", "result": "2nd Place"},
     "main": [[4, "Shivan Dragon", 100], [4, "Lightning Bolt", 88], [4, "English Only Thing", 35], [24, "Mountain", 100], [24, "Forest", 100]],
     "side": [[4, "Qasali Pridemage", 50]]},
]}}}
META_DECKS_FIXTURE = {"version": 1, "generated": "2026-10-06T03:00:00Z", "data_through": "2026-10-04", "windows": {"30": {"standard": {
    "Gruul Dragons": {"list": {"url": "https://melee.gg/Decklist/View/abc", "event": "Big Open", "date": "2026-10-03", "result": "1st Place"},
        "main": [[4, "Shivan Dragon", 100], [4, "Llanowar Elves", 95], [4, "Ragavan, Nimble Pilferer", 40], [4, "Lightning Bolt", 88],
                 [4, "Urza's Saga", 60], [20, "Mountain", 100], [18, "Forest", 100], [2, "Unknown New Card", 12]],
        "side": [[3, "Qasali Pridemage", 50], [2, "Deathrite Shaman", 10]],
        "more": [["English Only Thing", 35, 2.5]]},
    "Orzhov|u": {"list": {"url": "", "event": "Small Cup", "date": "2026-09-20", "result": "5-2"},
        "main": [[4, "English Only Thing", 75], [56, "Plains", 100]], "side": [], "more": []},
}}}}

def search_results(q):
    q = urllib.parse.unquote_plus(q)
    if q.startswith("lang:ja ("):   # the Japanese printings of many printings at once (loadPrintCards)
        pairs = set(re.findall(r'e:(\w+) cn:"([^"]+)"', q))
        return [c for c in CARDS if c["lang"] == "ja" and (c["set"], c["collector_number"]) in pairs]
    m = re.search(r'cn:"([^"]+)"', q)
    if m and "e:" in q:   # one printing in every language (include_multilingual), maybe over two set codes
        sets_ = re.findall(r'e:(\w+)', q)
        return [c for c in CARDS + MULTI if c["set"] in sets_ and c["collector_number"] == m.group(1)]
    m = re.search(r"oracleid:(\S+)", q)
    if m:
        prints = [c for c in CARDS if c["oracle_id"] == m.group(1)]
        return [c for c in prints if c["lang"] == ("ja" if "lang:ja" in q else "en")]
    m = re.search(r"e:(\S+)", q)
    if m:
        lang = "ja" if "lang:ja" in q else "en"
        return [c for c in CARDS if c["set"] == m.group(1) and c["lang"] == lang]
    return []

calls = []
def handle(route):
    req = route.request
    url = req.url
    calls.append(url)
    u = urllib.parse.urlparse(url)
    J = lambda obj, status=200: route.fulfill(status=status, content_type="application/json", body=json.dumps(obj))
    if url.startswith(PRICES_BASE):
        rel = u.path[len("/warujie-prices/"):]
        f = os.path.join(PRICE_SITE["dir"], rel) if PRICE_SITE["dir"] else None
        if f and os.path.isfile(f):
            return route.fulfill(status=200, content_type="application/gzip" if rel.endswith(".gz") else "application/json", body=open(f, "rb").read())
        return route.fulfill(status=404, body="not found")
    if url.startswith(SITE):
        path = u.path[len("/Warujie/"):]
        if path in ("", "index.html"):
            return route.fulfill(status=200, content_type="text/html; charset=utf-8", body=INDEX)
        if path == "preview.html":
            return route.fulfill(status=200, content_type="text/html; charset=utf-8", body=PREVIEW)
        if path == "combo_ja.js":
            return route.fulfill(status=200, content_type="text/javascript; charset=utf-8", body=COMBO_JA_JS)
        if path == "meta_decks.json":
            if DECKS_MODE["mode"] == "absent":
                return route.fulfill(status=404, body="not found")
            return route.fulfill(status=200, content_type="application/json", body=json.dumps(META_DECKS_FIXTURE))
        if path.startswith("meta_lists/"):
            key = path[len("meta_lists/"):].replace(".json", "")
            if key in LISTS_FIXTURE and DECKS_MODE["mode"] != "absent":
                return route.fulfill(status=200, content_type="application/json", body=json.dumps(LISTS_FIXTURE[key]))
            return route.fulfill(status=404, body="not found")
        if path == "meta.json":
            if META_MODE["mode"] == "absent":
                return route.fulfill(status=404, body="not found")
            return route.fulfill(status=200, content_type="application/json",
                                 body=REAL_META if META_MODE["mode"] == "real" else json.dumps(META_FIXTURE))
        if path == "ja_cards.json.gz" and DB_MODE["present"]:
            return route.fulfill(status=200, content_type="application/gzip",
                                 body={"legal": DB_LEGAL_GZ, "rar": DB_RAR_GZ, "many": DB_MANY_GZ, "abj": DB_ABJ_GZ, "roles": DB_ROLES_GZ, "prints": DB_PRINTS_GZ}.get(DB_MODE["variant"]) or (DB_SEARCH_GZ if DB_MODE["search"] else DB_EXTRA_GZ if DB_MODE["extra"] else DB_GZ))
        if path == "printings.json.gz" and PRINTINGS_MODE["file"]:
            return route.fulfill(status=200, content_type="application/gzip", body=gzip.compress(json.dumps(PRINTINGS_FILE).encode("utf-8")))
        return route.fulfill(status=404, body="not found")
    if u.netloc == "api.frankfurter.dev":
        eur = "EUR" in url
        return J({"date": "2026-10-03", "base": "EUR" if eur else "USD", "quote": "JPY", "rate": 160.0 if eur else 150.0})
    if u.netloc == "api.scryfall.com":
        if u.path == "/cards/collection":
            out = []
            for ident in json.loads(req.post_data)["identifiers"]:
                if "id" in ident and ident["id"] in BY_ID:
                    out.append(BY_ID[ident["id"]])
                elif "oracle_id" in ident:   # Scryfall answers with the English printing
                    out += [c for c in CARDS if c["oracle_id"] == ident["oracle_id"] and c["lang"] == "en"][:1]
                elif "name" in ident:
                    out += [c for c in CARDS + NAME_ONLY if c["lang"] == "en" and c["name"] == ident["name"]][:1]
                elif "set" in ident:
                    out += [c for c in CARDS if c["set"] == ident["set"] and c["collector_number"] == ident["collector_number"] and c["lang"] == "en"][:1]
            return J({"object": "list", "data": out})
        if u.path == "/cards/search":
            res = search_results(urllib.parse.parse_qs(u.query).get("q", [""])[0])
            if not res:
                return J({"object": "error", "status": 404}, 404)
            return J({"object": "list", "total_cards": len(res), "has_more": False, "data": res})
        if u.path == "/sets":
            return J({"object": "list", "data": SETS})
        if u.path == "/symbology":
            return J({"object": "list", "data": SYMBOLS})
        if u.path == "/cards/named":
            exact = urllib.parse.parse_qs(u.query).get("exact", [""])[0]
            if urllib.parse.parse_qs(u.query).get("format", [""])[0] == "image":
                calls.append("NAMED-IMAGE " + exact)
                return route.fulfill(status=200, content_type="image/png", body=ART_PNG)
            if exact == "Khalni Garden":
                return J({"object": "card", "name": "Khalni Garden", "artist": "Ryan Pancoast", "set": "wwk",
                          "image_uris": {"art_crop": "https://cards.scryfall.io/art_crop/front/khalni.jpg"}})
            return J(YAWG)
        if u.path == "/catalog/creature-types":
            return J({"object": "catalog", "data": ["Bird", "Dragon", "Elf", "Monkey", "Pirate", "Zombie", "Brushwagg", "Shapeshifter"]})
        m = re.match(r"^/cards/(\w+)/(\w+)/(\w+)$", u.path)
        if m and PRINTINGS_MODE["file"]:   # one printing in one language, as a language button from the printings file asks
            hit = [c for c in CARDS + MULTI if (c["set"], c["collector_number"], c["lang"]) == m.groups()]
            calls.append("LANG-LOOKUP " + u.path)
            return J(hit[0]) if hit else J({"object": "error"}, 404)
        m = re.match(r"^/cards/(\w+)/(\w+)/ja$", u.path)
        if m:
            hit = [c for c in CARDS if c["set"] == m.group(1) and c["collector_number"] == m.group(2) and c["lang"] == "ja"]
            calls.append("JA-LOOKUP " + u.path)
            return J(hit[0]) if hit else J({"object": "error"}, 404)
        m = re.match(r"^/cards/(\w+)/(\w+)/en$", u.path)
        if m:
            hit = [c for c in CARDS if c["set"] == m.group(1) and c["collector_number"] == m.group(2) and c["lang"] == "en"]
            calls.append("EN-LOOKUP " + u.path)
            return J(hit[0]) if hit else J({"object": "error"}, 404)
        m = re.match(r"^/cards/([\w-]+)$", u.path)
        if m and m.group(1) in BY_ID:
            return J(BY_ID[m.group(1)])
        return J({"object": "error"}, 404)
    if u.netloc == "cards.scryfall.io":
        if "art_crop/front/q/p/qp-ja" in u.path:
            return route.fulfill(status=404, body="")
        return route.fulfill(status=200, content_type="image/png", body=ART_PNG if "art_crop" in u.path else CARD_PNG)
    if u.netloc == "svgs.scryfall.io":
        fill = "#b9d7a0" if "card-symbols" in u.path else "#000"
        return route.fulfill(status=200, content_type="image/svg+xml",
                             body=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4.6" fill="{fill}"/><path d="M5 1.6v6.8M3.4 5a1.6 2.2 0 1 0 3.2 0a1.6 2.2 0 1 0-3.2 0" stroke="#111" stroke-width=".7" fill="none"/></svg>')
    if "fonts.g" in u.netloc:
        return route.fulfill(status=200, content_type="text/css", body="")
    return route.fulfill(status=404, body="")

results = []
def check(label, cond, detail=""):
    results.append((label, bool(cond)))
    print(("PASS " if cond else "FAIL ") + label + (f"   [{detail}]" if detail != "" and not cond else ""))

# ---- the card database builder (no browser) ----
sys.path.insert(0, _os.path.join(REPO, "tools"))
import build_ja_database as BJ
def built(*prints):
    e = BJ.CardEntry()
    for c in prints: e.add(dict(c, image_status=c.get("image_status", "highres_scan")))
    return dict(zip(BJ.FIELD_ORDER, e.to_row()))
_b = built(card("acid-it", "acid", "it", "leg", "44", "Acid Rain", rarity="rare"), card("eel-it", "acid", "it", "drk", "9", "Acid Rain", rarity="rare"),
            card("eel-en", "acid", "en", "drk", "9", "Acid Rain", rarity="uncommon", released_at="2021-06-18"))
check("builder: an English printing replaces another language's kept first (no Italian picture); Italian rarities at an English number don't count",
      _b["id"] == "eel-en" and _b["rarity"] == "uncommon" and _b["rarities"] == "ur", _b)
_b = built(card("v-en", "v", "en", "m10", "1", "Sengir Vampire", rarity="uncommon"), card("v-sld", "v", "en", "sld", "9", "Sengir Vampire", rarity="mythic", promo=True),
            card("v-ren", "v", "de", "ren", "5", "Sengir Vampire", rarity="rare"))
check("builder: rarities lists every paper rarity, Secret Lair and a German-only set included, in c u r m s b order",
      _b["rarities"] == "urm" and _b["rarity"] == "uncommon", _b)
_b = built(card("cc-400", "cc", "en", "tdm", "400", "Clarion Conqueror", rarity="mythic", border_color="borderless"),
            card("cc-5", "cc", "en", "tdm", "5", "Clarion Conqueror", rarity="rare", border_color="black"))
check("builder: on a tie, the ordinary frame is shown, not the borderless variant", _b["id"] == "cc-5" and _b["rarities"] == "rm", _b)
# 2.4: every set the card was printed in, its treatments (upper case: a Japanese printing has it)
_b = built(card("t-m10", "t", "en", "m10", "1", "Test", released_at="2009-07-17", frame="2003"),
           card("t-2xm", "t", "en", "2xm", "300", "Test", released_at="2020-08-07", border_color="borderless"),
           card("t-neo", "t", "ja", "neo", "400", "Test", released_at="2022-02-18", frame_effects=["showcase"], printed_name="テスト"),
           card("t-lea", "t", "en", "lea", "5", "Test", released_at="1993-08-05", frame="1993"),
           card("t-sld", "t", "en", "sld", "7", "Test", released_at="2023-01-01", promo_types=["serialized"], finishes=["etched"]))
check("builder: sets lists every set, oldest first; treatments one letter each, upper case for a Japanese printing (showcase)",
      _b["sets"] == "lea m10 2xm neo sld" and _b["treatments"] == "bsoenS", _b)
_b = built(card("y-ja1", "y", "ja", "m10", "1", "Y", released_at="2009-07-17", printed_name="ワイ", printed_text="飛行", printed_type_line="Creature — Bird"),
           card("y-ja2", "y", "ja", "m11", "2", "Y", released_at="2008-01-01", printed_name="ワイ", printed_type_line="クリーチャー — 鳥"))
check("builder: a Japanese type line from another Japanese printing when the one with the text has an English one",
      _b["type_ja"] == "クリーチャー — 鳥" and _b["oracle_ja"] == "飛行", _b)
_pic = [card("p-ja1", "p", "ja", "m10", "1", "P", rarity="rare", printed_name="ピー", image_status="lowres"),
        card("p-ja2", "p", "ja", "m10", "301", "P", rarity="rare", printed_name="ピー", variation=True, set_type="core")]
_b1 = built(*_pic)
_b2 = built(_pic[0], dict(_pic[1], promo=True))
check("builder: no sharp scan of the chosen Japanese printing -> one with a scan at the same rarity in a regular set (not a promo)",
      _b1["id"] == "p-ja2" and _b2["id"] == "p-ja1", (_b1["id"], _b2["id"]))
_P = BJ.Printings()
for _c, _o in ((card("a-ja", "a", "ja", "4bb", "4", "A", rarity="rare"), "a"), (card("a-de", "a", "de", "4bb", "4", "A", rarity="rare"), "a"),
               (card("a-en", "a", "en", "4ed", "4", "A", rarity="rare"), "a"), (card("z-en", "z", "en", "4ed", "5", "Z", rarity="common"), "z"),
               (card("q-ja", "q", "ja", "4bb", "5", "Q", rarity="uncommon"), "q"), (card("bl-en", "a", "en", "a25", "300", "A", border_color="borderless"), "a")):
    _P.add(_c, _o)
_pl = _P.payload()["sets"]
check("printings file: languages per set and number, the twin set's own (4bb/4ed) written lang@set, another card at the same number not mixed in",
      _pl["4bb"]["4"] == ["ja de en@4ed", "r", ""] and _pl["4ed"]["4"] == ["en ja@4bb de@4bb", "r", ""] and _pl["4ed"]["5"] == ["en", "c", ""]
      and _pl["4bb"]["5"] == ["ja", "u", ""] and _pl["a25"]["300"] == ["en", "m", "b"], _pl)
# the check that refuses a rebuild which lost cards
import check_database as CD
def _db_file(rows, name):
    f = os.path.join(PRICE_TMP, name)
    with gzip.open(f, "wt", encoding="utf-8") as g:
        json.dump({"version": 2, "generated": "2026-10-16", "fields": ["id", "oracle_id", "name_en", "name_ja", "oracle_ja", "rarity", "rarities"],
                   "cards": rows}, g, ensure_ascii=False)
    return f
_old = [[f"i{n}", f"o{n}", f"Card {n}", f"カード{n}", "テキスト", "common", "c"] for n in range(200)]
_ok = CD.check(_db_file(_old, "old.json.gz"), _db_file(_old[:198] + [["inew", "onew", "New Card", "新しいカード", "", "rare", "r"]], "ok.json.gz"))
_bad = CD.check(_db_file(_old, "old.json.gz"), _db_file(_old[:160], "bad.json.gz"))
check("database check: a rebuild that lost 2 cards passes, with a note naming the new card; one that lost 40 is refused",
      not _ok[0] and any("新しいカード / New Card" in l for l in _ok[1]) and any("40 cards would disappear" in p for p in _bad[0])
      and "**Refused:**" in _bad[1], (_ok[0], _bad[0]))
# 2.5: a "Japanese" text or type line in English (Edge of Eternities) is passed over for another printing's, or left empty
_b = built(card("w-ja1", "w", "ja", "eoe", "1", "W", released_at="2025-08-01", printed_name="ダブ", printed_text="Draw a card.", printed_type_line="Sorcery"),
           card("w-ja2", "w", "ja", "m10", "2", "W", released_at="2009-07-17", printed_name="ダブ", printed_text="カードを１枚引く。", printed_type_line="ソーサリー"))
_b2 = built(card("v-ja1", "v", "ja", "eoe", "3", "V", printed_name="ブイ", printed_text="Draw a card.", printed_type_line="Sorcery"))
check("builder: a Japanese text or type line with no Japanese in it is passed over for another printing's, or left empty",
      _b["oracle_ja"] == "カードを１枚引く。" and _b["type_ja"] == "ソーサリー" and _b2["oracle_ja"] == "" and _b2["type_ja"] == "" and _b2["name_ja"] == "ブイ", (_b, _b2))
_eng = [[f"i{n}", f"o{n}", f"Card {n}", f"カード{n}", "Draw a card." if n < 100 else "テキスト", "common", "c"] for n in range(200)]
_cut = CD.check(_db_file(_eng, "old.json.gz"), _db_file([r[:4] + [""] + r[5:] if r[4] == "Draw a card." else r for r in _eng], "cut.json.gz"))
check("database check: English texts dropped from oracle_ja are not counted as lost Japanese texts", not _cut[0], _cut[0])

Q = urllib.parse.quote
with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, color_scheme="dark")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "Failed to load resource" not in m.text else None)
    page.route("**/*", handle)
    def theme(): return page.evaluate("document.documentElement.getAttribute('data-theme')")
    def no_hscroll(): return not page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
    def count_text():   # the result count without the "「query」：" part in front
        return page.evaluate("(() => { const c = document.querySelector('#resultCount').cloneNode(true); c.querySelectorAll('.res-q').forEach(e => e.remove()); return c.textContent; })()")
    def open_adv():
        if not page.locator("#filterPanel").is_visible():
            page.click("#advToggle" if page.locator("#advToggle").is_visible() else "#filterOpenBtn")
            page.wait_for_selector("#filterPanel", state="visible")
    def home(url=None):
        page.goto(url or SITE)
        page.wait_for_selector("#homeHero", state="visible")
        page.wait_for_function("typeof dbState !== 'undefined' && dbState !== 'loading'")
    def top_search(q):
        sel = "#searchInput" if page.locator("#searchInput").is_visible() else "#heroInput"
        page.fill(sel, q); page.press(sel, "Escape"); page.press(sel, "Enter")

    # ---- 1. homepage ----
    n_home = len(calls)
    home()
    page.wait_for_selector("#hxList .hx-entry")
    check("home page: no card grid any more (the effect examples show cards)", not page.locator("#cardGrid").is_visible() and page.locator("#cardGrid .card-tile").count() == 0
          and not any("/cards/random" in c or "/cards/search" in c for c in calls[n_home:]))
    check("default theme follows the device (dark)", theme() == "dark")
    check("footer shows database count", "収録カード：7枚（日本語版あり 6枚）" in page.locator("#dbCount").inner_text(), page.locator("#dbCount").inner_text())

    # ---- 2. advanced search under the search bar + suggestion lists ----
    panel = page.locator("#filterPanel")
    check("home: hero with the search box; advanced search folded away", page.locator("#homeHero").is_visible() and page.locator("#heroInput").is_visible()
          and not panel.is_visible() and page.get_attribute("#advToggle", "aria-expanded") == "false")
    page.click("#advToggle")
    hb, pbox = page.locator("#heroInput").bounding_box(), panel.bounding_box()
    check("advanced search opens right under the search bar", panel.is_visible() and pbox["y"] > hb["y"] + hb["height"] and pbox["width"] > 500
          and page.evaluate("document.getElementById('heroAdvSlot').contains(document.getElementById('filterPanel'))")
          and page.get_attribute("#advToggle", "aria-expanded") == "true", pbox)
    check("colour and mana value chips are mana symbols (incl. colourless and X)",
          [c.get_attribute("data-color") for c in page.locator("#filterPanel .chip").all()] == ["W", "U", "B", "R", "G", "C"]
          and all("/card-symbols/" in s for s in page.evaluate("[...document.querySelectorAll('#filterPanel .chip img, #filterPanel .mv-chip img')].map(i => i.src)"))
          and page.locator(".mv-chip img[src$='X.svg']").count() == 1 and page.locator(".mv-chip img[src$='C.svg']").count() == 0
          and page.locator(".chip[data-color=C] img").get_attribute("src").endswith("/C.svg"))
    check("type suggestion list stays closed until the box is used", not page.locator("#creatureTypeList").is_visible())
    page.focus("#creatureTypeFilter")
    page.wait_for_function("document.querySelectorAll('#creatureTypeList .check-row').length === 8")
    box = page.locator("#creatureTypeList").bounding_box(); ib = page.locator("#creatureTypeFilter").bounding_box()
    check("creature types: list opens under the box", page.locator("#creatureTypeList").is_visible() and box["y"] >= ib["y"] + ib["height"] - 3 and abs(box["x"] - ib["x"]) < 2
          and page.get_attribute("#creatureTypeFilter", "aria-expanded") == "true", (box, ib))
    rows = page.locator("#creatureTypeList .check-row span:first-of-type").all_inner_texts()
    check("types without a Japanese name still listed", "Shapeshifter" in rows or "多相の戦士" in rows, rows)
    page.locator("#creatureTypeFilter").press_sequentially("どら")
    page.wait_for_function("document.querySelectorAll('#creatureTypeList .check-row').length === 1")
    check("creature types: hiragana finds the katakana name, typed part in bold",
          page.locator("#creatureTypeList .check-row").inner_text().split() == ["ドラゴン", "Dragon"] and page.locator("#creatureTypeList .check-row b").first.inner_text() == "ドラ",
          page.locator("#creatureTypeList").inner_html())
    page.fill("#creatureTypeFilter", "e")
    order = page.locator("#creatureTypeList .check-row span:first-of-type").all_inner_texts()
    check("creature types: names starting with the text come first", order and order[0] == "エルフ" and len(order) >= 4, order)
    page.fill("#creatureTypeFilter", "ドラゴン")
    row = page.locator("#creatureTypeList .check-row", has_text="ドラゴン")
    rb = row.bounding_box()
    check("the option is on screen and clickable", rb["y"] >= 0 and rb["y"] + rb["height"] <= 900, rb)
    row.click()
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました')")
    check("creature-type filter works", page.locator("#cardGrid .card-name-main").all_inner_texts() == ["シヴ山のドラゴン"])
    check("active filter shown as a pill; box cleared for the next type", page.locator("#activeFilters .filter-pill").all_inner_texts() == ["ドラゴン×"]
          and page.input_value("#creatureTypeFilter") == "", page.locator("#activeFilters .filter-pill").all_inner_texts())
    pb2, gb2 = panel.bounding_box(), page.locator("#cardGrid").bounding_box()
    check("results page (wide screen): the advanced search is a sidebar left of the results", panel.is_visible() and not page.locator("#homeHero").is_visible()
          and page.evaluate("document.getElementById('sideAdvSlot').contains(document.getElementById('filterPanel'))")
          and pb2["x"] + pb2["width"] <= gb2["x"] and 230 <= pb2["width"] <= 280 and not page.locator("#filterOpenBtn").is_visible(), (pb2, gb2))
    page.fill("#creatureTypeFilter", "elf"); page.press("#creatureTypeFilter", "Enter")
    page.wait_for_function("document.querySelectorAll('#activeFilters .filter-pill').length === 2")
    check("creature types: Enter picks the top suggestion", sorted(page.locator("#activeFilters .filter-pill").all_inner_texts()) == ["エルフ×", "ドラゴン×"])
    page.locator("#activeFilters .filter-pill", has_text="エルフ").click()
    page.wait_for_function("document.querySelectorAll('#activeFilters .filter-pill').length === 1")
    page.press("#creatureTypeFilter", "Escape")
    check("Escape closes the suggestion list", not page.locator("#creatureTypeList").is_visible())
    page.locator(".opt-chip[data-group=types][data-value=instant]").click()
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('0')")
    check("combining filters narrows results (dragon + instant = 0)", page.locator("#cardGrid .card-tile").count() == 0)
    page.locator("#activeFilters .filter-pill", has_text="ドラゴン").click()
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 1")
    check("removing a pill updates results (instant only)", page.locator("#cardGrid .card-name-main").all_inner_texts() == ["稲妻"])
    page.focus("#creatureTypeFilter")
    check("checkbox unticked after pill removed", page.locator("#creatureTypeList input:checked").count() == 0)
    page.press("#creatureTypeFilter", "Escape")
    page.locator(".chip[data-color=W]").click()
    page.locator(".opt-chip[data-group=types][data-value=instant]").click()
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 2")
    check("colour filter (white) finds white cards, incl. the English-only one (name printed once)",
          sorted(page.locator("#cardGrid .card-name-main").all_inner_texts()) == ["English Only Thing", "クァーサルの群れ魔道士"]
          and page.locator("#cardGrid .card-name-sub").all_inner_texts() == ["Qasali Pridemage"])
    page.fill("#keywordFilter", "fly")
    check("keywords: suggestions from the English name too", page.locator("#keywordList .check-row").first.inner_text().split() == ["飛行", "Flying"], page.locator("#keywordList").inner_text()[:200])
    page.fill("#keywordFilter", "飛行")
    page.locator("#keywordList .check-row", has_text="飛行").first.click()
    page.locator(".chip[data-color=W]").click()
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 2")
    check("keyword filter (飛行) works", sorted(page.locator("#cardGrid .card-name-main").all_inner_texts()) == ["English Only Thing", "シヴ山のドラゴン"])
    page.locator(".opt-chip[data-group=rarity][data-value=rare]").click()
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 1")
    page.locator(".opt-chip[data-group=manaCosts][data-value='6']").click()
    page.wait_for_function("document.querySelectorAll('#activeFilters .filter-pill').length === 3")
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 1")
    _got = page.locator("#cardGrid .card-tile").all_inner_texts()
    check("rarity + mana value filters", len(_got) == 1 and "シヴ山のドラゴン" in _got[0] and page.locator(".opt-chip[data-group=manaCosts][data-value='6']").get_attribute("aria-pressed") == "true")
    check("format filter waits for a database with legality data", page.locator("#formatSelect").is_disabled())
    page.click("#clearBtn")
    page.wait_for_selector("#homeHero", state="visible")
    check("clear returns to the home page, no pills", page.locator("#activeFilters .filter-pill").count() == 0 and page.locator("#cardGrid .card-tile").count() == 0 and page.locator("#homeHero").is_visible())
    page.fill("#keywordFilter", "")
    if page.locator("#filterPanel").is_visible(): page.click("#advToggle")
    check("advanced search folds away again", not panel.is_visible())

    # ---- 3. search + card page ----
    top_search("ラガバン")
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました')")
    check("search by Japanese name", page.locator("#cardGrid .card-name-main").all_inner_texts() == ["敏捷なこそ泥、ラガバン"])
    page.locator("#cardGrid .card-tile").first.click()
    page.wait_for_selector("#cardView .print-item")
    check("card URL", "?card=rag-ja-mh2" in page.url, page.url)
    art, info = page.locator(".cp-art").bounding_box(), page.locator(".cp-info").bounding_box()
    check("card page is two columns on desktop (image left, details right)", art["x"] + art["width"] <= info["x"] + 1 and abs(art["y"] - info["y"]) < 4, (art, info))
    price = page.locator("#cardViewCard .price-section").inner_text()
    check("prices in yen by default, the shop's dollar price on hover", "¥6,000" in price and "¥9,000" in price and "$40.00" not in price
          and page.locator("#cardViewCard .sp-val .cur").first.get_attribute("title") == "$40.00", price)
    page.wait_for_function("document.querySelector('#priceAvg').textContent.includes('平均')")
    check("average across printings", "¥6,800" in page.locator("#priceAvg").inner_text(), page.locator("#priceAvg").inner_text())
    check("all 3 printings in gallery", page.locator("#versionMenuPanel .print-item").count() == 3)
    href = lambda label: page.locator("#cardViewCard a.external-link-btn, #cardViewCard a.jp-shop", has_text=label).first.get_attribute("href")   # the Japanese shops are in the 日本 tab's list
    check("Hareruya: Japanese name on the Japanese site", href("晴れる屋") == "https://www.hareruyamtg.com/ja/products/search?product=" + Q("敏捷なこそ泥、ラガバン"), href("晴れる屋"))
    check("BIG MAGIC: own search, English name (no Google)", href("BIG MAGIC") == "https://www.bigweb.co.jp/ja/products/mtg/list?name=" + Q("Ragavan, Nimble Pilferer"), href("BIG MAGIC"))
    check("Tokyo MTG: own search, English name (no Google)", href("Tokyo MTG") == "https://tokyomtg.com/cardpage.html?p=q&query=" + Q("Ragavan, Nimble Pilferer"), href("Tokyo MTG"))
    check("MTGDecks: English card page", href("MTGDecks") == "https://mtgdecks.net/prices/ragavan-nimble-pilferer", href("MTGDecks"))
    check("MTGGoldfish: site search, English name", href("MTGGoldfish") == "https://www.mtggoldfish.com/q?query_string=Ragavan%2C+Nimble+Pilferer", href("MTGGoldfish"))
    check("no Google links anywhere on the card page", page.locator("#cardViewCard a[href*='google.']").count() == 0)
    check("link helpers handle apostrophes/accents and reject Japanese names", page.evaluate("""() => [
        mtgDecksSlug("Urza's Saga"), mtgDecksSlug("Lórien Revealed"),
        englishName({ name: "稲妻", oracle_id: "bolt-oracle" }),
        englishName({ name: "稲妻", oracle_id: "nope" }),
        mtgDecksUrl({ name: "稲妻", oracle_id: "nope" }),
        englishName({ name: "Fable of the Mirror-Breaker // Reflection of Kiki-Jiki", card_faces: [{ name: "Fable of the Mirror-Breaker" }] }),
      ]""") == ["urza-s-saga", "lorien-revealed", "Lightning Bolt", "", "", "Fable of the Mirror-Breaker"])
    if SHOTS: page.screenshot(path="card_dark.png", full_page=True)

    # set link on the card page, then search from the top bar while on another page
    page.locator("#cardViewCard .cp-set-link").click()
    page.wait_for_selector("#setGrid .card-tile")
    check("set link on card page opens the set", "?set=mh2" in page.url and page.locator("#setGrid .card-tile").count() == 2, page.url)
    top_search("稲妻")
    page.wait_for_function("document.getElementById('searchView').style.display === '' && document.querySelector('#resultCount').textContent.includes('件見つかりました')")
    check("top-bar search works from the set page", page.locator("#cardGrid .card-name-main").all_inner_texts() == ["稲妻"] and "set=" not in page.url, page.url)
    page.locator("#cardGrid .card-tile").first.click(); page.wait_for_selector("#cardView .cp-name")
    check("apostrophe-free card: MTGDecks link", href("MTGDecks") == "https://mtgdecks.net/prices/lightning-bolt")
    page.goto(SITE + "?card=saga-ja"); page.wait_for_selector("#cardView .cp-name")
    check("Urza's Saga → urza-s-saga on MTGDecks", href("MTGDecks") == "https://mtgdecks.net/prices/urza-s-saga", href("MTGDecks"))
    check("Urza's Saga on MTGGoldfish", href("MTGGoldfish") == "https://www.mtggoldfish.com/q?query_string=Urza's+Saga".replace("'", "'") or "Urza" in href("MTGGoldfish"), href("MTGGoldfish"))
    page.goto(SITE + "?card=eo-1"); page.wait_for_selector("#cardView .cp-name")
    check("English-only card → Hareruya English site", href("晴れる屋") == "https://www.hareruyamtg.com/en/products/search?product=English%20Only%20Thing", href("晴れる屋"))

    # ---- 4. sets tab ----
    page.click("#tabSets"); page.wait_for_selector("#setList .set-row")
    check("sets tab", page.get_attribute("#tabSets", "aria-selected") == "true" and "view=sets" in page.url)
    check("set list (expansions/core)", page.locator("#setList .set-name-ja").all_inner_texts() == ["English Only Set", "Magic 2010"])
    page.fill("#setFilter", "モダン")
    page.locator("#setList .set-row").first.click(); page.wait_for_selector("#setGrid .card-tile")
    check("set page lists its cards", sorted(page.locator("#setGrid .card-name-main").all_inner_texts()) == ["ウルザの物語", "敏捷なこそ泥、ラガバン"])
    if SHOTS: page.screenshot(path="set_dark.png", full_page=False)

    # ---- 5. themes: a square dark-mode switch; 端正な明朝 ----
    home()
    sw = page.locator("#darkSwitch")
    radii = page.evaluate("[getComputedStyle(document.querySelector('#darkSwitch .sq-track')).borderRadius, getComputedStyle(document.querySelector('#darkSwitch .sq-knob')).borderRadius]")
    check("dark mode is a square switch (a switch role, square track and knob), on in dark mode", sw.get_attribute("role") == "switch" and sw.get_attribute("aria-checked") == "true"
          and radii == ["4px", "2px"], radii)
    knob_on = page.locator("#darkSwitch .sq-knob").bounding_box()["x"] - page.locator("#darkSwitch .sq-track").bounding_box()["x"]
    page.click("#darkSwitch"); page.wait_for_timeout(300)
    knob_off = page.locator("#darkSwitch .sq-knob").bounding_box()["x"] - page.locator("#darkSwitch .sq-track").bounding_box()["x"]
    bg = page.evaluate("getComputedStyle(document.documentElement).backgroundColor")
    fg = page.evaluate("getComputedStyle(document.body).color")
    check("switching dark mode off: light page, dark text", theme() == "light" and bg == "rgb(241, 240, 245)" and fg == "rgb(29, 26, 43)", (bg, fg))
    check("the switch shows off, knob slid to the left", sw.get_attribute("aria-checked") == "false" and knob_on - knob_off >= 16, (knob_on, knob_off))
    check("light theme: a darker lime green that reads on white", page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()") == "#4a7a0a")
    if SHOTS: page.screenshot(path="home_light.png", full_page=False)
    page.reload(); page.wait_for_selector("#homeHero", state="visible")
    check("theme choice remembered after reload", theme() == "light" and sw.get_attribute("aria-checked") == "false")
    sw.focus(); page.keyboard.press("Space")
    check("dark theme (switch works from the keyboard too): black and grey", theme() == "dark" and page.evaluate("getComputedStyle(document.documentElement).backgroundColor") == "rgb(13, 13, 14)"
          and page.evaluate("getComputedStyle(document.querySelector('.topbar')).backgroundColor") == "rgb(18, 18, 20)" and sw.get_attribute("aria-checked") == "true")
    check("Yawgmoth mode removed: the switches are dark mode and lite mode", [x.strip() for x in page.locator(".sq-switch").all_inner_texts()] == ["ダーク", "軽量"]
          and page.locator("#yawgBackdrop, #fallLayer, .yawg-window, #yawgCredit, .theme-btn").count() == 0, page.locator(".sq-switch").all_inner_texts())
    if SHOTS: page.screenshot(path="home_dark.png", full_page=False)
    page.evaluate("localStorage.setItem('akuchie-theme', 'yawgmoth')"); page.reload(); page.wait_for_selector("#homeHero", state="visible")
    check("a saved Yawgmoth choice falls back to light or dark", theme() in ("light", "dark") and sw.get_attribute("aria-checked") == str(theme() == "dark").lower(), theme())
    if theme() != "dark": page.click("#darkSwitch")
    fonts = page.evaluate("""[getComputedStyle(document.querySelector('.brand-mark')).fontFamily, getComputedStyle(document.querySelector('.hero-title')).fontFamily,
        getComputedStyle(document.body).fontFamily, [...document.querySelectorAll('link[href*="fonts.googleapis"]')].map(l => l.href).join(' ')]""")
    check("端正な明朝: Zen Old Mincho for the logo and headings, Zen Kaku Gothic New for text", fonts[0].replace('"', '').startswith('Zen Old Mincho') and fonts[1].replace('"', '').startswith('Zen Old Mincho')
          and fonts[2].replace('"', '').startswith('Zen Kaku Gothic New') and "Zen+Old+Mincho" in fonts[3] and "Zen+Kaku+Gothic+New" in fonts[3] and "DotGothic" not in fonts[3], fonts)
    check("the fonts download from Google Fonts", any("fonts.googleapis.com/css2?family=Zen+Old+Mincho" in c for c in calls))

    # ---- 6. phone layout ----
    page.set_viewport_size({"width": 390, "height": 800})
    home()
    check("phone: no sideways scrolling (home)", no_hscroll())
    page.wait_for_selector("#hxList .hx-entry")
    eb = page.locator("#heroExample").bounding_box()
    check("phone: the effect examples fit the screen", eb["x"] >= 0 and eb["x"] + eb["width"] <= 390, eb)
    check("phone: the switches are tucked into the menu", not page.locator("#darkSwitch").is_visible() and not page.locator("#liteSwitch").is_visible() and page.locator("#menuBtn").is_visible())
    page.click("#menuBtn")
    check("phone: menu opens with both switches", page.locator("#darkSwitch").is_visible() and page.locator("#liteSwitch").is_visible() and page.get_attribute("#menuBtn", "aria-expanded") == "true")
    mb = [page.locator(x).bounding_box() for x in ("#darkSwitch", "#liteSwitch")]
    check("phone: the switches fit the screen, one under the other", all(r["x"] >= 0 and r["x"] + r["width"] <= 390 for r in mb) and mb[1]["y"] >= mb[0]["y"] + mb[0]["height"] - 1, mb)
    if SHOTS: page.screenshot(path="menu_phone.png", full_page=False)
    page.click("#darkSwitch")
    check("phone: the dark switch works in the menu, which stays open", theme() == "light" and page.locator("#darkSwitch").is_visible())
    page.click("#darkSwitch")
    page.click("#homeHero .hero-title")
    check("phone: menu closes when tapping elsewhere", not page.locator("#darkSwitch").is_visible() and theme() == "dark")
    check("phone: advanced search folded until opened", not page.locator("#filterPanel").is_visible())
    page.click("#advToggle"); page.wait_for_timeout(200)
    pb = page.locator("#filterPanel").bounding_box()
    check("phone: advanced search opens in the page, fully on screen", page.locator("#filterPanel").is_visible() and pb["x"] >= 0 and pb["x"] + pb["width"] <= 390 and no_hscroll(), pb)
    page.locator("#creatureTypeFilter").scroll_into_view_if_needed()
    page.fill("#creatureTypeFilter", "ドラゴン")
    lb = page.locator("#creatureTypeList").bounding_box()
    check("phone: type suggestions fit the screen", lb["x"] >= 0 and lb["x"] + lb["width"] <= 390, lb)
    if SHOTS: page.screenshot(path="filters_phone.png", full_page=False)
    page.locator("#creatureTypeList .check-row", has_text="ドラゴン").click()
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 1")
    page.click("#filterClose"); page.wait_for_timeout(200)
    check("phone: panel closes, filter applied, count on button", not page.locator("#filterPanel").is_visible() and page.locator("#filterOpenBtn").inner_text() == "詳しい条件（1）" and page.locator("#cardGrid .card-tile").count() == 1, page.locator("#filterOpenBtn").inner_text())
    page.goto(SITE + "?card=rag-ja-mh2"); page.wait_for_selector("#cardView .print-item")
    art, name, text = page.locator(".cp-art").bounding_box(), page.locator(".cp-name").bounding_box(), page.locator(".cp-text").bounding_box()
    check("phone: card page - small picture with the name beside it, rules text full width below", 120 <= art["width"] <= 140 and name["x"] > art["x"] + art["width"]
          and text["y"] >= art["y"] + art["height"] - 1 and text["width"] > 330 and no_hscroll(), (art, name, text))
    if SHOTS: page.screenshot(path="card_phone.png", full_page=False)
    page.goto(SITE + "?view=sets"); page.wait_for_selector("#setList .set-row")
    check("phone: no sideways scrolling (sets)", no_hscroll())

    # =====================================================================
    # ---- 7. back button ----
    page.set_viewport_size({"width": 1280, "height": 900})
    page.evaluate("localStorage.clear()")
    home()
    top_search("ドラゴン")
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました')")
    page.locator("#cardGrid .card-tile").first.click(); page.wait_for_selector("#cardView .cp-name")
    page.click("#backToSearchBtn")
    page.wait_for_function("document.getElementById('searchView').style.display === ''")
    check("back button returns to the same search results", page.locator("#cardGrid .card-name-main").all_inner_texts() == ["シヴ山のドラゴン"] and "card=" not in page.url, page.url)
    page.goto(SITE + "?card=bolt-ja-m10"); page.wait_for_selector("#cardView .cp-name")
    page.click("#backToSearchBtn"); page.wait_for_selector("#homeHero", state="visible")
    check("back button on a directly opened card goes to the home page", "card=" not in page.url and page.locator("#homeHero").is_visible(), page.url)

    # ---- 8. English mode ----
    JP = re.compile(r"[ぁ-んァ-ヶ一-龥]")
    lang = lambda: page.evaluate("document.documentElement.lang")
    check("site starts in Japanese; the JP | EN switch shows JP chosen", lang() == "ja" and page.locator("#langBtn [aria-pressed=true]").inner_text() == "JP")
    n_before = len(calls)
    page.click("#langBtn [aria-pressed=false]")
    page.wait_for_function("document.documentElement.lang === 'en' && document.querySelector('#hxList .hx-effect') && !/[ぁ-んァ-ヶ一-龥]/.test([...document.querySelectorAll('#hxList .hx-effect')].map(b => b.textContent).join(''))")
    check("English mode: html lang, the switch shows EN chosen", lang() == "en" and page.locator("#langBtn [aria-pressed=true]").inner_text() == "EN")
    check("English mode: the effect examples switch to English", page.locator("#hxList .hx-entry").count() >= 1 and page.locator("#hxLabel").inner_text() == "Effects to try",
          page.locator("#hxList .hx-effect").all_inner_texts())
    top_search("Shivan Dragon")
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('found') && document.querySelector('#cardGrid .card-tile img')")
    page.wait_for_function("document.querySelector('#cardGrid .card-tile img').src.includes('drag-en')")
    tile = page.locator("#cardGrid .card-tile").first.inner_text()
    check("English mode: English name first with the Japanese beside it, English printing, type line, rarity and price",
          page.locator("#cardGrid .card-name-main").first.inner_text() == "Shivan Dragon" and page.locator("#cardGrid .card-name-sub").first.inner_text() == "シヴ山のドラゴン"
          and "Creature — Dragon" in tile and "Rare" in tile and "¥75" in tile and page.locator("#cardGrid .card-tile .cur").first.get_attribute("title") == "$0.50", tile)
    ui = {sel: page.locator(sel).inner_text() for sel in [".top-tabs", ".theme-switch", "#filterPanel .filter-head", ".toolbar", "#guidePanel", "#dbCount", "#searchBtn"]}
    titles = page.locator("#filterPanel .filter-title").all_inner_texts()
    chips = page.locator("#filterPanel .opt-chip").all_inner_texts() + page.locator("#filterPanel .chip").all_inner_texts()
    leftovers = [(k, v) for k, v in ui.items() if JP.search(v)] + [x for x in titles + chips if JP.search(x)]
    check("English mode: no Japanese left in the interface text", not leftovers, leftovers)
    check("English mode: labels", ui[".top-tabs"].split() == ["Cards", "Sets", "Metagame", "Prices"] and "found" in ui[".toolbar"]
          and titles == ["Color", "Mana value", "Rarity", "Card type", "Role", "Creature type", "Keyword ability", "Format"]
          and "7 cards in the database (6 with a Japanese printing)" in ui["#dbCount"], (ui[".top-tabs"], titles, ui["#dbCount"]))
    check("English mode: search box placeholder", page.get_attribute("#searchInput", "placeholder").startswith("Card name or rules text"))
    page.focus("#creatureTypeFilter")
    ct = page.locator("#creatureTypeList .check-row span:first-of-type").all_inner_texts()
    dragon_row = page.locator("#creatureTypeList .check-row", has_text="Dragon").locator("span").all_inner_texts()
    check("English mode: creature types A–Z in English, Japanese beside", ct == sorted(ct) and ct[0] == "Bird" and dragon_row == ["Dragon", "ドラゴン"], (ct, dragon_row))
    page.press("#creatureTypeFilter", "Escape")
    page.click("#guidePanel summary")
    check("English mode: search tips in English", "Card name (English or Japanese)" in page.locator("#guideRows").inner_text() and page.locator("#guideExamples .example-pill").first.inner_text() == "flying lifelink")
    page.locator("#guideExamples .example-pill", has_text="o:damage c:r").click()
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('found')")
    check("English mode: example search works", count_text() == "2 cards found" and page.locator("#cardGrid .card-name-main").all_inner_texts() == ["Lightning Bolt", "Ragavan, Nimble Pilferer"], count_text())
    top_search("flying")
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('2 cards found')")
    open_adv()
    page.locator(".chip[data-color=W]").click()
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('1 card found')")
    check("English mode: filter pill, singular count", count_text() == "1 card found" and page.locator("#activeFilters .filter-pill").all_inner_texts() == ["Color: White×"], page.locator("#activeFilters .filter-pill").all_inner_texts())
    page.click("#clearBtn")
    top_search("Ragavan")
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 1 && document.querySelector('#resultCount').textContent.includes('found')")
    page.locator("#cardGrid .card-tile").first.click(); page.wait_for_selector("#cardView .print-item")
    info = page.locator("#cardViewCard .cp-info").inner_text()
    check("English card page: English name, type and rules text", page.locator(".cp-name").inner_text() == "Ragavan, Nimble Pilferer"
          and page.locator(".cp-name-sub").inner_text() == "敏捷なこそ泥、ラガバン" and "Legendary Creature — Monkey Pirate" in info
          and "create a Treasure token" in info, info[:300])
    check("English card page: section labels and legality", all(x in info for x in ["Price", "Non-foil", "¥6,000", "Find it in shops", "Decks", "Formats", "Banned", "Restricted", "Mythic"])
          and not JP.search(info.replace("敏捷なこそ泥、ラガバン", "")), info)
    check("English card page: Hareruya link goes to the English site", href("Hareruya") == "https://www.hareruyamtg.com/en/products/search?product=" + Q("Ragavan, Nimble Pilferer"), href("Hareruya"))
    page.wait_for_function("document.querySelector('#priceAvg').textContent.includes('Average')")
    vh = page.locator("#versionMenuHeading").inner_text()
    tags = page.locator("#versionMenuPanel .print-tag").all_inner_texts()
    check("English card page: printings list in English", vh == "All printings and treatments (3)" and "Borderless" in tags and "Showcase" in tags and "Regular" in tags
          and "Average of 3 printings" in page.locator("#priceAvg").inner_text() and page.locator("#versionMenuPanel .print-item.current").count() == 1, (vh, tags))
    check("English mode: page title", page.title() == "Ragavan, Nimble Pilferer — 悪知恵", page.title())
    if SHOTS: page.screenshot(path="card_en.png", full_page=False)
    # switching language while on the card page re-draws it in place
    page.click("#langBtn [aria-pressed=false]")
    page.wait_for_function("document.querySelector('.cp-name').textContent === '敏捷なこそ泥、ラガバン'")
    check("switching back on the card page shows Japanese again (no refetch of printings needed)",
          "フォーマット" in page.locator("#cardViewCard .cp-info").inner_text() and "使用デッキ" in page.locator("#cardViewCard .cp-info").inner_text() and page.locator("#versionMenuHeading").inner_text() == "すべての版・仕様（3）")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.querySelector('.cp-name').textContent === 'Ragavan, Nimble Pilferer'")
    page.reload(); page.wait_for_selector("#cardView .print-item")
    check("language choice remembered after reload", lang() == "en" and page.locator(".cp-name").inner_text() == "Ragavan, Nimble Pilferer" and page.locator("#tabSets").inner_text() == "Sets")
    page.click("#tabSets"); page.wait_for_selector("#setList .set-row")
    check("English mode: set list", page.locator("#setList .set-name-ja").all_inner_texts() == ["English Only Set", "Magic 2010"] and "249 cards" in page.locator("#setList").inner_text()
          and page.get_attribute("#setFilter", "placeholder").startswith("Find a set"), page.locator("#setList").inner_text())
    page.locator("#setList .set-row", has_text="Magic 2010").click(); page.wait_for_selector("#setGrid .card-tile")
    check("English mode: a set opens with its English printings", "4 cards (English, by collector number)" in page.locator("#setResultCount").inner_text()
          and page.get_attribute("#setHeader .set-lang-btn[data-lang=en]", "aria-pressed") == "true"
          and "Released 2009-07-17" in page.locator("#setHeader").inner_text(), page.locator("#setResultCount").inner_text())
    page.locator("#setHeader .set-lang-btn[data-lang=ja]").click()
    page.wait_for_function("document.querySelector('#setResultCount').textContent.includes('Japanese')")
    check("English mode: set page can still list the Japanese printings", "lang=ja" in page.url and all("-ja" in i for i in page.evaluate("[...document.querySelectorAll('#setGrid .card-tile')].map(a => a.dataset.id)")))
    if SHOTS:
        home(); page.wait_for_timeout(300)
        page.screenshot(path="home_en.png", full_page=False)

    # ---- 9. metagame tab (fixture data, English) ----
    home()
    page.click("#tabMeta"); page.wait_for_selector("#metaBody .meta-row")
    check("metagame tab opens with its own URL", "view=meta" in page.url and "format=standard" in page.url and page.get_attribute("#tabMeta", "aria-selected") == "true", page.url)
    check("metagame: six formats, two periods", page.locator("#metaFormats .seg-btn").all_inner_texts() == ["Standard", "Pioneer", "Modern", "Legacy", "Vintage", "Pauper"]
          and page.locator("#metaWindows .seg-btn").all_inner_texts() == ["Last 30 days", "Last 90 days"]
          and page.get_attribute("#metaWindows .seg-btn[data-days='30']", "aria-pressed") == "true")
    check("metagame: summary line", page.locator("#metaSummary").inner_text().replace("　", " ") == "2026-09-07 – 2026-10-06 12 events · 400 decks · 1,234 matches", page.locator("#metaSummary").inner_text())
    rows = page.locator("#metaBody .meta-row")
    r0 = rows.nth(0).inner_text()
    check("metagame: top deck with share, deck count, win rate and matches", all(x in r0 for x in ["Gruul Dragons", "25.0%", "100 decks", "55.0%", "400 matches"]), r0)
    widths = page.evaluate("[...document.querySelectorAll('#metaBody .bar-fill')].map(b => Math.round(100 * b.getBoundingClientRect().width / b.parentElement.getBoundingClientRect().width))")
    check("metagame: share bars are proportional (25 : 12.5 : 7.5 : 5)", widths == [100, 50, 30, 20], widths)
    dot = page.evaluate("(() => { const r = document.querySelector('#metaBody .meta-row'); const t = r.querySelector('.wr-track').getBoundingClientRect(); const d = r.querySelector('.wr-dot').getBoundingClientRect(); const c = r.querySelector('.wr-ci').getBoundingClientRect(); return [(d.left + d.width / 2 - t.left) / t.width, (c.left - t.left) / t.width, (c.right - t.left) / t.width]; })()")
    check("metagame: win-rate dot and interval placed on the 30–70% scale (55% → 62.5%, 50–60% → 50–75%)", abs(dot[0] - 0.625) < 0.01 and abs(dot[1] - 0.5) < 0.01 and abs(dot[2] - 0.75) < 0.01, dot)
    check("metagame: colour pips are mana symbols", [i.get_attribute("alt") for i in rows.nth(0).locator("img.pip").all()] == ["{R}", "{G}"])
    chips0 = rows.nth(0).locator(".meta-card")
    check("metagame: key cards (lands left out, unknown cards still named)", chips0.all_inner_texts() == ["Shivan Dragon", "Lightning Bolt", "Llanowar Elves", "Unknown New Card"]
          and chips0.nth(0).get_attribute("href") == "?card=drag-ja" and chips0.nth(3).get_attribute("href") is None, chips0.all_inner_texts())
    sm = rows.nth(0).locator(".meta-sample a")
    check("metagame: sample list link", sm.get_attribute("href") == "https://melee.gg/Decklist/View/abc" and "1st Place · Big Open" in sm.inner_text() and sm.get_attribute("target") == "_blank", sm.inner_text())
    r2, r3 = rows.nth(2).inner_text(), rows.nth(3).inner_text()
    check("metagame: too few matches → no win rate shown", "Too few matches (22)" in r2 and "—" in r2 and rows.nth(2).locator(".wr-dot").count() == 0, r2)
    check("metagame: unclassified decks are labelled", "Orzhov (unclassified)" in r3 and "40.0%" in r3, r3)
    check("metagame: remaining archetypes summed up", page.locator("#metaBody .meta-rest").inner_text() == "7 other archetypes: 50.0% in total (200 decks)", page.locator("#metaBody .meta-rest").inner_text())
    check("metagame: hover details", "220 wins, 180 losses" in rows.nth(0).locator(".meta-wr").get_attribute("title") and "95% interval 50.0–60.0%" in rows.nth(0).locator(".meta-wr").get_attribute("title"), rows.nth(0).locator(".meta-wr").get_attribute("title"))
    page.wait_for_function("[...document.querySelectorAll('#metaBody .meta-art img')].every(i => i.complete && i.naturalWidth > 0)")
    page.wait_for_timeout(300)
    arts = page.evaluate("""[...document.querySelectorAll('#metaBody .meta-row')].map(r => { const a = r.querySelector('.meta-art'); const i = a && a.querySelector('img');
        return [a ? a.className : null, i ? i.getAttribute('src') : null, i ? i.naturalWidth > 0 : null]; })""")
    check("metagame: a picture of each deck's main card (first non-land key card), straight from Scryfall's image server",
          arts[0] == ["meta-art", "https://cards.scryfall.io/art_crop/front/d/r/drag-ja.jpg", True] and arts[2][1] == "https://cards.scryfall.io/art_crop/front/b/o/bolt-ja-m10.jpg", arts)
    check("metagame: a missing picture falls back to the same card by name (another printing)", arts[1] == ["meta-art", "https://cards.scryfall.io/art_crop/front/q/p/qp-en.jpg?1700000000", True], arts[1])
    check("metagame: no artist credits under the decks or on the icons", page.locator("#metaBody .meta-illus").count() == 0
          and page.get_attribute("#metaBody .meta-row >> nth=0 >> .meta-art", "title") == "Shivan Dragon" and "Artist of" not in page.locator("#metaBody").inner_text(),
          page.get_attribute("#metaBody .meta-row >> nth=0 >> .meta-art", "title"))
    check("metagame: one Scryfall lookup for all the icons", sum("/cards/collection" in c for c in calls) >= 1)
    check("metagame: a deck without key cards gets an empty frame", arts[3] == ["meta-art empty", None, None], arts[3])
    fit = page.evaluate("""[...document.querySelectorAll('#metaBody .meta-row')].map(r => { const a = r.querySelector('.meta-art').getBoundingClientRect(), d = r.querySelector('.meta-deck').getBoundingClientRect(), b = r.getBoundingClientRect();
        return [Math.round(a.width), Math.round(a.height), a.height <= Math.max(d.height, r.querySelector('.meta-share').getBoundingClientRect().height) + 0.5, a.left > r.querySelector('.meta-rank').getBoundingClientRect().right, a.right < d.left]; })""")
    check("metagame: pictures sit left of the deck name and fit inside the row (rows keep their height)", all(f[0] == 64 and f[1] == 46 and f[2] and f[3] and f[4] for f in fit), fit)
    head = page.evaluate("(() => { const c = document.querySelectorAll('#metaBody .meta-cols > span'); const d = document.querySelector('#metaBody .meta-deck').getBoundingClientRect(); return Math.abs(c[2].getBoundingClientRect().left - d.left) < 2; })()")
    check("metagame: column headings still line up", head)
    if SHOTS: page.locator("#metaBody").screenshot(path="meta_art.png")
    page.select_option("#metaSort", "winrate")
    order = page.locator("#metaBody .meta-name-text").all_inner_texts()
    check("metagame: sort by win rate (decks with too few matches last)", order == ["Selesnya Cats", "Gruul Dragons", "Orzhov (unclassified)", "Mono Red Burn"], order)
    page.select_option("#metaSort", "share")
    page.locator("#metaWindows .seg-btn[data-days='90']").click()
    check("metagame: 90-day period", page.locator("#metaBody .meta-name-text").all_inner_texts() == ["Selesnya Cats", "Gruul Dragons"] and "days=90" in page.url and "1,000 decks" in page.locator("#metaSummary").inner_text(), page.url)
    page.locator("#metaFormats .seg-btn[data-format=modern]").click()
    check("metagame: a format missing from this period says so", "No data for this format" in page.locator("#metaBody").inner_text() and "format=modern" in page.url)
    page.locator("#metaWindows .seg-btn[data-days='30']").click()
    check("metagame: switching format", page.locator("#metaBody .meta-name-text").all_inner_texts() == ["Ragavan Tempo"] and "Too few matches (10)" in page.locator("#metaBody").inner_text())
    page.locator("#metaFormats .seg-btn[data-format=legacy]").click(); page.wait_for_selector("#metaBody .meta-row")
    gm = page.locator("#metaBody .meta-row", has_text="Golgari Midrange").locator(".meta-art")
    check("metagame: the deck's own picture card from the data is used (Ashnod's Altar, not the first key card)",
          gm.get_attribute("data-name") == "Ashnod's Altar" and "Ashnod" in gm.get_attribute("title"), gm.get_attribute("title"))
    icons = page.evaluate("""[deckIconName({ name: 'Broodscale', cards: ["Kozilek's Command", 'Basking Broodscale'] }),
        deckIconName({ name: 'Mono Blue Terror', cards: ['Counterspell', 'Tolarian Terror'] }),
        deckIconName({ name: 'Izzet Delver', cards: ['Brainstorm', 'Delver of Secrets'] }),
        deckIconName({ name: 'Azorius Control', cards: ['Teferi, Time Raveler'] }),
        deckIconName({ name: 'Gruul Dragons', cards: ["Urza's Saga", 'Shivan Dragon'] }),
        deckIconName({ name: 'X', icon: 'Given Card', cards: ['Other'] })]""")
    check("metagame: without a picture card in the data, the card named like the deck (else the first non-land key card)",
          icons == ["Basking Broodscale", "Tolarian Terror", "Delver of Secrets", "Teferi, Time Raveler", "Shivan Dragon", "Given Card"], icons)
    rats = page.locator("#metaBody .meta-row", has_text="Mono Black Rats").locator(".meta-art img")
    page.wait_for_function("(() => { const r = [...document.querySelectorAll('#metaBody .meta-row')].find(x => x.textContent.includes('Mono Black Rats')); const i = r && r.querySelector('.meta-art img'); return i && i.getAttribute('src').includes('rat-en'); })()")
    check("metagame: a main card missing from the database is looked up by name", rats.get_attribute("src") == "https://cards.scryfall.io/art_crop/front/r/a/rat-en.jpg?1700000000", rats.get_attribute("src"))
    page.locator("#metaFormats .seg-btn[data-format=pioneer]").click()
    check("metagame: empty format", "No data for this format" in page.locator("#metaBody").inner_text())
    note = page.locator("#metaNote").inner_text()
    check("metagame: method and sources explained", "mirror matches" in note and "MTGODecklistCache" in note and "Updated 2026-10-06 (events through 2026-10-04)" in note
          and page.locator("#metaNote a").first.get_attribute("href") == "https://github.com/Jiliac/MTGODecklistCache", note)
    page.goto(SITE + "?view=meta&format=standard&days=90"); page.wait_for_selector("#metaBody .meta-row")
    check("metagame: link with format and period opens directly", page.locator("#metaBody .meta-name-text").all_inner_texts() == ["Selesnya Cats", "Gruul Dragons"]
          and page.get_attribute("#metaWindows .seg-btn[data-days='90']", "aria-pressed") == "true")
    page.locator("#metaWindows .seg-btn[data-days='30']").click()
    page.locator("#metaBody a.meta-card", has_text="Shivan Dragon").click(); page.wait_for_selector("#cardView .cp-name")
    check("metagame: key card opens its card page", page.locator(".cp-name").inner_text() == "Shivan Dragon" and "card=drag-ja" in page.url, page.url)
    page.click("#backToSearchBtn"); page.wait_for_selector("#metaBody .meta-row")
    check("metagame: back from the card returns to the metagame tab", "view=meta" in page.url and page.locator("#metaView").is_visible(), page.url)
    # Japanese
    page.click("#langBtn [aria-pressed=false]")
    page.wait_for_function("document.querySelector('#metaFormats .seg-btn .sh-full').textContent === 'スタンダード'")
    r0 = page.locator("#metaBody .meta-row").nth(0).inner_text()
    check("metagame in Japanese: labels and Japanese card names", all(x in r0 for x in ["Gruul Dragons", "100デッキ", "400試合", "シヴ山のドラゴン", "稲妻", "ラノワールのエルフ", "サンプルリスト"])
          and page.locator("#metaWindows .seg-btn").all_inner_texts() == ["直近30日", "直近90日"] and "未分類" in page.locator("#metaBody").inner_text()
          and "12 大会" in page.locator("#metaSummary").inner_text().replace("　", " ") and page.locator("#tabMeta").inner_text() == "メタゲーム", r0)
    check("language back to Japanese is remembered", page.evaluate("localStorage.getItem('akuchie-lang')") == "ja")

    # real data (built from the live tournament archive), for a look at the layout
    META_MODE["mode"] = "real"
    for fmt, shot in (("modern", "meta_modern.png"), ("standard", "meta_standard.png")):
        page.goto(SITE + f"?view=meta&format={fmt}"); page.wait_for_selector("#metaBody .meta-row")
        n = page.locator("#metaBody .meta-row").count()
        check(f"metagame with real data ({fmt}): {n} archetypes, no sideways scroll", 10 <= n <= 40 and no_hscroll())
        if SHOTS: page.screenshot(path=shot, full_page=False)
    page.set_viewport_size({"width": 390, "height": 800})
    page.goto(SITE + "?view=meta&format=modern"); page.wait_for_selector("#metaBody .meta-row")
    check("phone: metagame fits (no sideways scroll)", no_hscroll())
    b = page.locator("#metaBody .meta-row").first.locator(".meta-share").bounding_box(); w = page.locator("#metaBody .meta-row").first.locator(".meta-wr").bounding_box()
    check("phone: share and win rate sit side by side under the deck name", abs(b["y"] - w["y"]) < 3 and b["x"] + b["width"] <= w["x"] + 1, (b, w))
    if SHOTS: page.screenshot(path="meta_phone.png", full_page=False)
    home()
    check("phone: top bar with the language button fits", no_hscroll() and page.locator("#langBtn").is_visible() and page.locator("#tabMeta").is_visible())
    if SHOTS: page.screenshot(path="home_phone.png", full_page=False)
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    check("phone: English top bar fits too", no_hscroll())
    page.click("#langBtn [aria-pressed=false]")
    for wdt in (821, 900, 1000, 1200, 1201, 1280):
        page.set_viewport_size({"width": wdt, "height": 800})
        box = page.locator("#searchInput" if page.locator("#searchInput").is_visible() else "#heroInput").bounding_box()
        check(f"width {wdt}: no sideways scroll, search box usable ({round(box['width'])}px)", no_hscroll() and box["width"] >= 260, box)
    page.set_viewport_size({"width": 1280, "height": 900})
    META_MODE["mode"] = "absent"
    page.goto(SITE + "?view=meta"); page.wait_for_selector("#metaBody .status-line")
    page.wait_for_function("!document.querySelector('#metaBody .spinner')")
    check("metagame: friendly message when meta.json has not been uploaded", "メタゲームデータがまだありません" in page.locator("#metaBody").inner_text())
    META_MODE["mode"] = "fixture"

    # ---- 11. the metagame tab with real data, in English ----
    META_MODE["mode"] = "real"
    page.goto(SITE + "?view=meta&format=legacy"); page.wait_for_selector("#metaBody .meta-row")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    check("metagame tab readable with real data", page.locator("#metaBody .meta-row").count() >= 10 and no_hscroll())
    if SHOTS: page.wait_for_timeout(300); page.screenshot(path="meta_real_en.png", full_page=False)
    page.click("#langBtn [aria-pressed=false]")
    META_MODE["mode"] = "fixture"

    # ---- 12. without the card database (live Scryfall search as the fallback) ----
    DB_MODE["present"] = False
    home()
    check("no database: home page without the effect examples", page.locator("#heroExample").is_hidden() and page.locator("#homeHero").is_visible())
    top_search("e:mh2")
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 2")
    check("no database: live search still works in Japanese", "2 件見つかりました" in count_text().replace(" ", " ") or "2" in count_text(), count_text())
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    check("no database: language switch keeps the results", page.locator("#cardGrid .card-tile").count() == 2 and "cards found" in count_text(), count_text())
    page.click("#tabMeta"); page.wait_for_selector("#metaBody .meta-row")
    check("no database: metagame tab still lists decks (English card names)", "Shivan Dragon" in page.locator("#metaBody").inner_text() and page.locator("#metaBody a.meta-card").count() == 0)
    page.click("#langBtn [aria-pressed=false]")
    DB_MODE["present"] = True

    # =====================================================================
    # ---- 14. pictures: real scans instead of placeholders, sharper sizes ----
    page.set_viewport_size({"width": 1280, "height": 900})
    page.evaluate("localStorage.clear()")
    home()
    def src_of(cid):
        name = {"bolt-ja-m10": "稲妻", "drag-ja": "シヴ山のドラゴン", "rag-ja-mh2": "ラガバン"}[cid]
        top_search(name)
        page.wait_for_function(f"document.querySelector(\"#cardGrid .card-tile[data-id='{cid}'] img\")")
        page.wait_for_timeout(250)
        return page.locator(f"#cardGrid .card-tile[data-id='{cid}'] img").get_attribute("src")
    check("pictures: Japanese placeholder replaced by the English printing's scan", "/normal/bolt-en-m10" in src_of("bolt-ja-m10"), src_of("bolt-ja-m10"))
    check("pictures: a low-resolution Japanese scan is still shown (Japanese first)", "/normal/drag-ja" in src_of("drag-ja"), src_of("drag-ja"))
    check("pictures: a good Japanese scan stays Japanese", "/normal/rag-ja-mh2" in src_of("rag-ja-mh2"), src_of("rag-ja-mh2"))
    tile_img = page.locator("#cardGrid .card-tile[data-id='rag-ja-mh2'] img")
    srcset = tile_img.get_attribute("srcset") or ""
    check("pictures: tiles offer small, normal and large sizes", all(f"/{k}/rag-ja-mh2.jpg {w}w" in srcset for k, w in (("small", 146), ("normal", 488), ("large", 672))) and tile_img.get_attribute("sizes"), srcset)
    page.goto(SITE + "?card=bolt-ja-m10"); page.wait_for_selector("#cardView .print-item")
    page.wait_for_function("document.querySelector('.cp-art img') && document.querySelector('.cp-art img').src.includes('bolt-en')")
    art = page.locator(".cp-art img")
    check("card page: placeholder replaced, large picture, note says why", "/large/bolt-en-m10" in art.get_attribute("src") and "/large/bolt-en-m10.jpg 672w" in (art.get_attribute("srcset") or "")
          and "日本語版の画像がScryfallにないため" in page.locator(".cp-img-note").inner_text(), (art.get_attribute("src"), page.locator(".cp-img-note").all_inner_texts()))
    thumbs = page.locator("#versionMenuPanel .print-item img")
    check("printings: thumbnails use the bigger picture (sharp on high-density screens), English scan for the placeholder",
          all("/normal/" in thumbs.nth(i).get_attribute("src") for i in range(thumbs.count())) and "/normal/bolt-en-m10" in thumbs.first.get_attribute("src"),
          [thumbs.nth(i).get_attribute("src") for i in range(thumbs.count())])
    page.goto(SITE + "?card=drag-ja"); page.wait_for_selector("#cardView .print-item")
    page.wait_for_timeout(400)
    check("card page: the low-resolution Japanese picture, no note", "/large/drag-ja" in page.locator(".cp-art img").first.get_attribute("src") and page.locator(".cp-img-note").count() == 0,
          page.locator(".cp-art img").first.get_attribute("src"))
    page.goto(SITE + "?card=rag-ja-mh2"); page.wait_for_selector("#cardView .print-item")
    page.wait_for_timeout(300)
    check("card page: a good Japanese scan stays, no note", "/large/rag-ja-mh2" in page.locator(".cp-art img").first.get_attribute("src") and page.locator(".cp-img-note").count() == 0)
    page.goto(SITE + "?set=m10&lang=ja"); page.wait_for_selector("#setGrid .card-tile img")
    check("set page: Japanese placeholder shows the English scan", "bolt-en-m10" in page.locator("#setGrid .card-tile[data-id='bolt-ja-m10'] img").get_attribute("src"))
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    page.goto(SITE + "?card=bolt-ja-m10"); page.wait_for_function("document.querySelector('.cp-art img') && document.querySelector('.cp-art img').src.includes('bolt-en')")
    check("card page note in English", "no picture of the Japanese printing" in page.locator(".cp-img-note").inner_text(), page.locator(".cp-img-note").inner_text())
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'ja'")
    if SHOTS: page.goto(SITE + "?card=bolt-ja-m10"); page.wait_for_selector(".cp-img-note"); page.screenshot(path="card_placeholder.png", full_page=False)

    # ---- 15. search: words that belong together ----
    DB_MODE["search"] = True
    home()
    def search(q):
        top_search(q)
        page.wait_for_function("!document.querySelector('#cardGrid .spinner') && document.querySelector('#resultCount').textContent.trim() !== ''")
        page.wait_for_timeout(100)
        return page.locator("#cardGrid .card-name-main").all_inner_texts()
    names = search("sacrifice 2 permanants")
    note = page.locator("#matchNote").inner_text()
    check("search: 'sacrifice 2 permanants' finds only the cards that do it (equal matches in あいうえお order)", names == ["高価な祭壇", "滅殺の獣", "対の供物"], names)
    check("search: misspelling corrected and said so", "「permanants」は「permanents」として検索しました" in note, note)
    check("search: count and toggle for the loose matches", "3 件見つかりました" in count_text().replace("\u00a0", " ")
          and page.locator("#looseToggle").inner_text() == "語句がバラバラに含まれるだけのカードも表示（+1件）", (count_text(), note))
    check("search: no group headings when every card is in one group", page.locator("#cardGrid .tier-divider").count() == 0)
    page.click("#looseToggle")
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 4")
    heads = page.locator("#cardGrid .tier-divider").all_inner_texts()
    check("search: loose matches added below their own heading", page.locator("#cardGrid .card-name-main").all_inner_texts()[-1] == "散らばった思考"
          and heads == ["語句がまとまって一致", "語句がバラバラに含まれるカード"] and page.locator("#looseToggle").inner_text() == "まとまって出てくるカードだけに戻す", heads)
    if SHOTS: page.screenshot(path="search_loose.png", full_page=False)
    page.click("#looseToggle")
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 3")
    check("search: and hidden again", page.locator("#cardGrid .tier-divider").count() == 0)
    page.click("#looseToggle"); page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 4")
    names = search("sacrifice two permanents")
    check("search: a new search starts with the loose matches hidden; 'two' = '2'", names == ["高価な祭壇", "滅殺の獣", "対の供物"] and "permanants" not in page.locator("#matchNote").inner_text(), names)
    check("search: o:\"…\" phrase with plural/number forms", search('o:"sacrifice two permanents"') == ["高価な祭壇", "滅殺の獣"])
    names = search("elf mana")
    check("search: short searches - type line or name counts for the whole card, in a second group", names == ["マナのエルフ", "木立のエルフ"]
          and page.locator("#cardGrid .tier-divider").all_inner_texts() == ["語句がまとまって一致", "カードのタイプ・名前と組み合わせて一致"], (names, page.locator("#cardGrid .tier-divider").all_inner_texts()))
    if SHOTS: page.screenshot(path="search_groups.png", full_page=False)
    check("search: keyword abilities count wherever they are", search("flying lifelink") == ["空の癒し手"])
    check("search: 'discard a card' is not 'discard two cards'", search("discard a card") == ["物色テスト"] and "+1件" in page.locator("#looseToggle").inner_text())
    check("search: 'draw two cards' is not '…two permanents: draw a card'", search("draw two cards") == ["散らばった思考", "入念な研究テスト"])
    names = search("2つのパーマネントを生け贄")
    check("search (Japanese): word order and particles may differ", names == ["高価な祭壇", "対の供物", "滅殺の獣"] and "+1件" in page.locator("#looseToggle").inner_text(), names)
    check("search (Japanese): full-width numbers and 生贄 spelling", search("パーマネント２つを生贄") == ["高価な祭壇", "対の供物", "滅殺の獣"])
    check("search (Japanese): 1枚捨てる finds カードを１枚捨てる only", search("1枚捨てる") == ["物色テスト"])
    check("search (Japanese): separate words in one ability", search("生け贄 パーマネント") == ["高価な祭壇", "対の供物", "滅殺の獣"])
    check("search (Japanese): keywords on different lines", search("飛行 絆魂") == ["空の癒し手"])
    names = search("permanants")
    check("search: one misspelt word is corrected too", "永続の盾" in names and len(names) == 5 and "permanents" in page.locator("#matchNote").inner_text(), names)
    strike, fly = search("strike"), search("fly")
    check("search: single words still find longer words containing them", strike == ["先制の兵"] and sorted(fly) == sorted(["空の癒し手", "シヴ山のドラゴン", "English Only Thing"]), (strike, fly))
    # load more keeps headings right across pages
    split = page.evaluate("""() => { state.query = 'sacrifice 2 permanents'; state.showLoose = true; const rows = localSearchAndFilter();
        const cards = rows.map(rowToCard); const first = resultTilesHtml(cards.slice(0, 3), rows.slice(0, 3), null);
        const second = resultTilesHtml(cards.slice(3), rows.slice(3), rows[2]); const again = resultTilesHtml(cards.slice(3), rows.slice(3), rows[3]);
        state.showLoose = false; return [first.split('tier-divider').length - 1, second.split('tier-divider').length - 1, again.split('tier-divider').length - 1]; }""")
    check("search: 'load more' adds a heading only where a new group starts", split == [1, 1, 0], split)
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    names = search("sacrifice 2 permanants")
    note = page.locator("#matchNote").inner_text()
    check("search in English: note and toggle", names == ["Annihilator Beast", "Costly Altar", "Paired Offering"] and 'Searched for “permanents” instead of “permanants”.' in note
          and page.locator("#looseToggle").inner_text() == "Also show cards that only contain the words separately (+1)", note)
    search("elf mana")
    check("search in English: group headings", page.locator("#cardGrid .tier-divider").all_inner_texts() == ["Words together", "Matching together with the card’s type or name"])
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'ja'")
    check("search: switching language keeps the headings", page.locator("#cardGrid .tier-divider").all_inner_texts() == ["語句がまとまって一致", "カードのタイプ・名前と組み合わせて一致"])
    page.set_viewport_size({"width": 390, "height": 800})
    search("sacrifice 2 permanants")
    check("phone: search note fits", no_hscroll() and page.locator("#looseToggle").is_visible())
    page.set_viewport_size({"width": 1280, "height": 900})
    DB_MODE["search"] = False


    # ---- 16. price history and price movers ----
    PRICE_SITE["dir"] = PRICES_FULL
    page.goto(SITE + "?card=rag-en-mh2"); page.wait_for_selector("#priceHistory svg .hist-line")
    page.wait_for_function("document.querySelector('#cardViewCard .shop-prices') && document.querySelector('#cardViewCard .shop-prices').textContent.includes('Cardsphere')")
    end = page.locator("#priceHistory .hist-end").text_content()
    check("price history: chart on the card page, ending at today's price in yen", page.locator("#priceHistory").is_visible() and end == "¥6,150", end)
    chg = page.locator("#priceHistory .hist-change").inner_text()
    check("price history: 3 months by default, with the change over the range", page.locator('#priceHistory .seg-btn[data-range="90"]').get_attribute("aria-pressed") == "true"
          and chg == "3か月で +36.7%", chg)
    check("price history: a day without a price leaves a gap in the line", page.locator("#priceHistory .hist-line").count() == 2)
    check("price history: no 'just started' note once a month of data exists", "始めたばかり" not in page.locator("#priceHistory").inner_text())
    page.locator("#priceHistory svg").scroll_into_view_if_needed()
    box = page.locator("#priceHistory svg").bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.3, box["y"] + box["height"] / 2)
    tip = page.locator("#priceHistory .hist-tip")
    check("price history: hovering shows the date and price", tip.is_visible() and "¥" in tip.inner_text() and "2026/" in tip.inner_text() and "$" in tip.inner_text(), tip.inner_text())
    page.mouse.move(5, 5)
    check("price history: and hides it again", not tip.is_visible())
    page.focus("#priceHistory svg"); page.keyboard.press("End")
    last = tip.inner_text()
    page.keyboard.press("ArrowLeft")
    check("price history: keyboard moves between dates", tip.is_visible() and "2026/10/9" in last and "2026/10/8" in tip.inner_text(), [last, tip.inner_text()])
    if SHOTS: page.locator("#priceHistory").screenshot(path="hist_card.png")
    page.click('#histFoil')
    check("price history: foil prices", page.locator("#priceHistory .hist-end").text_content() == "¥9,150")
    page.click('#histFoil')
    page.click('#priceHistory .seg-btn[data-range="30"]')
    chg30 = page.locator("#priceHistory .hist-change").inner_text()
    check("price history: 1-month range", chg30.startswith("1か月で +") and chg30 != chg, chg30)
    page.click("#priceHistory .hist-table summary")
    n_rows = page.locator("#priceHistory .hist-table tbody tr").count()
    check("price history: table view lists every day of the range that has a price", n_rows == 30 and page.locator("#priceHistory .hist-table tbody tr").first.inner_text().split("\t")[1] == "¥6,150", n_rows)
    page.click('#priceHistory .seg-btn[data-range="90"]')
    page.goto(SITE + "?card=rag-ja-mh2"); page.wait_for_selector("#priceHistory svg .hist-line")
    check("price history: Japanese printing shows its English twin's history", page.locator("#priceHistory .hist-end").text_content() == "¥6,150")
    page.goto(SITE + "?card=drag-en"); page.wait_for_function("document.getElementById('priceHistory') && !document.getElementById('priceHistory').hidden")
    check("price history: printing without history says so", "まだありません" in page.locator("#priceHistory").inner_text())
    page.goto(SITE + "?card=eo-1"); page.wait_for_selector(".cp-name"); page.wait_for_timeout(600)
    check("price history: nothing shown when its data file is missing", page.locator("#priceHistory").is_hidden())
    page.goto(SITE + "?card=rag-en-mh2"); page.wait_for_selector("#priceHistory svg .hist-line")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_selector("#priceHistory svg .hist-line")
    check("price history in English", page.locator("#priceHistory .hist-title").inner_text().replace("\n", " ").startswith("Price history") and "US market" in page.locator("#priceHistory .hist-title").inner_text()
          and page.locator("#priceHistory .hist-change").inner_text() == "+36.7% over 3M", page.locator("#priceHistory .hist-title").inner_text())
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'ja'")
    page.set_viewport_size({"width": 390, "height": 800}); page.wait_for_timeout(400)
    sw = page.evaluate("document.querySelector('#priceHistory svg').getBoundingClientRect().width")
    check("phone: chart fits the screen", no_hscroll() and sw <= 360, sw)
    if SHOTS: page.locator("#priceHistory").screenshot(path="hist_phone.png")
    page.set_viewport_size({"width": 1280, "height": 900})


    # ---- 16b. card page: prices by market (日本 / 米国 / 欧州) ----
    def shop_rows():
        return page.evaluate("""[...document.querySelectorAll('#cardViewCard .shop-prices .sp-shop')].map(s => {
            const a = s.nextElementSibling, b = a.nextElementSibling;
            const label = [...s.childNodes].map(n => n.textContent.replace('↗', '').trim()).filter(Boolean).join(' ');
            const v = x => x.querySelector('strong') ? (x.querySelector('.cur[title]') || x.querySelector('strong')).title || x.querySelector('strong').textContent : '—';   // the shop's own price
            return [label, v(a), v(b)];
        })""")
    def wait_market(m):
        page.wait_for_function(f"document.querySelector('#cardViewCard .price-section') && document.querySelector('#cardViewCard .price-section').dataset.market === '{m}'")
    psec = page.locator("#cardViewCard .price-section")
    page.goto(SITE + "?card=rag-en-mh2")
    page.wait_for_function("document.querySelector('#cardViewCard .shop-prices') && document.querySelector('#cardViewCard .shop-prices').textContent.includes('Card Kingdom')")
    check("card prices: 日本 / 米国 / 欧州 tabs, 米国 chosen at first",
          psec.locator(".price-tabs .seg-btn").all_inner_texts() == ["日本", "米国", "欧州"]
          and psec.locator('.seg-btn[data-pmarket="us"]').get_attribute("aria-selected") == "true", psec.locator(".price-tabs").inner_text())
    rows = shop_rows()
    check("card prices: US - selling prices (TCGplayer's lowest listing instead of its market price), then Card Kingdom's buying price",
          rows == [["TCGplayer 最安出品", "$37.50", "$55.00"], ["Card Kingdom 販売", "$44.99", "$69.99"], ["Cardsphere", "$39.50", "—"], ["Card Kingdom 買取", "$30.00", "$45.00"]], rows)
    best = page.evaluate("[...document.querySelectorAll('#cardViewCard .sp-val.best strong .cur')].map(s => s.title)")
    check("card prices: the cheapest selling price in each column is marked (not the buying price)", best == ["$37.50", "$55.00"]
          and psec.locator(".best-tag").all_inner_texts() == ["最安", "最安"], best)
    check("card prices: no market price shown when selling prices are known", "相場" not in psec.locator(".shop-prices").inner_text() and "¥6,000" not in psec.locator(".shop-prices").inner_text())
    ptxt = psec.inner_text()
    check("card prices: each dollar price shown in yen", "¥5,625" in ptxt and "¥8,250" in ptxt and "¥4,500" in ptxt and "¥5,925" in ptxt and "$37.50" not in ptxt, ptxt)
    check("card prices: column headings", psec.locator(".sp-h").all_inner_texts() == ["ショップ", "通常", "フォイル"], psec.locator(".sp-h").all_inner_texts())
    plink = lambda label: psec.locator(".sp-shop a", has_text=label).get_attribute("href")
    check("card prices: shop names link to the shop's search",
          plink("TCGplayer") == "https://www.tcgplayer.com/search/magic/product?productLineName=magic&q=" + Q("Ragavan, Nimble Pilferer", safe="")
          and plink("Card Kingdom") == "https://www.cardkingdom.com/catalog/search?search=header&filter%5Bname%5D=" + Q("Ragavan, Nimble Pilferer", safe="")
          and psec.locator(".sp-shop a").count() == 2, [plink("TCGplayer"), plink("Card Kingdom")])
    sub = psec.locator(".price-sub").inner_text()
    notes = page.locator("#priceNotes").inner_text()
    check("card prices: both exchange rates stay under the prices; where the prices come from (and the date) is in the notes at the bottom",
          "1ドル＝150.00円" in sub and "1ユーロ＝160.00円" in sub and "TCGCSV" not in sub and "MTGJSON" not in sub
          and "TCGCSV" in notes and "MTGJSON" in notes and "2026/10/9" in notes and "状態を問わない" in notes, (sub, notes))
    page.wait_for_function("document.querySelector('#priceAvg').textContent.includes('平均')")
    check("card prices: US tab keeps the average across printings", "¥6,800" in page.locator("#priceAvg").inner_text())
    check("card prices: no Japanese shop prices copied", not any(x in ptxt for x in ["晴れる屋", "BIG MAGIC", "カードラッシュ"]))
    # Europe
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="eu"]'); wait_market("eu")
    rows = shop_rows()
    ptxt = psec.inner_text()
    check("card prices: Europe - Cardmarket's lowest offer in euros, with yen at the euro rate",
          rows == [["Cardmarket 最安出品", "€31.90", "€48.00"]] and "¥5,104" in ptxt and "¥7,680" in ptxt and "€35.00" not in ptxt, (rows, ptxt))
    check("card prices: Europe - Cardmarket link, average left out",
          plink("Cardmarket") == "https://www.cardmarket.com/en/Magic/Products/Search?searchString=" + Q("Ragavan, Nimble Pilferer", safe="")
          and page.locator("#priceAvg").inner_text().strip() == "", page.locator("#priceAvg").inner_text())
    ntxt = page.locator("#priceNotes").inner_text()
    check("card prices: Europe - the note (at the bottom) names Cardmarket's price guide and says any condition or language", "価格ガイド" in ntxt and "言語を問わない" in ntxt and "2026/10/9" in ntxt, ntxt)
    page.wait_for_function("document.querySelector('#priceHistory .hist-end') && document.querySelector('#priceHistory .hist-end').textContent === '¥5,888'")
    check("card prices: the chart follows the tab (Cardmarket euros at ¥160)", "欧州市場" in page.locator("#priceHistory .hist-title").inner_text()
          and "Cardmarket" in page.locator("#priceHistory .hist-note").inner_text(), page.locator("#priceHistory .hist-title").inner_text())
    page.locator("#priceHistory svg").scroll_into_view_if_needed()
    box = page.locator("#priceHistory svg").bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.6, box["y"] + box["height"] / 2)
    check("card prices: chart tooltip in euros", "€" in page.locator("#priceHistory .hist-tip").inner_text() and "$" not in page.locator("#priceHistory .hist-tip").inner_text(), page.locator("#priceHistory .hist-tip").inner_text())
    page.mouse.move(5, 5)
    page.click('#histFoil')
    check("card prices: euro foil history", page.locator("#priceHistory .hist-end").text_content() == "¥8,608", page.locator("#priceHistory .hist-end").text_content())
    page.click('#histFoil')
    page.click("#priceHistory .hist-table summary")
    check("card prices: chart table in euros", "EUR" in page.locator("#priceHistory .hist-table thead").inner_text()
          and "€36.80" in page.locator("#priceHistory .hist-table tbody tr").first.inner_text(), page.locator("#priceHistory .hist-table tbody tr").first.inner_text())
    check("card prices: the choice is remembered", page.evaluate("localStorage.getItem('akuchie-market')") == "eu")
    if SHOTS: page.locator("#cardViewCard .price-section").screenshot(path="price_eu.png")
    page.reload(); wait_market("eu")
    page.wait_for_selector("#priceHistory svg .hist-line")
    page.wait_for_function("document.querySelector('#cardViewCard .shop-prices') && document.querySelector('#cardViewCard .shop-prices').textContent.includes('¥5,104')")
    check("card prices: still Europe after reloading", shop_rows()[0][1] == "€31.90" and page.locator("#priceHistory .hist-end").text_content() == "¥5,888")
    page.goto(SITE + "?card=rag-ja-mh2"); wait_market("eu")
    page.wait_for_function("document.querySelector('#cardViewCard .shop-prices') && document.querySelector('#cardViewCard .shop-prices').textContent.includes('¥5,104')")
    check("card prices: Japanese printing shows its English twin's lowest offer", shop_rows() == [["Cardmarket 最安出品", "€31.90", "€48.00"]], shop_rows())
    page.goto(SITE + "?card=rag-en-mul"); wait_market("eu")
    page.wait_for_function("document.querySelector('#cardViewCard .shop-prices') && document.querySelector('#cardViewCard .shop-prices').textContent.includes('¥6,080')")
    check("card prices: no lowest offer known -> the trend price (here MTGJSON's), dated", shop_rows() == [["Cardmarket トレンド", "€38.00", "—"]]
          and "MTGJSON" in page.locator("#priceNotes").inner_text() and "2026/10/9" in page.locator("#priceNotes").inner_text(), (shop_rows(), page.locator("#priceNotes").inner_text()))
    page.goto(SITE + "?card=bolt-en-m10"); wait_market("eu"); page.wait_for_timeout(500)
    check("card prices: no euro price at all -> says so", "この版の価格情報はありません" in psec.inner_text() and psec.locator(".shop-prices").count() == 0, psec.inner_text())
    # Japan: work in progress
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="jp"]'); wait_market("jp")
    check("card prices: Japan tab - one notice for prices and listings, nothing else", psec.locator(".jp-notice .wip-badge").inner_text() == "準備中"
          and "掲載の許可をいただいたショップから順に" in psec.inner_text() and psec.locator(".jp-dir-note").count() == 0 and page.locator("#offersBox").is_hidden() and psec.locator(".shop-prices").count() == 0 and psec.locator(".price-sub").count() == 0, psec.inner_text())
    page.goto(SITE + "?card=rag-en-mh2"); wait_market("jp")
    page.wait_for_function("document.getElementById('priceHistory') && !document.getElementById('priceHistory').hidden && document.querySelector('#priceHistory .hist-note')")
    check("card prices: Japan tab - the chart says Japanese history is on the way", "日本の価格の推移は準備中" in page.locator("#priceHistory").inner_text()
          and page.locator("#priceHistory svg").count() == 0, page.locator("#priceHistory").inner_text())
    if SHOTS: page.locator("#cardViewCard .price-section").screenshot(path="price_jp.png")
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="us"]'); wait_market("us")
    page.wait_for_selector("#priceHistory svg .hist-line")
    check("card prices: back to US, chart in dollars again", page.locator("#priceHistory .hist-end").text_content() == "¥6,150" and shop_rows()[0][1] == "$37.50")
    page.wait_for_function("document.querySelector('#cardViewCard .shop-prices').textContent.includes('Cardsphere')")
    if SHOTS: page.locator("#cardViewCard .price-section").screenshot(path="price_us.png")
    page.goto(SITE + "?card=saga-en"); wait_market("us")
    page.wait_for_function("document.querySelector('#cardViewCard .shop-prices') && document.querySelector('#cardViewCard .shop-prices').textContent.includes('Card Kingdom')")
    check("card prices: only the shops that have the card", shop_rows() == [["TCGplayer 最安出品", "$28.00", "—"], ["Card Kingdom 販売", "$32.99", "—"]], shop_rows())
    page.goto(SITE + "?card=drag-en"); wait_market("us"); page.wait_for_timeout(500)
    check("card prices: no selling price known -> TCGplayer's market price instead, no MTGJSON note", shop_rows() == [["TCGplayer 相場", "$0.50", "—"]]
          and "MTGJSON" not in page.locator("#priceNotes").inner_text(), (shop_rows(), page.locator("#priceNotes").inner_text()))
    page.goto(SITE + "?card=rag-en-mh2"); page.wait_for_function("document.querySelector('#cardViewCard .shop-prices') && document.querySelector('#cardViewCard .shop-prices').textContent.includes('Cardsphere')")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    page.wait_for_function("document.querySelector('#cardViewCard .shop-prices') && document.querySelector('#cardViewCard .shop-prices').textContent.includes('Cardsphere')")
    check("card prices in English", psec.locator(".price-tabs .seg-btn").all_inner_texts() == ["Japan", "US", "Europe"]
          and shop_rows() == [["TCGplayer lowest listing", "$37.50", "$55.00"], ["Card Kingdom selling", "$44.99", "$69.99"], ["Cardsphere", "$39.50", "—"], ["Card Kingdom buying", "$30.00", "$45.00"]]
          and psec.locator(".sp-h").all_inner_texts() == ["Shop", "Non-foil", "Foil"] and "€1 = ¥160.00" in psec.inner_text(), (shop_rows(), psec.inner_text()))
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="jp"]'); wait_market("jp")
    check("card prices in English: Japan - coming soon, as shops give permission", "Coming soon" in psec.inner_text() and "permission" in psec.inner_text(), psec.inner_text())
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="us"]'); wait_market("us")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'ja'")
    page.set_viewport_size({"width": 390, "height": 800}); page.wait_for_timeout(300)
    page.wait_for_function("document.querySelector('#cardViewCard .shop-prices') && document.querySelector('#cardViewCard .shop-prices').textContent.includes('Cardsphere')")
    sp = page.locator("#cardViewCard .shop-prices").bounding_box()
    check("phone: shop price table fits", no_hscroll() and sp["width"] <= 370, sp)
    if SHOTS: page.locator("#cardViewCard .price-section").screenshot(path="price_phone.png")
    page.set_viewport_size({"width": 1280, "height": 900})

    page.click("#tabPrices"); page.wait_for_selector("#moverBody .mover-row")
    col_names = lambda d: [x.split("\n")[0] for x in page.locator(f'#moverBody .mover-col[data-dir="{d}"] .mover-name').all_inner_texts()]
    check("price movers: tab opens on the US market, 7 days", "view=prices&market=us&win=7" in page.url
          and page.locator("#moverMarkets .seg-btn").all_inner_texts() == ["日本", "米国", "欧州"]
          and page.get_attribute('#moverMarkets .seg-btn[data-market="us"]', "aria-selected") == "true", page.url)
    check("price movers: winners and losers side by side",
          [re.sub(r"\s", "", x) for x in page.locator("#moverBody .mover-col-head").all_inner_texts()] == ["▲値上がり", "▼値下がり"]
          and col_names("up") == ["クァーサルの群れ魔道士", "Deathrite Shaman", "敏捷なこそ泥、ラガバン"] and col_names("down") == ["ウルザの物語"],
          [page.locator("#moverBody .mover-col-head").all_inner_texts(), col_names("up"), col_names("down")])
    up_box = page.locator('#moverBody .mover-col[data-dir="up"]').bounding_box(); down_box = page.locator('#moverBody .mover-col[data-dir="down"]').bounding_box()
    check("price movers: two columns on a wide screen", abs(up_box["y"] - down_box["y"]) < 2 and down_box["x"] > up_box["x"] + up_box["width"] - 1, (up_box, down_box))
    first = page.locator('#moverBody .mover-col[data-dir="up"] .mover-row').first.inner_text()
    check("price movers: change, dollars first and yen beside", "+13.0%" in first and "¥966 → ¥1,092" in first and "$6.44" not in first, first)
    lose = page.locator('#moverBody .mover-col[data-dir="down"] .mover-row').first.inner_text()
    check("price movers: losers show the fall", "−5.7%" in lose and "¥4,613 → ¥4,350" in lose, lose)
    check("price movers: all three periods offered", page.locator("#moverWindows .seg-btn").all_inner_texts() == ["前日比", "1週間", "1か月"])
    check("price movers: summary counts both lists", "（4枚）" in page.locator("#moverSummary").inner_text(), page.locator("#moverSummary").inner_text())
    page.click('#moverWindows .seg-btn[data-win="1"]')
    check("price movers: a period where nothing moved says so in each column", page.locator("#moverBody .mover-col .hb-empty").count() == 2 and "win=1" in page.url)
    page.click('#moverWindows .seg-btn[data-win="30"]')
    check("price movers: 30 days", "−20.5%" in page.locator('#moverBody .mover-col[data-dir="down"] .mover-chg').first.inner_text()
          and "win=30" in page.url and "2026/9/9 → 2026/10/9" in page.locator("#moverSummary").inner_text(), page.locator("#moverSummary").inner_text())
    if SHOTS: page.screenshot(path="prices_tab.png")
    # Europe
    page.click('#moverMarkets .seg-btn[data-market="eu"]')
    page.wait_for_function("document.querySelector('#moverBody .mover-row') && location.search.includes('market=eu') && document.querySelector('#moverBody .cur[data-from=eur]')")
    check("price movers: European market - its own winners and losers", "market=eu" in page.url and "win=30" in page.url
          and col_names("up") == ["ウルザの物語", "敏捷なこそ泥、ラガバン"] and col_names("down") == ["Deathrite Shaman"], [page.url, col_names("up"), col_names("down")])
    page.click('#moverWindows .seg-btn[data-win="7"]')
    first = page.locator('#moverBody .mover-col[data-dir="up"] .mover-row').first.inner_text()
    check("price movers: euros first, yen at the euro rate", "+5.1%" in first and "¥6,576 → ¥6,912" in first and "€41.10" not in first and "$" not in first, first)
    lose = page.locator('#moverBody .mover-col[data-dir="down"] .mover-row').first.inner_text()
    check("price movers: European losers", "−16.3%" in lose and "¥1,032 → ¥864" in lose, lose)
    check("price movers: note names Cardmarket for Europe", "Cardmarket" in page.locator("#moverNote").inner_text() and "€2" in page.locator("#moverNote").inner_text())
    if SHOTS: page.screenshot(path="prices_eu.png")
    # Japan
    page.click('#moverMarkets .seg-btn[data-market="jp"]')
    check("price movers: Japan - work in progress", "market=jp" in page.url and page.locator("#moverBody .wip-badge").inner_text() == "準備中"
          and "日本のショップ価格は準備中" in page.locator("#moverBody").inner_text() and page.locator("#moverWindows .seg-btn").count() == 0
          and page.locator("#moverBody .mover-row").count() == 0, page.locator("#moverBody").inner_text())
    if SHOTS: page.screenshot(path="prices_jp.png")
    page.reload(); page.wait_for_selector("#moverBody .wip-badge")
    check("price movers: the market is kept in the address", page.get_attribute('#moverMarkets .seg-btn[data-market="jp"]', "aria-selected") == "true")
    page.goto(SITE + "?view=prices&win=7&dir=down"); page.wait_for_selector("#moverBody .mover-row")
    check("price movers: old links (dir=down) still open, on the US market", page.get_attribute('#moverMarkets .seg-btn[data-market="us"]', "aria-selected") == "true"
          and col_names("down") == ["ウルザの物語"])
    page.locator('#moverBody .mover-col[data-dir="up"] a.mover-card').first.click(); page.wait_for_selector("#priceHistory svg .hist-line")
    check("price movers: a row opens the card page", "card=qp-en" in page.url)
    page.go_back(); page.wait_for_selector("#moverBody .mover-row")
    check("price movers: back returns to the list", "view=prices" in page.url and page.locator("#tabPrices").get_attribute("aria-selected") == "true")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    check("price movers in English", page.locator("#moverMarkets .seg-btn").all_inner_texts() == ["Japan", "US", "Europe"] and page.title() == "Price movers — 悪知恵"
          and [re.sub(r"\s", "", x) for x in page.locator("#moverBody .mover-col-head").all_inner_texts()] == ["▲Winners", "▼Losers"]
          and "Qasali Pridemage" in page.locator("#moverBody").inner_text() and "TCGplayer" in page.locator("#moverNote").inner_text(), page.locator("#moverBody .mover-col-head").all_inner_texts())
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'ja'")
    page.set_viewport_size({"width": 390, "height": 800}); page.wait_for_timeout(300)
    up_box = page.locator('#moverBody .mover-col[data-dir="up"]').bounding_box(); down_box = page.locator('#moverBody .mover-col[data-dir="down"]').bounding_box()
    check("phone: price movers fit, losers below winners", no_hscroll() and page.locator("#tabPrices").is_visible() and down_box["y"] > up_box["y"] + up_box["height"] - 1, (up_box, down_box))
    for w in (390, 360):
        page.set_viewport_size({"width": w, "height": 800}); page.wait_for_timeout(200)
        ob = page.locator("#pricesView .imp-open").bounding_box(); bar = page.locator("#pricesView .meta-bar").bounding_box(); up = page.locator('#moverBody .mover-col[data-dir="up"]').bounding_box()
        check(f"phone {w}px: the deck price button sits between the bar and the winners, full width and thin", no_hscroll() and ob["y"] >= bar["y"] + bar["height"] and ob["y"] + ob["height"] <= up["y"]
              and abs(ob["x"] - bar["x"]) < 1 and abs(ob["width"] - bar["width"]) < 1 and ob["height"] <= 52, (ob, bar, up))
    if SHOTS: page.screenshot(path="prices_phone.png", full_page=True)
    page.set_viewport_size({"width": 1280, "height": 900})
    PRICE_SITE["dir"] = PRICES_NOEU
    page.goto(SITE + "?view=prices&market=eu"); page.wait_for_selector("#moverBody .status-line .serif")
    check("price movers: data from before the euro prices -> Europe says when they appear", "次回の価格更新から" in page.locator("#moverBody").inner_text(), page.locator("#moverBody").inner_text())
    PRICE_SITE["dir"] = PRICES_FULL
    PRICE_SITE["dir"] = PRICES_ONE
    page.goto(SITE + "?view=prices"); page.wait_for_selector("#moverBody .status-line .serif")
    check("price movers: first day -> 'just started' message", "始めたばかり" in page.locator("#moverBody").inner_text())
    page.goto(SITE + "?card=rag-en-mh2"); page.wait_for_function("document.getElementById('priceHistory') && !document.getElementById('priceHistory').hidden")
    check("price history: first day -> today's price and 'just started' note", "1日分" in page.locator("#priceHistory").inner_text() and "¥6,150" in page.locator("#priceHistory").inner_text())
    PRICE_SITE["dir"] = None
    page.goto(SITE + "?view=prices"); page.wait_for_selector("#moverBody .status-line .serif")
    check("price movers: no data published yet -> friendly message", "価格データがまだありません" in page.locator("#moverBody").inner_text())
    page.goto(SITE + "?card=rag-en-mh2"); page.wait_for_selector(".cp-name"); page.wait_for_timeout(600)
    check("price history: hidden when no data is published", page.locator("#priceHistory").is_hidden())


    # ---- 17. the new layout: suggestions, hero example, home boxes, text view, scrolling, formats, preview page ----
    page.set_viewport_size({"width": 1280, "height": 900})
    page.evaluate("localStorage.clear()")
    PRICE_SITE["dir"] = PRICES_FULL
    home()
    check("home: logo text, centred WARUJIE under 悪知恵, new subtitle and title",
          page.locator(".brand-mark").inner_text() == "悪知恵" and page.locator(".brand-roman").inner_text() == "WARUJIE"
          and abs(page.evaluate("(() => { const a = document.querySelector('.brand-mark').getBoundingClientRect(), b = document.querySelector('.brand-roman').getBoundingClientRect(); return (a.left + a.width / 2) - (b.left + b.width / 2); })()")) < 1.5
          and "効果テキスト" in page.locator("#brandSub").inner_text() and page.title().startswith("悪知恵（warujie）"), page.title())
    check("home: top-bar search hidden (the big box is the search box)", not page.locator("#searchInput").is_visible() and page.locator("#heroInput").is_visible())
    # name suggestions
    page.locator("#heroInput").press_sequentially("ラガ")
    page.wait_for_selector("#heroSuggest .suggest-item")
    sug = page.locator("#heroSuggest .suggest-item")
    check("suggestions: card names as you type, typed part in bold", sug.count() == 1 and "敏捷なこそ泥、ラガバン" in sug.first.inner_text() and sug.first.locator("b").first.inner_text() == "ラガ"
          and page.get_attribute("#heroInput", "aria-expanded") == "true", sug.all_inner_texts())
    page.fill("#heroInput", ""); page.locator("#heroInput").press_sequentially("らが")
    page.wait_for_selector("#heroSuggest .suggest-item")
    check("suggestions: hiragana typed before conversion finds the katakana name", "ラガバン" in page.locator("#heroSuggest").inner_text())
    page.fill("#heroInput", ""); page.locator("#heroInput").press_sequentially("light")
    page.wait_for_function("document.getElementById('heroSuggest').textContent.includes('Lightning')")
    check("suggestions: English names too", "稲妻" in page.locator("#heroSuggest").inner_text() and "Lightning Bolt" in page.locator("#heroSuggest").inner_text(), page.locator("#heroSuggest").inner_text())
    page.fill("#heroInput", ""); page.locator("#heroInput").press_sequentially("o:damage")
    page.wait_for_timeout(250)
    check("suggestions: none for search syntax / rules text", not page.locator("#heroSuggest").is_visible())
    page.fill("#heroInput", ""); page.locator("#heroInput").press_sequentially("シヴ")
    page.wait_for_selector("#heroSuggest .suggest-item")
    page.press("#heroInput", "ArrowDown")
    check("suggestions: arrow keys move through the list", page.get_attribute("#heroSuggest .suggest-item", "aria-selected") == "true"
          and page.get_attribute("#heroInput", "aria-activedescendant") == "heroSuggest-0")
    colours = page.evaluate("""(() => { const cs = el => getComputedStyle(el); const root = cs(document.documentElement);
        const items = [...document.querySelectorAll('#heroSuggest .suggest-item')];
        return { sel: cs(items[0]).backgroundColor, surface2: root.getPropertyValue('--surface-2').trim(), others: items.slice(1).map(i => cs(i).backgroundColor),
                 btn: cs(document.querySelector('.hero-row > button')).backgroundColor, accent: root.getPropertyValue('--accent').trim() }; })()""")
    check("suggestions: the picked row is the theme's grey, the rest plain (not the accent colour)", colours["sel"] == "rgb(34, 34, 38)" and colours["surface2"] == "#222226"
          and all(c == "rgba(0, 0, 0, 0)" for c in colours["others"]), colours)
    check("accent: retro lime green (the search button too)", colours["accent"] == "#b5e655" and colours["btn"] == "rgb(181, 230, 85)", colours)
    if SHOTS: page.locator("#heroForm").screenshot(path="suggest_dark.png")
    page.press("#heroInput", "Enter"); page.wait_for_selector("#cardView .cp-name")
    check("suggestions: Enter on a suggestion opens that card", "card=drag-ja" in page.url and page.locator(".cp-name").inner_text() == "シヴ山のドラゴン", page.url)
    page.fill("#searchInput", ""); page.locator("#searchInput").press_sequentially("ラノ")
    page.wait_for_function("document.getElementById('searchSuggest').textContent.includes('ラノワール')")
    page.locator("#searchSuggest .suggest-item").first.click(); page.wait_for_function("document.querySelector('.cp-name') && document.querySelector('.cp-name').textContent === 'ラノワールのエルフ'")
    check("suggestions: the top-bar box suggests too (on other pages), click opens the card", "card=elf-ja" in page.url)
    page.fill("#searchInput", ""); page.locator("#searchInput").press_sequentially("ラノ")
    page.wait_for_function("document.getElementById('searchSuggest').textContent.includes('ラノワール')")
    page.press("#searchInput", "Escape")
    check("suggestions: Escape closes the list", not page.locator("#searchSuggest").is_visible())
    page.press("#searchInput", "Enter")
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました')")
    check("suggestions: Enter without picking one is a normal search", page.locator("#cardGrid .card-name-main").all_inner_texts() == ["ラノワールのエルフ"]
          and page.locator(".res-q").inner_text() == "「ラノ」：", page.locator(".res-q").all_inner_texts())
    # card page: compact rows, link-only shops incl. Card Rush, mana symbols in the text
    page.goto(SITE + "?card=elf-ja"); page.wait_for_selector("#cardView .print-item")
    check("card page: rules text shows mana symbols", [i.get_attribute("alt") for i in page.locator(".cp-text img.sym").all()] == ["{T}", "{G}"]
          and [i.get_attribute("alt") for i in page.locator(".cp-cost img.pip").all()] == ["{G}"], page.locator(".cp-text").inner_html())
    sl = page.locator("#cardViewCard .shop-links")
    row = page.evaluate("[...document.querySelectorAll('#cardViewCard .shop-links a.external-link-btn')].map(a => a.textContent.replace('↗', '').trim())")
    above = page.evaluate("[...document.querySelectorAll('#cardViewCard .sp-shop a, #offersBox .of-shop a')].map(a => a.textContent.replace('↗', '').trim())")
    check("card page: 「ショップで探す」 lists only this market's shops that the prices above don't link to (no Japanese shops: they are in the 日本 tab)",
          "Star City Games" in row and set(row) <= {"TCGplayer", "Card Kingdom", "Star City Games"} and not set(row) & set(above)
          and page.locator("#cardViewCard .shop-links .sg-label").count() == 0, (row, above))
    clink = lambda label: page.locator("#cardViewCard a", has_text=label).first.get_attribute("href")
    check("card page: shop link addresses (Japanese name for Card Rush, English for the US)",
          href("カードラッシュ") == "https://www.cardrush-mtg.jp/product-list?keyword=" + Q("ラノワールのエルフ")
          and clink("Card Kingdom") == "https://www.cardkingdom.com/catalog/search?search=header&filter%5Bname%5D=Llanowar%20Elves"
          and clink("Star City Games") == "https://starcitygames.com/search/?search_query=Llanowar%20Elves"
          and clink("TCGplayer") == "https://www.tcgplayer.com/search/magic/product?productLineName=magic&q=Llanowar%20Elves",
          [a.get_attribute("href") for a in sl.locator("a").all()])
    check("card page: no magi link", "magi" not in sl.inner_text().lower().replace("magic", "") and page.locator("#cardViewCard a[href*='magi.camp'], #cardViewCard a[href*='magi.']").count() == 0)
    fs = page.evaluate("[parseFloat(getComputedStyle(document.querySelector('#cardViewCard .shop-links a.external-link-btn')).fontSize), document.querySelector('#cardViewCard .shop-links a.external-link-btn').getBoundingClientRect().height, parseFloat(getComputedStyle(document.querySelector('#cardViewCard .cp-row:not(.shop-links) a.external-link-btn')).fontSize)]")
    check("card page: shop links are smaller than the other link buttons", fs[0] < fs[2] and fs[1] <= 24, fs)
    check("card page: no shop prices are copied onto the page", "晴れる屋" not in page.locator("#cardViewCard .price-section").inner_text())
    page.set_viewport_size({"width": 390, "height": 800}); page.wait_for_timeout(200)
    check("phone: shop link groups fit (the row scrolls sideways inside itself)", no_hscroll(), page.evaluate("document.documentElement.scrollWidth"))
    if SHOTS: sl.screenshot(path="shop_links_phone.png")
    page.set_viewport_size({"width": 1280, "height": 900}); page.wait_for_timeout(200)
    if SHOTS: sl.screenshot(path="shop_links.png")
    lg = page.locator("#cardViewCard .cp-row.cp-wrap")
    up_front = page.evaluate("[...document.querySelectorAll('#cardViewCard .cp-row.cp-wrap .legal-row')].filter(r => !r.closest('details')).map(r => r.querySelector('.legal-name').textContent)")
    check("card page: formats as one compact row (no second heading)", up_front == ["スタンダード", "モダン", "レガシー", "ヴィンテージ"] and not lg.locator(".legal-heading").is_visible(), (up_front, lg.inner_html()[:300]))
    check("card page: price history sits below the details", page.locator(".card-lower #priceHistory").count() == 1)
    # hero example + home boxes
    DB_MODE["search"] = True
    home()
    page.wait_for_selector("#hxList .hx-entry")
    check("effect examples: no search bar in the box, three different effects with a card each",
          page.locator("#heroExample .hx-query").count() == 0 and page.locator("#hxList .hx-entry").count() == 3
          and len(set(page.locator("#hxList .hx-effect").all_inner_texts())) == 3 and page.locator("#hxList a.hx-item").count() == 3
          and len(set(a.get_attribute("data-card") for a in page.locator("#hxList a.hx-item").all())) == 3, page.locator("#hxList").inner_text())
    check("effect examples: all effects come from the list of keywords and game actions",
          page.evaluate("[...document.querySelectorAll('#hxList .hx-effect')].every(b => HERO_EFFECTS.some(f => f[0] === b.textContent.trim()))"))
    # a fixed set, to check what each entry shows
    page.evaluate("""HERO_EFFECTS.splice(0, HERO_EFFECTS.length, ['手札をすべて捨てる', '', 'Discard your hand', 'discard your hand'],
        ['カードを1枚捨てる', '', 'Discard a card', 'discard a card'], ['飛行', '', 'Flying', 'flying'], ['宝物・トークンを生成する', '宝物・トークン1つを生成する', 'Create a treasure token', 'create a treasure token'],
        ['ゲームに勝利する', '', 'Win the game', 'win the game'])""")
    page.evaluate("heroFx.entries = []; renderHeroExample(1)")
    page.wait_for_function("document.querySelectorAll('#hxList .hx-entry').length === 3 && document.querySelector('#hxList img.sym, #hxList .hx-thumb img')")
    labels = page.locator("#hxList .hx-effect").all_inner_texts()
    check("effect examples: only effects that have cards (no card discards its hand or wins here)", sorted(labels) == sorted(["カードを1枚捨てる", "飛行", "宝物・トークンを生成する"]), labels)
    entry = page.locator("#hxList .hx-entry", has_text="カードを1枚捨てる")
    check("effect examples: the card's text with the effect marked", "物色テスト" in entry.locator(".hx-name").inner_text()
          and "１枚捨てる" in "".join(entry.locator("mark.hl").all_inner_texts()).replace("1", "１"), entry.inner_text())
    page.wait_for_function("document.querySelector('#hxList .hx-thumb img')")
    sym = page.evaluate("""(() => { const t = document.querySelector('#hxList .hx-text'); t.insertAdjacentHTML('beforeend', symbolize(esc('{1}{B}{B}')));
        const s = t.querySelector('img.sym'); return s ? [s.getBoundingClientRect().width, s.getBoundingClientRect().height, parseFloat(getComputedStyle(t).fontSize)] : null; })()""")
    check("effect examples: mana symbols at the size of the text", sym and sym[0] <= sym[2] * 1.2 and sym[1] <= sym[2] * 1.2, sym)
    thumb = page.locator("#hxList .hx-thumb img").first.bounding_box()
    check("effect examples: card pictures stay small", 30 <= thumb["width"] <= 50, thumb)
    before = page.locator("#hxList .hx-effect").all_inner_texts()
    page.evaluate("""HERO_EFFECTS.push(['先制攻撃', '', 'First strike', 'first strike'], ['絆魂', '', 'Lifelink', 'lifelink'], ['カードを1枚引く', '', 'Draw a card', 'draw a card'])""")
    page.click("#hxNext")
    page.wait_for_function(f"JSON.stringify([...document.querySelectorAll('#hxList .hx-effect')].map(b => b.textContent.trim())) !== {json.dumps(json.dumps(before, ensure_ascii=False, separators=(',', ':')))}")
    after = page.locator("#hxList .hx-effect").all_inner_texts()
    check("effect examples: 'another' shows other effects", not set(after) & set(before), (before, after))
    page.locator("#hxList .hx-effect").first.click()
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました')")
    check("effect examples: clicking an effect searches for it", page.input_value("#searchInput") == after[0] and not page.locator("#homeHero").is_visible(), (page.input_value("#searchInput"), after[0]))
    home()
    page.wait_for_selector("#hxList a.hx-item")
    cid = page.locator("#hxList a.hx-item").first.get_attribute("data-card")
    page.locator("#hxList a.hx-item").first.click(); page.wait_for_selector("#cardView", state="visible")
    check("effect examples: clicking a card opens it", f"card={cid}" in page.url, page.url)
    page.goto(SITE); page.wait_for_selector("#homeMoversBody .hb-row")
    hb_names = lambda d: page.locator(f'#homeMoversBody .hb-part[data-dir="{d}"] .hb-name').all_inner_texts()
    check("home: price box tabs 日本 / 米国 / 欧州 (the card page's order), US chosen", page.locator("#homeMoversTabs .seg-btn").all_inner_texts() == ["日本", "米国", "欧州"]
          and page.get_attribute("#homeMoversTabs .seg-btn[data-market=us]", "aria-selected") == "true", page.locator("#homeMoversTabs").inner_text())
    first_row = page.locator('#homeMoversBody .hb-part[data-dir="up"] .hb-row').first.inner_text()
    check("home: US - 7-day winners and losers in dollars, Japanese names",
          hb_names("up") == ["クァーサルの群れ魔道士", "Deathrite Shaman", "敏捷なこそ泥、ラガバン"] and hb_names("down") == ["ウルザの物語"]
          and [re.sub(r"\s", "", x) for x in page.locator("#homeMoversBody .hb-part-head").all_inner_texts()] == ["▲値上がり", "▼値下がり"]
          and "+13.0%" in first_row and "¥966 → ¥1,092" in first_row and "TCGplayer" in page.locator("#homeMoversBody .hb-src").inner_text(), (hb_names("up"), hb_names("down"), first_row))
    check("home: losers show the fall", "−5.7%" in page.locator('#homeMoversBody .hb-part[data-dir="down"] .hb-row').first.inner_text())
    check("home: 'see all' goes to the US market", page.get_attribute("#homeMoversMore", "href") == "?view=prices&market=us&win=7")
    page.click("#homeMoversTabs .seg-btn[data-market=eu]")
    page.wait_for_function("document.querySelector('#homeMoversBody .hb-src') && document.querySelector('#homeMoversBody .hb-src').textContent.includes('Cardmarket')")
    eu_row = page.locator('#homeMoversBody .hb-part[data-dir="up"] .hb-row').first.inner_text()
    check("home: Europe tab - winners and losers in euros", hb_names("up") == ["ウルザの物語", "敏捷なこそ泥、ラガバン"] and hb_names("down") == ["Deathrite Shaman"]
          and "¥6,576 → ¥6,912" in eu_row and "+5.1%" in eu_row and page.get_attribute("#homeMoversMore", "href") == "?view=prices&market=eu&win=7", (hb_names("up"), eu_row))
    if SHOTS: page.locator("#homeMovers").screenshot(path="home_box_eu.png")
    page.click("#homeMoversMore"); page.wait_for_selector("#moverBody .mover-row")
    check("home: 'see all' from Europe opens the European list", "market=eu" in page.url and page.get_attribute('#moverMarkets .seg-btn[data-market="eu"]', "aria-selected") == "true")
    page.go_back(); page.wait_for_selector("#homeMoversBody .hb-row")
    page.click("#homeMoversTabs .seg-btn[data-market=jp]")
    check("home: Japan tab - work in progress", page.locator("#homeMoversBody .wip-badge").inner_text() == "準備中" and "日本のショップ価格は準備中" in page.locator("#homeMoversBody").inner_text()
          and page.get_attribute("#homeMoversTabs .seg-btn[data-market=jp]", "aria-selected") == "true" and not page.locator("#homeMoversMore").is_visible())
    if SHOTS: page.locator("#homeMovers").screenshot(path="home_box_jp.png")
    page.click("#homeMoversTabs .seg-btn[data-market=us]"); page.wait_for_selector("#homeMoversBody .hb-row")
    if SHOTS: page.locator("#homeMovers").screenshot(path="home_box_us.png")
    PRICE_SITE["dir"] = PRICES_NOEU
    page.goto(SITE); page.wait_for_selector("#homeMoversBody .hb-row")
    page.click("#homeMoversTabs .seg-btn[data-market=eu]"); page.wait_for_function("document.getElementById('homeMoversBody').textContent.includes('次回の価格更新から')")
    check("home: Europe before the euro prices are published -> says when they appear", True)
    PRICE_SITE["dir"] = PRICES_FULL
    page.goto(SITE); page.wait_for_selector("#homeMoversBody .hb-row")
    page.wait_for_selector("#homeMetaBody .hb-row")
    page.wait_for_function("document.querySelector('#homeMetaBody .hb-art img') && document.querySelector('#homeMetaBody .hb-art img').getAttribute('src').includes('drag-ja')")
    hb_art = page.evaluate("[...document.querySelectorAll('#homeMetaBody .hb-row')].map(r => { const a = r.querySelector('.hb-art'); const i = a && a.querySelector('img'); const b = a && a.getBoundingClientRect(); return [a ? a.dataset.name : null, i ? i.getAttribute('src') : null, b ? Math.round(b.width) : 0, b ? Math.round(b.height) : 0]; })")
    check("home: top decks show each deck's picture too", hb_art[0] == ["Shivan Dragon", "https://cards.scryfall.io/art_crop/front/d/r/drag-ja.jpg", 44, 32]
          and hb_art[1][0] == "Qasali Pridemage" and len(hb_art) == 3, hb_art)
    check("home: no artist credits under the top decks", page.locator("#homeMetaBody .hb-illus").count() == 0 and "Artist of" not in page.locator("#homeMetaBody").inner_text())
    rh = page.evaluate("[...document.querySelectorAll('#homeMetaBody .hb-row')].map(r => Math.round(r.getBoundingClientRect().height))")
    check("home: rows keep their height with the pictures", all(h <= 60 for h in rh), rh)
    if SHOTS: page.locator("#homeMeta").screenshot(path="home_meta_icons.png")
    check("home: top decks with format tabs", page.locator("#homeMetaTabs .seg-btn").all_inner_texts() == ["スタンダード", "パイオニア", "モダン", "レガシー"]
          and page.locator("#homeMetaBody .hb-name").all_inner_texts()[:2] == ["グルール・ドラゴン", "Selesnya Cats"], page.locator("#homeMetaBody").inner_text())
    page.locator("#homeMetaTabs .seg-btn[data-format=legacy]").click()
    page.wait_for_function("document.querySelector('#homeMetaBody .hb-name') && document.querySelector('#homeMetaBody .hb-name').textContent === 'イゼット・デルバー'")
    check("home: switching the deck tab", page.get_attribute("#homeMetaTabs .seg-btn[data-format=legacy]", "aria-pressed") == "true" and page.locator("#homeMetaBody .hb-row").count() == 5)
    page.locator("#homeMetaTabs .seg-btn[data-format=pioneer]").click()
    page.wait_for_function("!document.querySelector('#homeMetaBody .hb-row')")
    check("home: a format without data says so", "まだありません" in page.locator("#homeMetaBody").inner_text())
    page.locator("#homeMetaTabs .seg-btn[data-format=legacy]").click(); page.wait_for_selector("#homeMetaBody .hb-row")
    page.click("#homeMetaMore"); page.wait_for_selector("#metaBody .meta-row")
    check("home: 'open metagame' goes to the chosen format", "format=legacy" in page.url and page.locator("#metaBody .meta-name-text").first.inner_text() == "イゼット・デルバー", page.url)
    page.go_back(); page.wait_for_selector("#homeMoversBody .hb-row")
    page.locator("#homeMoversBody .hb-name").first.click(); page.wait_for_selector("#cardView .cp-name")
    check("home: a mover opens its card", "card=qp-en" in page.url)
    if SHOTS:
        page.goto(SITE); page.wait_for_selector("#homeMoversBody .hb-row"); page.wait_for_selector("#hxList .hx-item"); page.wait_for_timeout(400)
        page.screenshot(path="v7_home.png", full_page=False)
        page.screenshot(path="v7_home_full.png", full_page=True)
    # text view
    home()
    top_search("2つのパーマネントを生け贄")
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました')")
    check("results: picture view by default, with a view switch", page.get_attribute("#viewToggle .view-btn[data-view=image]", "aria-selected") == "true" and page.locator("#cardGrid .card-tile").count() == 3)
    page.click("#viewToggle .view-btn[data-view=text]")
    page.wait_for_selector("#cardGrid .text-row")
    marks = page.locator("#cardGrid .text-row").first.locator("mark.hl").all_inner_texts()
    check("text view: one row per card with its rules text, the matching words marked", page.locator("#cardGrid .text-row").count() == 3 and page.locator("#cardGrid .card-tile").count() == 0
          and any("パーマネント" in m for m in marks) and any("生け贄" in m for m in marks), marks)
    if SHOTS: page.screenshot(path="v7_text_view.png", full_page=False)
    page.locator("#cardGrid .text-row").first.click(); page.wait_for_selector("#cardView .cp-name")
    check("text view: a row opens the card", "card=" in page.url)
    page.go_back(); page.wait_for_selector("#cardGrid .text-row")
    page.reload(); page.wait_for_selector("#homeHero", state="visible"); page.wait_for_function("dbState !== 'loading'")
    top_search("2つのパーマネントを生け贄"); page.wait_for_selector("#cardGrid .text-row")
    check("text view: choice remembered after reload (home page still shows pictures)", page.evaluate("localStorage.getItem('akuchie-view')") == "text" and page.locator("#cardGrid .text-row").count() == 3)
    top_search("sacrifice two permanents"); page.wait_for_selector("#cardGrid .text-row")
    check("text view: English search marks the English text", any("sacrifice" in m.lower() for m in page.locator("#cardGrid mark.hl").all_inner_texts()), page.locator("#cardGrid mark.hl").all_inner_texts())
    page.click("#viewToggle .view-btn[data-view=image]"); page.wait_for_selector("#cardGrid .card-tile")
    DB_MODE["search"] = False
    # infinite scroll
    DB_MODE["variant"] = "many"
    home()
    top_search("テスト用の熊")
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 30")
    page.mouse.wheel(0, 20000)
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 60", timeout=8000)
    page.mouse.wheel(0, 40000)
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 70", timeout=8000)
    check("results: more cards load by themselves while scrolling (30 → 60 → 70)", page.locator("#cardGrid .card-tile").count() == 70 and not page.locator("#loadMoreBtn").is_visible())
    # format filter (needs the legality field in the database)
    DB_MODE["variant"] = "legal"
    home()
    open_adv()
    check("format filter: enabled when the database has legality data", not page.locator("#formatSelect").is_disabled()
          and page.locator("#formatSelect option").all_inner_texts()[:5] == ["指定なし", "スタンダード", "パイオニア", "モダン", "レガシー"], page.locator("#formatSelect option").all_inner_texts())
    page.select_option("#formatSelect", "modern")
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました')")
    check("format filter: only cards legal in Modern", sorted(page.locator("#cardGrid .card-name-main").all_inner_texts()) == sorted(["敏捷なこそ泥、ラガバン", "稲妻", "ウルザの物語"])
          and page.locator("#activeFilters .filter-pill").all_inner_texts() == ["モダンで使用可×"], (page.locator("#cardGrid .card-name-main").all_inner_texts(), page.locator("#activeFilters .filter-pill").all_inner_texts()))
    page.locator("#activeFilters .filter-pill").click()
    page.wait_for_selector("#homeHero", state="visible")
    check("format filter: pill removes it", page.input_value("#formatSelect") == "")
    # rarity: a card counts under every rarity it was printed at, as on Scryfall
    names_on = lambda: sorted(page.locator("#cardGrid .card-name-main").all_inner_texts())
    DB_MODE["variant"] = "rar"
    home()
    open_adv()
    page.locator(".opt-chip[data-group=rarity][data-value=mythic]").click()
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました')")
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile .card-foot').length === 2")
    # each tile: (label, dot class, tooltip, arrow class or "")
    feet = lambda: {t.locator(".card-name-main").inner_text(): (t.locator(".rarity-dot").inner_text().strip(), t.locator(".rarity-dot .dot").get_attribute("class"),
            t.locator(".rarity-dot").get_attribute("title") or "", t.locator(".shift-icon").get_attribute("class") if t.locator(".shift-icon").count() else "")
            for t in page.locator("#cardGrid .card-tile").all()}
    check("rarity filter: 神話レア finds cards with any mythic printing (Shivan Dragon has one)", names_on() == sorted(["敏捷なこそ泥、ラガバン", "シヴ山のドラゴン"]), names_on())
    f = feet()
    check("rarity filter: a tile whose printing is another rarity still says 神話レア, with a ↓ arrow in the picture's rarity colour and the picture's rarity as tooltip",
          f.get("シヴ山のドラゴン", ("",))[0] == "神話レア" and "mythic" in f["シヴ山のドラゴン"][1] and "この絵はレアの版です" in f["シヴ山のドラゴン"][2]
          and f["シヴ山のドラゴン"][3] == "shift-icon down rare"
          and f.get("敏捷なこそ泥、ラガバン", ("",))[0] == "神話レア" and not f["敏捷なこそ泥、ラガバン"][2] and not f["敏捷なこそ泥、ラガバン"][3], f)
    # several rarities at once: any of them
    page.locator(".opt-chip[data-group=rarity][data-value=rare]").click()
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile .card-foot').length === 4")
    f = feet()
    check("rarity filter: R and M together find cards with a rare or a mythic printing", names_on() == sorted(["敏捷なこそ泥、ラガバン", "シヴ山のドラゴン", "ウルザの物語", "ラノワールのエルフ"]), names_on())
    check("rarity filter: both buttons stay on, one pill each, in rarity order",
          page.locator(".opt-chip[data-group=rarity][aria-pressed=true]").evaluate_all("bs => bs.map(b => b.dataset.value)") == ["rare", "mythic"]
          and page.locator("#activeFilters .filter-pill").all_inner_texts() == ["レア×", "神話レア×"], page.locator("#activeFilters .filter-pill").all_inner_texts())
    check("rarity filter: with R and M, Shivan Dragon (a rare picture) is plain レア; Llanowar Elves (a common picture) says レア with the arrow",
          f["シヴ山のドラゴン"][0] == "レア" and not f["シヴ山のドラゴン"][3] and f["ラノワールのエルフ"][0] == "レア"
          and f["ラノワールのエルフ"][3] == "shift-icon down common" and f["ウルザの物語"][0] == "レア" and not f["ウルザの物語"][3], f)
    page.locator(".opt-chip[data-group=rarity][data-value=common]").click()
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile .card-foot').length === 6")
    check("rarity filter: adding C finds the commons too", len(names_on()) == 6 and "稲妻" in names_on(), names_on())
    page.locator(".opt-chip[data-group=rarity][data-value=rare]").click()
    page.locator(".opt-chip[data-group=rarity][data-value=common]").click()
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile .card-foot').length === 2")
    check("rarity filter: turning R and C off again leaves the mythics", names_on() == sorted(["敏捷なこそ泥、ラガバン", "シヴ山のドラゴン"]), names_on())
    page.locator("#activeFilters .filter-pill").click()
    page.wait_for_selector("#homeHero", state="visible")
    for q, want in (("r:m", ["敏捷なこそ泥、ラガバン", "シヴ山のドラゴン"]), ("r:rare", ["ウルザの物語", "シヴ山のドラゴン", "ラノワールのエルフ"]),
                    ("神話レア ドラゴン", ["シヴ山のドラゴン"]), ("r:u", ["クァーサルの群れ魔道士", "稲妻"]), ("-r:c", ["ウルザの物語", "クァーサルの群れ魔道士", "シヴ山のドラゴン", "敏捷なこそ泥、ラガバン"])):
        top_search(q)
        page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました')")
        page.wait_for_function(f"document.querySelectorAll('#cardGrid .card-tile').length === {len(want)}")
        check(f"rarity: {q} counts every printing's rarity", names_on() == sorted(want), names_on())
    top_search("r:rare")
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile .card-foot').length === 3")
    check("rarity: r:rare says レア on every tile and marks only the one whose picture isn't rare (Llanowar Elves, ↓)",
          page.locator("#cardGrid .rarity-dot").all_inner_texts() == ["レア"] * 3 and page.locator("#cardGrid .shift-icon").count() == 1
          and page.locator("#cardGrid .card-tile", has_text="ラノワールのエルフ").locator(".shift-icon.down.common").count() == 1,
          page.locator("#cardGrid .rarity-dot").all_inner_texts())
    DB_MODE["variant"] = None
    home()
    top_search("r:m")
    page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 1")
    check("rarity: a database without the rarities field still filters by the shown printing's rarity", names_on() == ["敏捷なこそ泥、ラガバン"], names_on())
    # the preview page
    home(SITE + "preview.html"); page.wait_for_selector("#hxList a.hx-item")
    check("preview.html: same site, kept out of search engines", page.locator("meta[name=robots]").get_attribute("content") == "noindex" and page.locator("#homeHero").is_visible())
    page.locator("#hxList a.hx-item").first.click(); page.wait_for_selector("#cardView .cp-name")
    check("preview.html: card links stay on the preview page", "/Warujie/preview.html?card=" in page.url, page.url)
    page.click("#brandLink"); page.wait_for_selector("#homeHero", state="visible")
    check("preview.html: the logo returns to the preview home page", page.url.endswith("/Warujie/preview.html"), page.url)
    # English home
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    page.wait_for_function("document.querySelector('#homeMetaTabs .seg-btn').textContent === 'Standard'")
    page.wait_for_function("document.querySelector('#hxList .hx-effect') && !/[ぁ-んァ-ヶ一-龥]/.test([...document.querySelectorAll('#hxList .hx-effect')].map(b => b.textContent).join(''))")
    check("English home: hero, example and boxes in English", page.locator(".hero-title").inner_text() == "Find cards by what they say." and page.locator("#advToggle").inner_text().startswith("Advanced search")
          and page.locator("#homeMoversTitle").inner_text().startswith("Price movers") and not JP.search(" ".join(page.locator("#hxList .hx-effect").all_inner_texts())), page.locator("#hxList .hx-effect").all_inner_texts())
    if SHOTS: page.wait_for_timeout(300); page.screenshot(path="v7_home_en.png", full_page=False)
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'ja'")
    # phones
    page.set_viewport_size({"width": 390, "height": 800})
    page.goto(SITE); page.wait_for_selector("#homeMoversBody .hb-row")
    check("phone: new home page fits", no_hscroll())
    if SHOTS: page.wait_for_timeout(300); page.screenshot(path="v7_home_phone.png", full_page=False); page.screenshot(path="v7_home_phone_full.png", full_page=True)
    page.locator("#heroInput").press_sequentially("ラガ"); page.wait_for_selector("#heroSuggest .suggest-item")
    sb = page.locator("#heroSuggest").bounding_box()
    check("phone: suggestions fit the screen", sb["x"] >= 0 and sb["x"] + sb["width"] <= 390 and no_hscroll(), sb)
    page.press("#heroInput", "Escape")
    top_search("飛行")
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました')")
    check("phone: results fit", no_hscroll())
    if SHOTS: page.screenshot(path="v7_results_phone.png", full_page=False)
    page.click("#viewToggle .view-btn[data-view=text]"); page.wait_for_selector("#cardGrid .text-row")
    check("phone: text view fits", no_hscroll())
    if SHOTS: page.screenshot(path="v7_text_phone.png", full_page=False)
    page.click("#viewToggle .view-btn[data-view=image]")
    n0 = len(calls)
    page.goto(SITE + "?card=rag-ja-mh2"); page.wait_for_selector("#cardView .print-item"); page.wait_for_timeout(300)
    check("a card page opened directly does not download the home page's data", not any(x in c for c in calls[n0:] for x in ("meta.json", "movers.json")), [c for c in calls[n0:] if "json" in c])
    if SHOTS: page.wait_for_timeout(300); page.screenshot(path="v7_card_phone.png", full_page=False); page.screenshot(path="v7_card_phone_full.png", full_page=True)
    page.set_viewport_size({"width": 1280, "height": 900})
    if SHOTS:
        page.goto(SITE + "?card=rag-ja-mh2"); page.wait_for_selector("#priceHistory svg .hist-line"); page.wait_for_timeout(300)
        page.screenshot(path="v7_card.png", full_page=False); page.screenshot(path="v7_card_full.png", full_page=True)
        home(); page.click("#advToggle"); page.focus("#creatureTypeFilter"); page.locator("#creatureTypeFilter").press_sequentially("エ"); page.wait_for_timeout(200)
        page.screenshot(path="v7_adv.png", full_page=False)
        page.evaluate("setTheme('light', true)"); page.goto(SITE); page.wait_for_selector("#homeMoversBody .hb-row"); page.wait_for_timeout(300)
        page.screenshot(path="v7_home_light.png", full_page=False)
        page.evaluate("setTheme('dark', true)")
    PRICE_SITE["dir"] = None


    # ---- 18. round 2: Japanese type lines and pictures, deck pages, logo, following search box, sidebar ----
    page.set_viewport_size({"width": 1280, "height": 900})
    home(); page.evaluate("localStorage.clear()")
    tl = page.evaluate("""[translateTypeLine('Legendary Creature — Human Artificer'), translateTypeLine('Artifact Creature — Golem'),
        translateTypeLine('Basic Snow Land — Forest'), translateTypeLine('Kindred Instant — Elf'), translateTypeLine('Enchantment — Aura // Sorcery'),
        translateTypeLine('Legendary Planeswalker — Jace')]""")
    check("type lines: English put into Japanese when Scryfall has no Japanese one", tl == ["伝説のクリーチャー — 人間・工匠", "アーティファクト・クリーチャー — ゴーレム",
          "基本氷雪土地 — 森", "同族インスタント — エルフ", "エンチャント — オーラ // ソーサリー", "伝説のプレインズウォーカー — Jace"], tl)
    DB_MODE["variant"] = "abj"
    home()
    top_search("拒絶")
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました') && document.querySelector('#cardGrid .card-tile img')")
    tile = page.locator("#cardGrid .card-tile").first
    page.wait_for_function("document.querySelector('#cardGrid .card-tile img').src.includes('abj-en')")
    check("a Japanese card Scryfall has no Japanese type line or picture for: type line in Japanese, English picture",
          "インスタント" in tile.inner_text() and "Instant" not in tile.inner_text() and "/normal/abj-en" in tile.locator("img").get_attribute("src"), tile.inner_text())
    tile.click(); page.wait_for_selector("#cardView .cp-name")
    page.wait_for_function("document.querySelector('.cp-art img') && document.querySelector('.cp-art img').src.includes('abj-en')")
    check("…and on its card page, with the note why the picture is English", "インスタント" in page.locator(".cp-typeline").inner_text()
          and "日本語版の画像がScryfallにないため" in page.locator(".cp-img-note").inner_text(), page.locator(".cp-typeline").inner_text())
    DB_MODE["variant"] = None

    # deck pages
    ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin="https://warujie.github.io")
    DECKS_MODE["mode"] = "fixture"
    page.goto(SITE + "?view=meta&format=standard"); page.wait_for_selector("#metaBody .meta-row")
    first = page.locator("#metaBody .meta-row").first
    check("metagame: each deck name links to the deck's own page", first.locator("a.meta-name-text").get_attribute("href") == "?view=deck&format=standard&days=30&deck=Gruul%20Dragons"
          and first.locator("a.meta-decklink").count() == 0, first.locator("a.meta-name-text").get_attribute("href"))   # no second "deck list" link beside it
    first.locator("a.meta-name-text").click()
    page.wait_for_selector("#deckBody .deck-group")
    check("deck page: own address, title, metagame tab selected", "view=deck" in page.url and "deck=Gruul%20Dragons" in page.url
          and page.title() == "グルール・ドラゴン（スタンダード）のデッキリスト — 悪知恵" and page.get_attribute("#tabMeta", "aria-selected") == "true", (page.url, page.title()))
    chosen = lambda: page.evaluate("document.querySelector('#deckListSel').selectedOptions[0].textContent")
    head = page.locator(".deck-head").inner_text() + chosen()
    check("deck page: format, period, share, win rate and where the list comes from", all(x in head for x in ["スタンダード・直近30日", "使用率 25.0%（100デッキ）", "勝率 55.0%（400試合）", "1st Place・Big Open（2026-10-03）"])
          and page.locator(".deck-pick-bar a.deck-src-link").get_attribute("href") == "https://melee.gg/Decklist/View/abc" and page.locator(".deck-src").count() == 0, head)   # the picker names the list; its page is the 出典 link beside it
    page.wait_for_function("document.querySelectorAll('#deckBody .deck-section')[0].querySelectorAll('.deck-card img').length >= 6")
    groups = page.evaluate("[...document.querySelectorAll('#deckBody .deck-section')[0].querySelectorAll('.dg-head')].map(h => [h.firstChild.textContent, h.querySelector('.dg-n') ? h.querySelector('.dg-n').textContent : ''])")
    check("deck page: main deck grouped by card type, with card counts", groups == [["クリーチャー", "12"], ["インスタント", "4"], ["土地", "42"], ["その他", "2"]], groups)
    check("deck page: total of the main deck", page.locator("#deckBody .deck-section").first.locator("h2").inner_text().replace("\n", "") == "メインデッキ60枚",
          page.locator("#deckBody .deck-section").first.locator("h2").inner_text())
    names = page.evaluate("[...document.querySelectorAll('#deckBody .deck-section')[0].querySelectorAll('.deck-card')].map(c => [c.querySelector('.dc-name').textContent, (c.querySelector('.dc-count') || {}).textContent || ''])")
    check("deck page: Japanese names, sorted by mana value within a type, lands by count", names == [["ラノワールのエルフ", "×4"], ["敏捷なこそ泥、ラガバン", "×4"], ["シヴ山のドラゴン", "×4"],
          ["稲妻", "×4"], ["Mountain", "×20"], ["Forest", "×18"], ["ウルザの物語", "×4"], ["Unknown New Card", "×2"]], names)
    cards = page.locator("#deckBody .deck-section").first.locator(".deck-card")
    check("deck page: pictures (Japanese printings), share of lists playing each card", "/normal/elf-ja" in cards.nth(0).locator("img").get_attribute("src")
          and cards.nth(0).locator(".dc-rate").inner_text() == "採用率 95%" and cards.nth(0).get_attribute("href") == "?card=elf-ja", cards.nth(0).inner_html()[:300])
    check("deck page: a card nobody knows yet is still listed, without a link", page.locator("#deckBody div.deck-card", has_text="Unknown New Card").count() == 1)
    side = page.locator("#deckBody .deck-section").nth(1)
    check("deck page: sideboard", side.locator("h2").inner_text().replace("\n", "") == "サイドボード5枚"
          and side.locator(".dc-name").all_inner_texts() == ["Deathrite Shaman", "クァーサルの群れ魔道士"], side.locator(".dc-name").all_inner_texts())
    more = page.locator("#deckBody .deck-more")
    check("deck page: other popular cards, with share and average copies", "ほかによく使われるカード" in more.inner_text() and "English Only Thing" in more.inner_text()
          and "採用率 35%・平均2.5枚" in more.inner_text(), more.inner_text())
    check("deck page: what the share means", "100デッキ" in page.locator(".deck-foot").inner_text())
    if SHOTS: page.wait_for_timeout(400); page.screenshot(path="r2_deck.png", full_page=True)
    page.click("#deckExport summary")
    page.click("#deckExport [data-export=mtgo]")
    page.wait_for_function("document.querySelector('#deckExport [data-export=mtgo]').textContent === 'コピーしました'")
    clip = page.evaluate("navigator.clipboard.readText()")
    check("deck page: export for MTGO (English, sideboard after a blank line)", clip.startswith("4 Shivan Dragon\n4 Llanowar Elves\n") and "\n\n3 Qasali Pridemage\n2 Deathrite Shaman\n" in clip, clip)
    page.wait_for_timeout(1400)
    page.click("#deckExport summary")
    page.click("#deckExport [data-export=arena]")
    page.wait_for_function("document.querySelector('#deckExport [data-export=arena]').textContent === 'コピーしました'")
    clip = page.evaluate("navigator.clipboard.readText()")
    check("deck page: export for Arena (Deck / Sideboard headings)", clip.startswith("Deck\n4 Shivan Dragon\n4 Llanowar Elves\n") and "\n\nSideboard\n3 Qasali Pridemage\n2 Deathrite Shaman\n" in clip, clip)
    page.wait_for_timeout(1400)
    page.click("#deckBody [data-dview=list]")
    page.wait_for_selector("#deckBody .dl-row")
    rows = page.locator("#deckBody .deck-section").first.locator(".dl-row")
    check("deck page: list view - count, name, mana cost, share", rows.count() == 8 and rows.nth(0).locator(".dl-count").inner_text() == "4"
          and "ラノワールのエルフ" in rows.nth(0).inner_text() and rows.nth(0).locator(".dl-cost img").count() == 1 and rows.nth(0).locator(".dl-rate").inner_text() == "95%", rows.nth(0).inner_text())
    rows.nth(2).locator(".dl-name").hover()
    page.wait_for_function("document.getElementById('deckPeek').style.display === 'block'")
    check("deck page: hovering a name shows the card", "drag-ja" in page.get_attribute("#deckPeek", "src"))
    if SHOTS: page.screenshot(path="r2_deck_list.png", full_page=False)
    page.mouse.move(5, 5)
    page.reload(); page.wait_for_selector("#deckBody .dl-row")
    check("deck page: list view remembered", page.evaluate("localStorage.getItem('akuchie-deck-view')") == "list")
    page.click("#deckBody [data-dview=image]"); page.wait_for_selector("#deckBody .deck-card")
    page.locator("#deckBody a.deck-card", has_text="稲妻").click(); page.wait_for_selector("#cardView .cp-name")
    check("deck page: a card opens its page", "card=bolt-ja-m10" in page.url)
    page.click("#backToSearchBtn"); page.wait_for_selector("#deckBody .deck-card")
    check("…and back returns to the deck", "view=deck" in page.url)
    page.click("#deckBack"); page.wait_for_selector("#metaBody .meta-row")
    check("deck page: back to the metagame tab", "view=meta" in page.url)
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Orzhov&u=1"); page.wait_for_selector("#deckBody .deck-group")
    check("deck page: unclassified decks too", page.title().startswith("オルゾフ（未分類）") and "使用率 5.0%" in page.locator(".deck-head").inner_text())
    page.goto(SITE + "?view=deck&format=standard&deck=Nope"); page.wait_for_selector("#deckBody .status-line .serif")
    check("deck page: an unknown deck says so", "このデッキは見つかりませんでした" in page.locator("#deckBody").inner_text() and page.locator("#deckBody .status-line a").get_attribute("href").startswith("?view=meta&format=standard"))
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Gruul%20Dragons"); page.wait_for_selector("#deckBody .deck-group")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    page.wait_for_function("document.querySelector('#deckBody .dg-head') && document.querySelector('#deckBody .dg-head').firstChild.textContent === 'Creatures'")
    check("deck page in English", page.title() == "Gruul Dragons (Standard) deck list — 悪知恵" and "Llanowar Elves" in page.locator("#deckBody .deck-section").first.inner_text()
          and "Main deck" in page.locator("#deckBody").inner_text() and "in 95% of lists" in page.locator("#deckBody").inner_text(), page.title())
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'ja'")
    DECKS_MODE["mode"] = "absent"
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Gruul%20Dragons"); page.wait_for_selector("#deckBody .deck-group")
    gk = page.evaluate("[...document.querySelectorAll('#deckBody .dg-head')].map(h => h.firstChild.textContent)")
    check("deck page without meta_decks.json: key cards by type, and a note how to get whole lists", "meta_decks.json" in page.locator(".deck-note").inner_text()
          and gk == ["クリーチャー", "インスタント", "土地", "その他"] and page.locator("#deckBody .dc-count").count() == 0 and page.locator("#deckExport").count() == 0, gk)
    DECKS_MODE["mode"] = "fixture"
    page.goto(SITE); page.wait_for_selector("#homeMetaBody .hb-row")
    page.locator("#homeMetaBody a.hb-name").first.click(); page.wait_for_selector("#deckBody .deck-group")
    check("home: a top deck opens its deck page", "view=deck" in page.url and "deck=Gruul%20Dragons" in page.url, page.url)
    page.set_viewport_size({"width": 390, "height": 800}); page.wait_for_timeout(300)
    xs = sorted({round(c.bounding_box()["x"]) for c in page.locator("#deckBody .deck-section").first.locator(".deck-card").all()[:3]})
    check("phone: deck page fits, three cards to a row", no_hscroll() and len(xs) == 3, xs)
    if SHOTS: page.screenshot(path="r2_deck_phone.png", full_page=False)
    page.set_viewport_size({"width": 1280, "height": 900})

    # the logo clears everything and goes home
    home()
    top_search("飛行"); page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました')")
    page.locator("#sideAdvSlot .chip[data-color=W]").click()
    page.wait_for_function("document.querySelectorAll('#activeFilters .filter-pill').length === 1")
    page.click("#brandLink"); page.wait_for_selector("#homeHero", state="visible")
    check("logo: back to the home page, search and filters cleared", page.input_value("#heroInput") == "" and page.input_value("#searchInput") == ""
          and page.locator("#activeFilters .filter-pill").count() == 0 and page.evaluate("state.colors.size + state.query.length") == 0 and page.locator("#cardGrid .card-tile").count() == 0)
    page.goto(SITE + "?card=elf-ja"); page.wait_for_selector("#cardView .cp-name")
    page.click("#brandLink"); page.wait_for_selector("#homeHero", state="visible")
    check("logo from a card page: the home page", page.url == SITE and page.locator("#homeHero").is_visible(), page.url)

    # the search box follows the page (a short window, so the home page can scroll)
    page.set_viewport_size({"width": 1280, "height": 520})
    home()
    check("home: no top-bar search box while the big one is in view", not page.locator("#searchInput").is_visible())
    page.mouse.wheel(0, 500); page.wait_for_function("document.documentElement.dataset.heroOut === 'true'")
    sb = page.locator("#searchInput").bounding_box()
    check("home: scrolled past the big search box, the top bar's box appears and stays at the top", page.locator("#searchInput").is_visible() and 0 <= sb["y"] < 60, sb)
    if SHOTS: page.screenshot(path="r2_home_scrolled.png", full_page=False)
    page.evaluate("window.scrollTo(0, 0)"); page.wait_for_function("document.documentElement.dataset.heroOut === 'false'")
    check("…and goes away when the big box is back", not page.locator("#searchInput").is_visible())
    page.mouse.wheel(0, 500); page.wait_for_function("document.documentElement.dataset.heroOut === 'true'")
    page.fill("#searchInput", "稲妻"); page.press("#searchInput", "Escape"); page.press("#searchInput", "Enter")
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました')")
    check("…and searches", page.locator("#cardGrid .card-name-main").all_inner_texts() == ["稲妻"])
    for w in (1100, 1280):
        page.set_viewport_size({"width": w, "height": 420})
        page.click("#brandLink"); page.wait_for_selector("#homeHero", state="visible")
        seq = []
        top = page.evaluate("document.documentElement.scrollHeight - window.innerHeight")
        for y in range(0, min(640, top), 8):
            page.evaluate(f"window.scrollTo(0, {y})"); page.wait_for_timeout(30)
            seq.append(page.evaluate("document.documentElement.dataset.heroOut"))
        flips = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
        check(f"width {w}: scrolling down past the big box switches the top-bar box on exactly once (no flicker)", flips == 1 and seq[-1] == "true", seq)
    page.set_viewport_size({"width": 1280, "height": 900})

    # results: the advanced search on the left, staying in view
    DB_MODE["variant"] = "many"
    home()
    top_search("テスト用の熊"); page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 30")
    panel = page.locator("#filterPanel")
    pb, gb = panel.bounding_box(), page.locator("#cardGrid").bounding_box()
    check("results: advanced search on the left without opening it", panel.is_visible() and pb["x"] + pb["width"] <= gb["x"] and not page.locator("#filterOpenBtn").is_visible(), (pb, gb))
    if SHOTS: page.screenshot(path="r2_results_sidebar.png", full_page=False)
    page.mouse.wheel(0, 1600); page.wait_for_timeout(300)
    pb = panel.bounding_box()
    check("results: the sidebar stays in view while scrolling", 0 <= pb["y"] <= 140 and pb["y"] + 50 < 900, pb)
    page.focus("#creatureTypeFilter")
    check("sidebar: type suggestions open inside the panel", page.locator("#creatureTypeList").is_visible() and page.evaluate("getComputedStyle(document.getElementById('creatureTypeList')).position") == "static")
    page.press("#creatureTypeFilter", "Escape")
    page.locator("#sideAdvSlot .chip[data-color=W]").click()
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('0')")
    check("sidebar: filters apply to the results", page.locator("#cardGrid .card-tile").count() == 0)
    page.locator("#activeFilters .filter-pill").click(); page.wait_for_function("document.querySelectorAll('#cardGrid .card-tile').length === 30")
    page.set_viewport_size({"width": 900, "height": 900}); page.wait_for_timeout(250)
    check("narrower screens: the panel folds away above the results again", page.evaluate("document.getElementById('resultsAdvSlot').contains(document.getElementById('filterPanel'))")
          and page.locator("#filterOpenBtn").is_visible() and not panel.is_visible())

    # phones: the search box and tabs stay at the top
    page.set_viewport_size({"width": 390, "height": 800}); page.wait_for_timeout(250)
    page.evaluate("window.scrollTo(0, 0)"); page.wait_for_timeout(100)
    page.mouse.wheel(0, 1500); page.wait_for_timeout(300)
    sb, br, tb = page.locator("#searchInput").bounding_box(), page.locator(".brand").bounding_box(), page.locator("#tabSearch").bounding_box()
    check("phone: scrolling a long list keeps the search box and tabs at the top; the logo row scrolls away", 0 <= sb["y"] <= 24 and br["y"] + br["height"] <= 1 and 0 < tb["y"] < 130 and no_hscroll(), (sb, br, tb))
    if SHOTS: page.screenshot(path="r2_phone_scrolled.png", full_page=False)
    DB_MODE["variant"] = None
    page.click("#brandLink"); page.wait_for_selector("#homeHero", state="visible"); page.wait_for_timeout(200)
    page.mouse.wheel(0, 1300); page.wait_for_function("document.documentElement.dataset.heroOut === 'true'"); page.wait_for_timeout(300)
    sb = page.locator("#searchInput").bounding_box()
    check("phone home: once the big search box is out of sight, the top bar's box follows", page.locator("#searchInput").is_visible() and 0 <= sb["y"] <= 24, sb)
    if SHOTS: page.screenshot(path="r2_phone_home_scrolled.png", full_page=False)
    page.set_viewport_size({"width": 1280, "height": 900})
    DECKS_MODE["mode"] = "absent"

    # ---- 19. round 6: Commander combos at the bottom of card pages (preview.html only) ----
    PRICE_SITE["dir"] = PRICES_FULL
    DB_MODE["extra"] = True
    page.set_viewport_size({"width": 1280, "height": 900})
    n0 = len(calls)
    page.goto(SITE + "?card=altar-en"); page.wait_for_selector("#cardView .cp-name"); page.wait_for_timeout(800)
    check("live site: no combos yet (and neither their data nor the translator is downloaded)", not page.locator("#combosBox").is_visible()
          and not any("/c/" in c or "combo_ja" in c for c in calls[n0:]), [c for c in calls[n0:] if "/c/" in c or "combo_ja" in c])
    n0 = len(calls)
    page.goto(SITE + "preview.html?card=altar-en"); page.wait_for_selector("#combosBox .combo-row")
    box = page.locator("#combosBox")
    check("preview: combos under the card, most played first", box.locator(".combos-heading").inner_text().startswith("統率者戦のコンボ（8件）")
          and box.locator(".combo-row").count() == 6, box.locator(".combos-heading").inner_text())
    after_versions = page.evaluate("(() => { const v = document.getElementById('versionsBox').getBoundingClientRect(), c = document.getElementById('combosBox').getBoundingClientRect(); return c.top >= v.bottom - 1; })()")
    check("preview: the combo panel is at the bottom of the page", after_versions)
    row0 = box.locator(".combo-row").first
    chips = [c.strip() for c in row0.locator(".combo-chip").all_inner_texts()]
    check("preview: first combo - this card + Pack Rat (Japanese name, linked), its results and links", chips == ["アシュノッドの供犠台", "群れネズミ"]
          and row0.locator(".combo-chip.this").count() == 1 and row0.locator("a.combo-chip").get_attribute("href") == "?card=rat-ja"
          and row0.locator("a[href='https://commanderspellbook.com/combo/1-combo/']").count() == 1 and "5,000" in row0.inner_text(), (chips, row0.inner_text()))
    check("preview: results in Japanese", row0.locator(".combo-results").inner_text().replace("→", "").strip() == "無限の無色マナ・無限の死亡誘発", row0.locator(".combo-results").inner_text())
    check("preview: no format row on combos (they are for Commander)", box.locator(".combo-list .legal-circles, .combo-list .legal-circle").count() == 0)
    check("preview: the translator is loaded once, with the combos", sum("combo_ja.js" in c for c in calls[n0:]) == 1, [c for c in calls[n0:] if "combo_ja" in c])
    row1 = box.locator(".combo-row").nth(1)
    check("preview: a combo needing 'any card of a kind' shows it, in Japanese", row1.locator(".combo-chip.template").inner_text() == "頑強を持つクリーチャー", row1.locator(".combo-chip.template").inner_text())
    check("preview: a result the translator doesn't know stays in English", row1.locator(".combo-results").inner_text().replace("→", "").strip() == "無限の無色マナ・Some brand new result", row1.locator(".combo-results").inner_text())
    check("preview: the summary says the steps are in Japanese", row0.locator(".combo-steps summary").inner_text() == "前提条件と手順を見る", row0.locator(".combo-steps summary").inner_text())
    row0.locator(".combo-steps summary").click()
    st = row0.locator(".combo-steps").inner_text()
    steps = row0.locator(".combo-steps li").all_inner_texts()
    check("preview: prerequisites in Japanese with the Japanese card names", "アシュノッドの供犠台と群れネズミが戦場にある。" in st, st)
    check("preview: steps in Japanese, mana as symbols", steps == ["群れネズミを生け贄に捧げてアシュノッドの供犠台を起動し、を加える。", "群れネズミが死亡し、アシュノッドの供犠台が誘発する。", "繰り返す。"]
          and row0.locator(".combo-steps li").first.locator("img.sym").count() == 2 and not re.search(r"[A-Za-z]{3}", "".join(steps)), steps)
    row1.locator(".combo-steps summary").click()
    st1 = row1.locator(".combo-steps").inner_text()
    check("preview: a step the translator can't handle stays in English, and the summary says so", row1.locator(".combo-steps summary").inner_text() == "前提条件と手順を見る（一部英語）"
          and row1.locator(".combo-steps li").all_inner_texts() == ["Frobnicate the Llanowar Elves with a weird new trick.", "繰り返す。"], (row1.locator(".combo-steps summary").inner_text(), st1))
    if SHOTS: box.screenshot(path="combos_open.png")
    page.click("#comboMoreBtn")
    check("preview: 'show more' lists the rest", box.locator(".combo-row").count() == 8 and page.locator("#comboMoreBtn").count() == 0)
    page.wait_for_selector("#comboPartnerGrid .card-tile")
    check("preview: cards that combo with this one, as tiles", "群れネズミ" in page.locator("#comboPartnerGrid").inner_text(), page.locator("#comboPartnerGrid").inner_text())
    check("preview: source, date and a link to every combo on Commander Spellbook", "Commander Spellbook" in box.locator(".combo-note").inner_text() and "2026-10-08" in box.locator(".combo-note").inner_text()
          and "日本語にしたもの" in box.locator(".combo-note").inner_text()
          and box.locator(".combo-note a", has_text="すべて見る").get_attribute("href") == "https://commanderspellbook.com/search/?q=" + Q('card:"Ashnod\'s Altar"', safe="'"), box.locator(".combo-note").inner_html())
    if SHOTS: box.screenshot(path="combos.png")
    box.locator("a.combo-chip").first.click(); page.wait_for_selector("#combosBox .combo-row")
    check("preview: a combo card opens its page, with its own combos", "card=rat-ja" in page.url and page.locator("#combosBox .combos-heading").inner_text().startswith("統率者戦のコンボ（1件）"), page.url)
    page.goto(SITE + "preview.html?card=bolt-en-m10"); page.wait_for_selector("#cardView .cp-name"); page.wait_for_timeout(800)
    check("preview: a card without combos shows no panel", not page.locator("#combosBox").is_visible())
    page.goto(SITE + "preview.html?card=rag-en-mh2"); page.wait_for_selector("#combosBox .combo-row")
    check("preview: a combo with a card missing from the database still lists it (no link)", page.locator("#combosBox .combo-chip", has_text="Unknown Combo Piece").count() == 1
          and page.locator("#combosBox a.combo-chip", has_text="Unknown Combo Piece").count() == 0)
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_selector("#combosBox .combo-row")
    check("preview in English: heading", page.locator("#combosBox .combos-heading").inner_text().startswith("Commander combos (1)"), page.locator("#combosBox .combos-heading").inner_text())
    page.locator("#combosBox .combo-steps summary").first.click()
    check("preview in English: results and steps stay in English", page.locator("#combosBox .combo-results").first.inner_text().replace("→", "").strip() == "Infinite colorless mana"
          and page.locator("#combosBox .combo-steps summary").first.inner_text() == "Prerequisites and steps"
          and page.locator("#combosBox .combo-steps li").all_inner_texts() == ["Sacrifice a Rat to Ashnod's Altar.", "Repeat."], page.locator("#combosBox .combo-steps").first.inner_text())
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'ja'"); page.wait_for_selector("#combosBox .combo-row")
    page.wait_for_function("document.querySelector('#combosBox .combos-heading').textContent.startsWith('統率者戦のコンボ')")
    page.locator("#combosBox .combo-steps summary").first.click()
    check("…and back in Japanese: a line it can't fully translate (a card not in the combo) stays English", "Sacrifice a Rat to Ashnod's Altar." in page.locator("#combosBox .combo-steps").first.inner_text()
          and page.locator("#combosBox .combo-steps li").all_inner_texts()[-1] == "繰り返す。", page.locator("#combosBox .combo-steps").first.inner_text())
    page.set_viewport_size({"width": 390, "height": 800}); page.goto(SITE + "preview.html?card=altar-en"); page.wait_for_selector("#combosBox .combo-row")
    check("phone: combo panel fits", no_hscroll())
    if SHOTS: page.locator("#combosBox").screenshot(path="combos_phone.png")
    page.set_viewport_size({"width": 1280, "height": 900})
    PRICE_SITE["dir"] = None
    page.goto(SITE + "preview.html?card=altar-en"); page.wait_for_selector("#cardView .cp-name"); page.wait_for_timeout(800)
    check("preview: no combo data published -> no panel, no errors", not page.locator("#combosBox").is_visible())
    DB_MODE["extra"] = False

    # ---- 20. round 7: the lightweight mode ----
    PRICE_SITE["dir"] = PRICES_FULL
    META_MODE["mode"] = "fixture"
    DECKS_MODE["mode"] = "fixture"
    DB_MODE["extra"] = True
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(SITE); page.wait_for_selector("#homeHero", state="visible"); page.evaluate("localStorage.clear()")
    page.goto(SITE); page.wait_for_selector("#homeMoversBody .hb-row"); page.wait_for_selector("#hxList .hx-entry")
    check("normal mode: lite switch off, home boxes and examples shown, no lite note", page.get_attribute("#liteSwitch", "aria-checked") == "false" and page.locator("#homeBoxes").is_visible()
          and page.locator("#heroExample").is_visible() and not page.locator("#liteNote").is_visible())
    check("the lite switch says what it does", "画像やフォント" in (page.get_attribute("#liteSwitch", "title") or ""))
    page.wait_for_load_state("networkidle"); page.wait_for_timeout(300)   # the normal page's own picture requests are done
    n0 = len(calls)
    with page.expect_navigation():
        page.click("#liteSwitch")
    page.wait_for_selector("#homeHero", state="visible"); page.wait_for_timeout(800)
    got = calls[n0:]
    check("lite switch: on, remembered, and the page reloads in lite mode", page.evaluate("document.documentElement.dataset.lite") == "1"
          and page.get_attribute("#liteSwitch", "aria-checked") == "true" and page.evaluate("localStorage.getItem('akuchie-lite')") == "1")
    check("lite: no web fonts", page.evaluate("document.querySelectorAll('link[href*=googleapis]').length") == 0 and not any("fonts.g" in c for c in got), [c for c in got if "font" in c])
    check("lite: the home page downloads no card database, metagame, prices or pictures",
          not any(x in c for c in got for x in ("ja_cards", "meta.json", "movers.json", "warujie-prices", "cards.scryfall.io", "NAMED-IMAGE", "/cards/random")), got)
    check("lite: the home page is just the search, with a note and a way back", not page.locator("#homeBoxes").is_visible() and not page.locator("#heroExample").is_visible()
          and page.locator("#liteNote").is_visible() and "軽量モードで表示中" in page.locator("#liteNote").inner_text() and page.locator("#liteOff").inner_text() == "通常の表示に戻す")
    check("lite: still the same look (the Mincho name first, system fonts behind it)", "serif" in page.evaluate("getComputedStyle(document.querySelector('.hero-title')).fontFamily"))
    if SHOTS: page.screenshot(path="lite_home.png", full_page=False)
    page.click("#heroInput")
    page.wait_for_function("dbState !== 'loading'")
    check("lite: the card database downloads once the search box is used (the smaller file first; this test server only has the .gz)",
          [c.rsplit("/", 1)[-1] for c in calls[n0:] if "ja_cards" in c] == ["ja_cards.json", "ja_cards.json.gz"], [c for c in calls[n0:] if "ja_cards" in c])
    page.locator("#heroInput").press_sequentially("ラガ"); page.wait_for_selector("#heroSuggest .suggest-item")
    check("lite: name suggestions work", "ラガバン" in page.locator("#heroSuggest").inner_text() and page.locator("#heroSuggest img[src*='cards.scryfall.io']").count() == 0)
    page.press("#heroInput", "Escape")
    top_search("飛行")
    page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました')")
    page.wait_for_selector("#cardGrid .text-row")
    check("lite: results as text rows without pictures, no picture/text switch", page.locator("#cardGrid .text-row").count() == 2 and page.locator("#cardGrid img[src*='cards.scryfall.io']").count() == 0
          and not page.locator("#viewToggle").is_visible() and not any("cards.scryfall.io" in c for c in calls[n0:]), page.locator("#cardGrid").inner_text()[:200])
    if SHOTS: page.screenshot(path="lite_results.png", full_page=False)
    n1 = len(calls)
    page.locator("#cardGrid .text-row", has_text="シヴ山のドラゴン").click(); page.wait_for_selector("#cardView .cp-name")
    page.wait_for_timeout(500)
    check("lite: a result opens its card page", "card=drag-ja" in page.url)
    n1 = len(calls)
    page.goto(SITE + "?card=rag-ja-mh2"); page.wait_for_selector("#cardView .print-item"); page.wait_for_timeout(800)
    pics = [c for c in calls[n1:] if "cards.scryfall.io" in c]
    check("lite card page: only the card's own picture, not the large size", page.locator(".cp-art img").count() >= 1 and len(pics) == 1 and "/normal/rag-ja-mh2" in pics[0]
          and page.locator("#versionMenuPanel .print-item img[src*='cards.scryfall.io']").count() == 0, pics)
    check("lite card page: prices shown, price history behind a button", "¥6,000" in page.locator("#cardViewCard .price-section").inner_text()
          and page.locator("#priceHistory .lite-load").inner_text() == "価格の推移を表示" and not any("/h/" in c for c in calls[n1:]), [c for c in calls[n1:] if "prices" in c])
    if SHOTS: page.screenshot(path="lite_card.png", full_page=True)
    page.click("#priceHistory .lite-load"); page.wait_for_selector("#priceHistory svg .hist-line")
    check("lite: the button loads the price chart", any("/h/" in c for c in calls[n1:]) and page.locator("#priceHistory .lite-load").count() == 0)
    check("lite: no combos on the live site", page.locator("#combosBox .lite-load").count() == 0 and not page.locator("#combosBox").is_visible())
    n2 = len(calls)
    page.goto(SITE + "preview.html?card=altar-en"); page.wait_for_selector("#combosBox .lite-load")
    check("lite preview: the combos wait behind a button", page.locator("#combosBox .lite-load").inner_text() == "統率者戦のコンボを表示"
          and not any("/c/" in c or "combo_ja" in c for c in calls[n2:]), [c for c in calls[n2:] if "/c/" in c])
    page.click("#combosBox .lite-load"); page.wait_for_selector("#combosBox .combo-row")
    check("lite preview: the button loads the combos, in Japanese", "無限の無色マナ" in page.locator("#combosBox").inner_text() and any("combo_ja" in c for c in calls[n2:]))
    n3 = len(calls)
    page.goto(SITE + "?view=meta&format=legacy"); page.wait_for_selector("#metaBody .meta-row"); page.wait_for_timeout(500)
    check("lite metagame: no deck pictures, nothing sideways", page.locator("#metaBody img[src*='cards.scryfall.io']").count() == 0 and not any("cards.scryfall.io" in c or "NAMED-IMAGE" in c for c in calls[n3:])
          and no_hscroll(), [c for c in calls[n3:] if "cards.scryfall" in c or "NAMED" in c])
    if SHOTS: page.screenshot(path="lite_meta.png", full_page=False)
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Gruul%20Dragons"); page.wait_for_selector("#deckBody .dl-row"); page.wait_for_timeout(300)
    check("lite deck page: the text list, without the picture view", page.locator("#deckBody .dl-row").count() >= 8 and not page.locator("#deckBody .view-toggle").is_visible()
          and page.locator("#deckBody img[src*='cards.scryfall.io']").count() == 0)
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    page.goto(SITE); page.wait_for_selector("#homeHero", state="visible")
    check("lite in English: note and switch label", "Lite mode is on" in page.locator("#liteNote").inner_text() and page.locator("#liteSwitch .sq-label").inner_text() == "Lite"
          and page.locator("#liteOff").inner_text() == "Switch back to the full site")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'ja'")
    page.set_viewport_size({"width": 390, "height": 800}); page.goto(SITE); page.wait_for_selector("#homeHero", state="visible")
    check("lite phone: fits, and the menu has the lite switch on", no_hscroll() and (page.click("#menuBtn") or True) and page.locator("#liteSwitch").is_visible()
          and page.get_attribute("#liteSwitch", "aria-checked") == "true")
    if SHOTS: page.screenshot(path="lite_phone_menu.png", full_page=False)
    page.click("#homeHero .hero-title")
    if SHOTS: page.screenshot(path="lite_phone.png", full_page=False)
    page.set_viewport_size({"width": 1280, "height": 900})
    n4 = len(calls)
    with page.expect_navigation():
        page.click("#liteOff")
    page.wait_for_selector("#homeMoversBody .hb-row")
    check("'back to the full site': lite mode off, fonts, home boxes and pictures back", page.evaluate("document.documentElement.dataset.lite") is None
          and page.get_attribute("#liteSwitch", "aria-checked") == "false" and page.evaluate("localStorage.getItem('akuchie-lite')") is None
          and page.locator("#homeBoxes").is_visible() and any("fonts.googleapis" in c for c in calls[n4:]) and any("ja_cards" in c for c in calls[n4:]))
    page.evaluate("localStorage.setItem('akuchie-lite', '1')"); page.reload(); page.wait_for_selector("#liteNote", state="visible")
    with page.expect_navigation():
        page.click("#liteSwitch")
    page.wait_for_selector("#homeMoversBody .hb-row")
    check("the lite switch turns it off too", page.evaluate("document.documentElement.dataset.lite") is None and page.evaluate("localStorage.getItem('akuchie-lite')") is None)
    PRICE_SITE["dir"] = None
    DECKS_MODE["mode"] = "absent"
    DB_MODE["extra"] = False

    # ---- 21. round 8: the footer (Fan Content notice, sources, disclaimer, privacy, contact) ----
    page.set_viewport_size({"width": 1280, "height": 900})
    page.evaluate("localStorage.clear()")
    home()
    foot = page.locator("footer.attribution")
    ft = foot.inner_text()
    check("footer: the Fan Content notice starts with the site's name, word for word",
          "悪知恵 (Warujie) is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC." in ft
          and foot.locator("a", has_text="Fan Content Policy").get_attribute("href") == "https://company.wizards.com/en/legal/fancontentpolicy", ft[:300])
    check("footer: the notice in Japanese too", "非公式のファンコンテンツです" in ft)
    hrefs = foot.locator("a").evaluate_all("as => as.map(a => a.href)")
    need = ["https://scryfall.com/", "https://mtgjson.com/", "https://tcgcsv.com/", "https://www.cardmarket.com/", "https://frankfurter.dev/",
            "https://github.com/Jiliac/MTGODecklistCache", "https://github.com/Badaro/MTGOFormatData", "https://www.cardkingdom.com/", "https://manapool.com/",
            "https://tagger.scryfall.com/", "https://edhrec.com/"]
    check("footer: every data source credited with a link", all(h in hrefs for h in need) and "欧州中央銀行" in ft, [h for h in need if h not in hrefs])
    check("footer: Commander Spellbook only where the combos are (not on the live page)", not foot.locator(".combos-only").is_visible())
    check("footer: price disclaimer", "価格は参考値です" in ft and "各ショップでご確認ください" in ft)
    check("footer: privacy note", "Cookie・アクセス解析・広告はありません" in ft and "Google Fonts" in ft)
    cl = page.locator("#contactLink")
    check("footer: contact email link", cl.get_attribute("href") == "mailto:" + CONTACT and cl.inner_text() == CONTACT and "お問い合わせ" in ft)
    check("footer: the address isn't written out in the page source", CONTACT not in INDEX and CONTACT not in PREVIEW)
    if SHOTS: foot.screenshot(path="footer_ja.png")
    page.goto(SITE + "preview.html"); page.wait_for_selector("#homeHero", state="visible")
    check("preview footer: Commander Spellbook credited", page.locator("footer .combos-only").is_visible()
          and page.locator("footer .combos-only a").get_attribute("href") == "https://commanderspellbook.com")
    page.goto(SITE); page.wait_for_selector("#homeHero", state="visible")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    ft = foot.inner_text()
    check("English footer: no Japanese translation of the notice, everything else in English",
          "非公式" not in ft and "Prices are for reference only" in ft and "no accounts, cookies, analytics or ads" in ft and "Contact" in ft
          and "European Central Bank" in ft and page.locator("#contactLink").inner_text() == CONTACT, ft)
    if SHOTS: foot.screenshot(path="footer_en.png")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'ja'")
    page.set_viewport_size({"width": 390, "height": 800}); page.goto(SITE); page.wait_for_selector("#homeHero", state="visible")
    check("phone: footer fits", no_hscroll())
    if SHOTS: page.locator("footer.attribution").screenshot(path="footer_phone.png")
    page.set_viewport_size({"width": 1280, "height": 900})

    # ---- 22. round 9: listings and stock beside the prices; notes at the bottom; shop links on the left ----
    PRICE_SITE["dir"] = PRICES_FULL
    DB_MODE["extra"] = True
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(SITE); page.wait_for_selector("#homeHero", state="visible"); page.evaluate("localStorage.clear()")
    OFFER_JS = """[...document.querySelectorAll('#offersBox .of-row:not(.of-h)')].map(r => [
        (r.querySelector('.of-shop a') || r.querySelector('.of-shop')).textContent.replace(' ↗', '').trim(),
        r.querySelector('.of-lang:not(.of-country)') ? r.querySelector('.of-lang:not(.of-country)').textContent : '',
        r.querySelector('.of-cond').textContent, r.querySelector('.of-price .cur').title || r.querySelector('.of-price strong').textContent,
        r.querySelector('.of-price strong').textContent, r.querySelector('.of-stock').textContent])"""   # the shop's own price, then the shown one
    offer_rows = lambda: page.evaluate(OFFER_JS)
    ob = page.locator("#offersBox")
    page.goto(SITE + "?card=rag-ja-mh2")
    page.wait_for_selector("#offersBox .of-row:not(.of-h)")
    page.wait_for_function("document.querySelector('#cardViewCard .shop-prices') && document.querySelector('#cardViewCard .shop-prices').textContent.includes('Cardsphere')")
    us_rows = [["Mana Pool", "", "LP", "$35.50", "¥5,325", "2点"], ["TCGplayer", "", "—", "$37.50", "¥5,625", "出品あり"],
               ["Card Kingdom", "", "EX", "$38.24", "¥5,736", "1点"], ["Mana Pool", "", "NM", "$39.00", "¥5,850", "4点"],
               ["Mana Pool", "日本語", "NM", "$42.00", "¥6,300", "1点"], ["Card Kingdom", "", "NM", "$44.99", "¥6,749", "3点"]]
    check("listings: every shop's copies by condition, cheapest first, with yen and stock (sold-out ones left out)", offer_rows() == us_rows, offer_rows())
    check("listings: heading, market and columns", ob.locator(".offers-title").inner_text().replace("\n", "") == "出品と在庫安い順"
          and ob.locator(".of-h > span").all_inner_texts() == ["ショップ", "状態", "価格", "在庫"], (ob.locator(".offers-title").inner_text(), ob.locator(".of-h > span").all_inner_texts()))
    check("listings: the cheapest is marked", ob.locator(".of-row.best").count() == 1 and ob.locator(".of-row.best .of-price strong").inner_text() == "¥5,325")
    pb, sb, cb = psec.bounding_box(), page.locator("#cardViewCard .shop-prices").bounding_box(), page.locator("#cardViewCard .cp-info").bounding_box()
    obb = ob.bounding_box()
    check("listings: in the space right of the prices, from the top of the price area, inside the card box",
          obb["x"] >= sb["x"] + sb["width"] and abs(obb["y"] - pb["y"]) < 40 and obb["x"] + obb["width"] <= cb["x"] + cb["width"] and obb["width"] >= 360, (pb, sb, obb, cb))
    olink = lambda shop: ob.locator(".of-shop a", has_text=shop).first.get_attribute("href")
    check("listings: shop names open the card at that shop (product pages)", olink("Card Kingdom") == "https://www.cardkingdom.com/mtg/modern-horizons-2/ragavan-nimble-pilferer"
          and olink("Mana Pool") == "https://manapool.com/card/mh2/138/ragavan-nimble-pilferer" and olink("TCGplayer") == "https://www.tcgplayer.com/product/1001"
          and ob.locator(".of-shop a").first.get_attribute("target") == "_blank", [olink("Card Kingdom"), olink("Mana Pool"), olink("TCGplayer")])
    check("listings: conditions explained on hover; TCGplayer's unknown condition and stock say so",
          ob.locator(".of-cond", has_text="LP").first.get_attribute("title") == "ライトリープレイド（軽い傷）"
          and "公開されていません" in ob.locator(".of-cond.any").first.get_attribute("title") and "公開されていません" in ob.locator(".of-stock.any").first.get_attribute("title"))
    if SHOTS: page.screenshot(path="offers_us.png", full_page=False); page.locator("#cardViewCard .cp-info").screenshot(path="offers_us_box.png")
    sw = page.locator("#offerFoil")
    check("listings: a foil switch, off at first", sw.get_attribute("role") == "switch" and sw.get_attribute("aria-checked") == "false" and sw.inner_text().strip() == "フォイル")
    sw.click(); page.wait_for_function("document.getElementById('offerFoil').getAttribute('aria-checked') === 'true'")
    foil_rows = [["TCGplayer", "", "—", "$55.00", "¥8,250", "出品あり"], ["Mana Pool", "", "NM", "$58.00", "¥8,700", "2点"], ["Card Kingdom", "", "NM", "$69.99", "¥10,499", "1点"]]
    check("listings: the foil switch shows the foil copies", offer_rows() == foil_rows and ob.locator(".of-shop a", has_text="Card Kingdom").get_attribute("href").endswith("-foil"), offer_rows())
    page.reload(); page.wait_for_selector("#offersBox .of-row:not(.of-h)")
    check("listings: the foil choice is remembered", page.get_attribute("#offerFoil", "aria-checked") == "true" and offer_rows() == foil_rows)
    if SHOTS: page.locator("#cardViewCard .cp-info").screenshot(path="offers_foil_box.png")
    page.click("#offerFoil"); page.wait_for_function("document.getElementById('offerFoil').getAttribute('aria-checked') === 'false'")
    check("listings: switched back to non-foil", offer_rows() == us_rows)
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="eu"]'); wait_market("eu")
    page.wait_for_selector("#offersBox[data-market=eu] .of-row:not(.of-h)")
    eu_rows = offer_rows()
    countries = page.evaluate("[...document.querySelectorAll('#offersBox .of-row:not(.of-h)')].map(r => r.querySelector('.of-country') ? r.querySelector('.of-country').textContent : '')")
    check("listings: Europe tab - CardTrader's sellers in Europe (condition, language, stock, country) and Cardmarket's cheapest offer, in euros",
          eu_rows == [["CardTrader", "", "SP", "€29.00", "¥4,640", "2点"], ["Cardmarket", "", "—", "€31.90", "¥5,104", "出品あり"], ["CardTrader", "日本語", "NM", "€33.00", "¥5,280", "1点"]]
          and countries == ["IT", "", "DE"] and "安い順" in ob.locator(".offers-title").inner_text()
          and olink("Cardmarket") == "https://www.cardmarket.com/en/Magic/Products?idProduct=2001" and olink("CardTrader") == "https://www.cardtrader.com/cards/701"
          and ob.locator(".of-country").first.get_attribute("title") == "出品者の国：IT", (eu_rows, countries, olink("CardTrader")))
    eu_notes = page.locator("#priceNotes").inner_text()
    check("notes: Europe names CardTrader with its date and the European condition grades", "CardTrader の欧州の出品者（" in eu_notes and "SP＝軽い傷" in eu_notes, eu_notes)
    page.click("#offerFoil"); page.wait_for_function("document.getElementById('offerFoil').getAttribute('aria-checked') === 'true'")
    check("listings: Europe foil - CardTrader's Mint copy and Cardmarket's foil low", offer_rows() == [["Cardmarket", "", "—", "€48.00", "¥7,680", "出品あり"], ["CardTrader", "", "M", "€50.00", "¥8,000", "1点"]], offer_rows())
    page.click("#offerFoil"); page.wait_for_function("document.getElementById('offerFoil').getAttribute('aria-checked') === 'false'")
    if SHOTS: page.locator("#cardViewCard .cp-info").screenshot(path="offers_eu_box.png")
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="jp"]'); wait_market("jp")
    page.wait_for_selector("#offersBox[data-market=jp]", state="attached")
    check("listings: Japan tab - no listings column (the price notice covers both)", ob.is_hidden() and ob.locator(".of-row").count() == 0
          and "在庫" in page.locator("#cardViewCard .jp-notice").inner_text())
    if SHOTS: page.locator("#cardViewCard .cp-info").screenshot(path="offers_jp_box.png")
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="us"]'); wait_market("us")
    page.wait_for_selector("#offersBox[data-market=us] .of-row:not(.of-h)")
    # the notes moved to the bottom of the page; the exchange rates stay
    notes = page.locator("#priceNotes")
    nt = notes.inner_text()
    vb, nb = page.locator("#versionsBox").bounding_box(), notes.bounding_box()
    check("notes: at the bottom of the page, under every other part", nb["y"] >= vb["y"] + vb["height"] - 1 and notes.is_visible(), (vb, nb))
    check("notes: the English-printing note, the sources with their date and where the listings come from", "英語版の価格を表示" in nt and "TCGCSV" in nt
          and "Card Kingdom（2026/10/8時点）・Mana Pool（2026/10/9時点）" in nt and "状態の目安" in nt and nt.startswith("価格について"), nt)
    st = psec.inner_text()
    check("notes: the price area keeps only the exchange rates", "1ドル＝150.00円" in st and "英語版の価格" not in st and "TCGCSV" not in st and "Card Kingdom（" not in st, st)
    if SHOTS: notes.screenshot(path="price_notes.png")
    # shop links: under the prices, on the left
    sl = page.locator("#cardViewCard .shop-links")
    lab, groups = sl.locator(".cp-row-label").bounding_box(), [g.bounding_box() for g in sl.locator(".shop-group").all()]
    chips_right = max(b["x"] + b["width"] for b in [c.bounding_box() for c in sl.locator(".external-link-btn:visible").all()])
    check("shop links: the label above the countries, all on the left of the listings", all(abs(g["x"] - lab["x"]) < 2 and g["y"] >= lab["y"] + lab["height"] - 1 for g in groups)
          and chips_right <= obb["x"] and abs(lab["x"] - pb["x"]) < 2, (lab, groups, chips_right, obb))
    # more than 8 copies: the rest on request
    page.goto(SITE + "?card=saga-ja"); page.wait_for_selector("#offersBox .of-row:not(.of-h)")
    sc = page.evaluate("(() => { const b = document.querySelector('#offersBox .of-scroll'); const cs = getComputedStyle(b); return [b.scrollHeight > b.clientHeight + 20, cs.overflowY, cs.scrollbarWidth, b.clientHeight]; })()")
    check("listings: every copy at once, in a box that scrolls with a thin scrollbar (no 'show all')", ob.locator(".of-scroll .of-row").count() == 12 and page.locator("#offersMore").count() == 0
          and sc[0] and sc[1] == "auto" and sc[2] == "thin" and 300 <= sc[3] <= 400, sc)
    head_y = ob.locator(".of-h").bounding_box()["y"]
    page.evaluate("document.querySelector('#offersBox .of-scroll').scrollTop = 9999"); page.wait_for_timeout(100)
    check("listings: scrolling the box keeps the column names and the page where they are", abs(ob.locator(".of-h").bounding_box()["y"] - head_y) < 1
          and ob.locator(".of-scroll .of-row").last.is_visible())
    rows = offer_rows()
    check("listings: all twelve, other languages marked", len(rows) == 12 and [r[3] for r in rows] == ["$15.00", "$21.00", "$24.74", "$26.00", "$27.00", "$28.00", "$28.04", "$28.50", "$29.50", "$30.00", "$32.99", "$36.00"]
          and [r[1] for r in rows if r[1]] == ["ドイツ語", "フランス語", "日本語"] and page.locator("#offersMore").count() == 0, rows)
    page.goto(SITE + "?card=drs-en"); page.wait_for_selector("#offersBox .of-row:not(.of-h)")
    check("listings: a printing with only foil copies opens on foil (the remembered choice unchanged)", page.get_attribute("#offerFoil", "aria-checked") == "true"
          and [r[2:4] for r in offer_rows()] == [["LP", "$11.00"], ["NM", "$12.50"]] and page.evaluate("localStorage.getItem('akuchie-offer-foil')") != "1", offer_rows())
    page.click("#offerFoil"); page.wait_for_function("document.getElementById('offerFoil').getAttribute('aria-checked') === 'false'")
    check("listings: …and can still be switched to non-foil (none found)", "この版の出品は見つかりませんでした" in ob.inner_text())
    page.goto(SITE + "?card=bolt-en-m10"); page.wait_for_function("document.querySelector('#offersBox .offers-empty') && document.querySelector('#offersBox .offers-empty').textContent.includes('見つかりません')")
    check("listings: a printing nobody sells says so", "この版の出品は見つかりませんでした" in ob.inner_text() and ob.locator(".of-row").count() == 0, ob.inner_text())
    # English
    page.goto(SITE + "?card=rag-ja-mh2"); page.wait_for_selector("#offersBox .of-row:not(.of-h)")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    page.wait_for_selector("#offersBox .of-row:not(.of-h)")
    er = offer_rows()
    check("listings in English", ob.locator(".offers-title").inner_text().replace("\n", "") == "Listings and stockcheapest first"
          and ob.locator(".of-h > span").all_inner_texts() == ["Shop", "Condition", "Price", "Stock"] and er[0][5] == "2" and er[1][5] == "listed"
          and er[4][1] == "Japanese" and page.locator("#priceNotes .price-notes-heading").inner_text() == "About the prices", er)
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'ja'")
    # narrower screens: the listings go under the prices
    for w in (1100, 900):
        page.set_viewport_size({"width": w, "height": 900}); page.wait_for_timeout(250)
        pb, obb = psec.bounding_box(), ob.bounding_box()
        check(f"width {w}: listings under the prices, nothing sideways", obb["y"] >= pb["y"] + pb["height"] - 1 and no_hscroll(), (pb, obb))
    page.set_viewport_size({"width": 390, "height": 800}); page.goto(SITE + "?card=rag-ja-mh2"); page.wait_for_selector("#offersBox .of-row:not(.of-h)")
    page.wait_for_timeout(300)
    rb = [r.bounding_box() for r in ob.locator(".of-row").all()]
    check("phone: the listings fit under the prices", no_hscroll() and all(b["x"] >= 0 and b["x"] + b["width"] <= 390 for b in rb)
          and ob.bounding_box()["y"] >= psec.bounding_box()["y"] + psec.bounding_box()["height"] - 1, rb[:2])
    if SHOTS: ob.screenshot(path="offers_phone.png"); page.locator("#priceNotes").screenshot(path="price_notes_phone.png")
    page.set_viewport_size({"width": 1280, "height": 900})
    page.evaluate("localStorage.clear()")
    PRICE_SITE["dir"] = None
    DB_MODE["extra"] = False

    # ---- 23. round 11: roles (player slang), role chips, help when nothing is found, similar cards ----
    os.makedirs(os.path.join(PRICES_ROLES, "t"), exist_ok=True)
    open(os.path.join(PRICES_ROLES, "t", "tags.json.gz"), "wb").write(gzip.compress(json.dumps(TAGS_FIXTURE).encode()))
    PRICE_SITE["dir"] = PRICES_ROLES
    DB_MODE["variant"] = "roles"
    page.set_viewport_size({"width": 1280, "height": 900})
    home(); page.evaluate("localStorage.clear()")
    home()
    names = lambda: page.locator("#cardGrid .card-name-main").all_inner_texts()
    note = lambda: page.locator("#matchNote").inner_text()
    DONE = """(() => { const g = document.getElementById('cardGrid');
        if (g.querySelector('.spinner') || document.querySelector('#zeroHelp .zh-loading')) return false;
        return !!(g.querySelector('.card-tile, .text-row') || g.querySelector('.status-line')); })()"""
    def run(q):
        before = page.evaluate("searchToken")
        top_search(q)
        page.wait_for_function(f"searchToken > {before}")
        page.wait_for_function(DONE)
        page.wait_for_timeout(120)
    def literal_count():
        page.wait_for_function("!document.querySelector('#matchNote .role-literal') || document.querySelector('#matchNote .role-count').textContent")
        el = page.locator("#matchNote .role-count")
        return el.inner_text() if el.count() else None

    # role words: slang finds what it means, most played first
    run("ドロー")
    check("roles: ドロー finds the cards that draw (role), in あいうえお order of their readings; a name containing ドロー (ドローン) is not one of them",
          names() == ["研究テスト", "熟考漂いテスト", "論争テスト"], names())
    n = note()
    check("roles: the note says it's the role ドロー (no 'most played' note in the default order)", "役割「ドロー」のカードを表示しています。" in n and "よく使われているカードから順に並べています。" not in n, n)
    before = page.evaluate("searchToken")
    page.select_option("#sortSelect", "popular")
    page.wait_for_function(f"searchToken > {before}"); page.wait_for_function(DONE); page.wait_for_timeout(120)
    check("roles: the 'most played' order puts the most played first, and says so", names() == ["研究テスト", "論争テスト", "熟考漂いテスト"]
          and "よく使われているカードから順に並べています。" in note(), (names(), note()))
    before = page.evaluate("searchToken")
    page.select_option("#sortSelect", "name")
    page.wait_for_function(f"searchToken > {before}"); page.wait_for_function(DONE); page.wait_for_timeout(120)
    n = note()
    lc = literal_count()
    check("roles: a link to search names and rules text for ドロー instead, with how many it finds", "「ドロー」をカード名・効果文から探す" in n and lc == "（4件）", (n, lc))
    page.click("#matchNote .role-literal")
    page.wait_for_function("document.getElementById('searchInput').value === '\"ドロー\"'"); page.wait_for_function(DONE)
    lit = names()
    check("roles: the text search (in quotes) works as before: ドローン by its name, draw by the rules text", len(lit) == 4 and "ドローンテスト" in lit and "研究テスト" in lit
          and "役割「ドロー」として探す" in note(), (lit, note()))
    page.click("#matchNote .role-literal")
    page.wait_for_function("document.getElementById('searchInput').value === 'ドロー'"); page.wait_for_function(DONE)
    check("roles: …and back to the role", names() == ["研究テスト", "熟考漂いテスト", "論争テスト"], names())
    run("ランプ")
    check("roles: ランプ is ramp (mana) - not トランプル, and not Path, whose land goes to the opponent", names() == ["加速の石", "ラノワールのエルフ"], names())
    check("roles: the note names the role ランプ stands for", "「ランプ」を役割「マナ加速」として検索しました。" in note() and literal_count() == "（1件）", note())
    run("トランプル")
    check("roles: the text and keyword search is unchanged (トランプル finds trample)", names() == ["トランプルの獣"] and page.locator("#matchNote .role-literal").count() == 0, (names(), note()))
    run("サクり台")
    check("roles: サクり台 (ひらがな り) finds the sac outlet that stays on the battlefield, not a one-shot spell", names() == ["予見者テスト"], names())
    run("サクリ台")
    check("roles: サクリ台 (カタカナ) too", names() == ["予見者テスト"], names())
    run("赤の除去")
    check("roles: 赤の除去 - red removal, あいうえお order", names() == ["稲妻", "大きな稲妻テスト", "ショック"], names())
    check("roles: …the note says red", "役割「除去」として検索しました" in note() and "条件：赤。" in note(), note())
    run("除去 マナ総量<=1 色:w")
    check("roles: with the search's own conditions", names() == ["剣テスト", "道テスト"], names())
    run("2マナの除去")
    check("roles: 2マナの除去", names() == ["大きな稲妻テスト"], names())
    run("クローン")
    check("roles: a role word that is also a card's name shows that card first", names()[:1] == ["クローン"], names())
    run("加速")
    check("roles: 加速 - the card called 加速 first, then ramp", names() == ["加速", "加速の石", "ラノワールのエルフ"], names())
    run("ライフ回復")
    check("roles: life gain leaves out cards where only the opponent gains life", page.locator("#cardGrid .status-line").count() == 1 and "見つかりませんでした" in page.locator("#cardGrid").inner_text(), names())
    run("-除去 ドロー")
    check("roles: - in front leaves a role out", names() == ["研究テスト", "熟考漂いテスト", "論争テスト"] and "役割「除去」のカードを除いています。" in note(), note())
    run("役割:サクり台")
    check("roles: the 役割: operator", names() == ["予見者テスト"], names())
    run("otag:burn 色:u")
    check("roles: otag: (Scryfall's syntax) for the tags themselves", names() == ["青い稲妻テスト"], names())
    run("破壊")
    check("roles: rules-text words are not roles (破壊 searched as text, no role note)", page.locator("#matchNote .role-literal").count() == 0 and "役割" not in note(), note())
    check("roles: none of the home page's effect examples is read as a role", page.evaluate("HERO_EFFECTS.filter(fx => buildSearchPlan(fx[1] || fx[0]).roles.length || buildSearchPlan(fx[3] || fx[2]).roles.length).length") == 0)
    page.fill("#searchInput", ""); page.focus("#searchInput"); page.locator("#searchInput").press_sequentially("ドロ")
    page.wait_for_selector("#searchSuggest .role-suggest")
    first = page.locator("#searchSuggest .suggest-item").first
    check("suggestions: a role word is offered while typing (ドロ -> ドロー, search by role), before card names",
          first.locator(".s-main").inner_text() == "ドロー" and first.locator(".s-sub").inner_text() == "役割で探す"
          and "ドローンテスト" in page.locator("#searchSuggest").inner_text(), page.locator("#searchSuggest").inner_text())
    check("suggestions: the role line has no green ＋, the card names under it do",
          page.locator("#searchSuggest .role-suggest").evaluate("b => !b.closest('li').querySelector('.sug-add')")
          and page.locator("#searchSuggest .sug-add").count() == page.locator("#searchSuggest .suggest-item:not(.role-suggest)").count() >= 1)
    first.click(); page.wait_for_function(DONE)
    check("suggestions: picking it searches the role", page.evaluate("document.getElementById('searchInput').value") == "ドロー" and names() == ["研究テスト", "熟考漂いテスト", "論争テスト"], names())
    page.fill("#searchInput", ""); page.focus("#searchInput"); page.locator("#searchInput").press_sequentially("ランプ")
    page.wait_for_selector("#searchSuggest .suggest-item")
    check("suggestions: slang says which role it is", page.locator("#searchSuggest .suggest-item .s-sub").first.inner_text() == "役割「マナ加速」で探す", page.locator("#searchSuggest").inner_text())
    page.press("#searchInput", "Escape")
    run("赤の除去")
    check("roles: a card whose name contains the search (赤の除去テスト) doesn't turn it into a name search", names() == ["稲妻", "大きな稲妻テスト", "ショック"], names())
    run("赤の除去テスト")
    check("roles: …the card is found by its full name", names() == ["赤の除去テスト"], names())
    run("吹きさらしの要塞テスト")
    check("furigana: a name printed with furigana is found without it, and shown without it", names() == ["吹きさらしの要塞テスト"], names())
    if SHOTS: page.screenshot(path="roles_search.png")

    # the role filter in the advanced search
    page.fill("#searchInput", ""); page.evaluate("state.query = ''")
    open_adv()
    page.click("#roleFilter")
    page.wait_for_function("document.querySelectorAll('#roleList .check-row').length > 40")
    page.locator("#roleFilter").press_sequentially("ランプ")
    page.wait_for_function("document.querySelectorAll('#roleList .check-row').length >= 1")
    first = page.locator("#roleList .check-row").first.inner_text().split()
    check("role filter: slang finds the role in the list (ランプ -> マナ加速)", first == ["マナ加速", "Ramp"], first)
    page.locator("#roleList .check-row", has_text="マナ加速").locator("input").check()
    page.wait_for_function(DONE)
    pills = page.locator("#activeFilters .filter-pill").all_inner_texts()
    check("role filter: a pill, and only ramp cards", [p.replace("×", "").strip() for p in pills] == ["役割：マナ加速"] and sorted(names()) == sorted(["加速の石", "ラノワールのエルフ"]), (pills, names()))
    page.click(".chip[data-color=G]"); page.wait_for_function(DONE)
    check("role filter: with a color", names() == ["ラノワールのエルフ"], names())
    page.click("#activeFilters .filter-pill[data-group=roles]"); page.wait_for_function(DONE)
    check("role filter: the pill removes it", page.locator("#activeFilters .filter-pill[data-group=roles]").count() == 0 and "トランプルの獣" in names(), names())
    page.click("#clearBtn"); page.wait_for_timeout(200)
    setFilterDrawer = page.evaluate("setFilterDrawer(false)")

    # help when nothing is found
    run("稲要")
    zh = page.locator("#zeroHelp")
    check("no results: a close card name", "もしかして" in zh.inner_text() and zh.locator("a.zh-card", has_text="稲妻").count() == 1, zh.inner_text())
    page.click(".chip[data-color=R]") if False else None
    open_adv(); page.click(".chip[data-color=U]"); page.wait_for_function(DONE)
    page.evaluate("setFilterDrawer(false)")
    run("飛行 速攻")
    zt = zh.inner_text()
    check("no results with a filter on: fewer words or fewer filters, each with how many it finds",
          "「速攻」を外す1件" in zt and "絞り込みを外す" not in zt, zt)
    run("ドラゴン 飛行")
    zt = zh.inner_text()
    check("no results: removing the color filter (with its count)", "「色：青」を外す1件" in zt, zt)
    zh.locator(".zh-btn", has_text="「色：青」を外す").click(); page.wait_for_function(DONE)
    check("no results: the suggestion removes the filter and searches", names() == ["シヴ山のドラゴン"] and page.locator("#activeFilters .filter-pill").count() == 0, names())
    run("役割:ほげ")
    zt = zh.inner_text()
    check("no results: an unknown role says so and offers roles", "「ほげ」という役割はありません。" in note() and "役割の例" in zt and "除去" in zt, (note(), zt))
    run("似:稲要")
    zt = zh.inner_text()
    check("no results: 似: with an unknown card says so and offers close names", "「稲要」という名前のカードが見つかりませんでした。" in note() and "稲妻" in zt, (note(), zt))
    zh.locator(".zh-btn", has_text="稲妻").first.click(); page.wait_for_function(DONE)
    check("no results: …which searches 似:稲妻", page.evaluate("document.getElementById('searchInput').value") == "似:稲妻" and "ショック" in names(), names())
    if SHOTS: run("ドラゴン 飛行 色:u"); page.screenshot(path="zero_help.png")

    # similar cards in search: 似:<name>, with any filters
    run("似:稲妻")
    sim_all = names()
    check("similar search: the closest effects first (same text and roles), the card itself left out",
          set(sim_all[:3]) == {"ショック", "青い稲妻テスト", "大きな稲妻テスト"} and "稲妻" not in sim_all, sim_all)
    check("similar search: the note links the card", "「稲妻」に効果が近い順に表示しています" in note() and page.locator("#matchNote a[data-card]").inner_text() == "稲妻", note())
    run("似:稲妻 色<=r マナ総量<=1")
    check("similar search: with colors within red and mana value 1 or less", names()[:1] == ["ショック"] and "青い稲妻テスト" not in names() and "大きな稲妻テスト" not in names(), names())
    open_adv(); page.click(".opt-chip[data-group=rarity][data-value=rare]"); page.wait_for_function(DONE)
    page.evaluate("setFilterDrawer(false)")
    check("similar search: …and with the panel's filters", "ショック" not in names(), names())
    page.click("#clearBtn") if page.locator("#clearBtn").is_visible() else page.evaluate("document.getElementById('clearBtn').click()")
    page.wait_for_timeout(300)

    # the card page: role chips and similar cards
    page.goto(SITE + "?card=bolt-ja-m10")
    page.wait_for_selector("#cpRoles .role-chip")
    chips = page.locator("#cpRoles .role-chip").all_inner_texts()
    check("card page: the card's roles as chips under the rules text", chips == ["除去", "クリーチャー除去", "火力"] and page.locator("#cpRoles .cp-row-label").inner_text() == "役割", chips)
    tb, rb = page.locator("#cardViewCard .cp-text").bounding_box(), page.locator("#cpRoles").bounding_box()
    check("card page: the chips sit right under the rules text", rb["y"] >= tb["y"] + tb["height"] - 1 and rb["y"] - (tb["y"] + tb["height"]) < 40, (tb, rb))
    check("card page: no similar cards section", page.locator("#similarBox").count() == 0 and "似た効果のカード" not in page.locator("#cardView").inner_text())
    page.locator("#cpRoles .role-chip", has_text="火力").click()
    page.wait_for_function("document.getElementById('searchInput').value === '火力'"); page.wait_for_function(DONE)
    check("card page: a role chip searches that role", names() == ["青い稲妻テスト", "稲妻", "大きな稲妻テスト", "ショック"] and "役割「火力」" in note(), names())
    page.evaluate("localStorage.removeItem('akuchie-similar')")
    page.goto(SITE + "?card=elf-ja"); page.wait_for_selector("#cpRoles .role-chip")
    check("card page: other cards' roles", page.locator("#cpRoles .role-chip").all_inner_texts() == ["マナ加速", "マナ・クリーチャー"])
    page.goto(SITE + "?card=drag-ja"); page.wait_for_selector("#cardViewCard .price-section")
    page.wait_for_timeout(600)
    check("card page: a card without roles has no role row", not page.locator("#cpRoles").is_visible())

    # phone
    page.set_viewport_size({"width": 390, "height": 800})
    page.goto(SITE + "?card=bolt-ja-m10"); page.wait_for_selector("#cpRoles .role-chip"); page.wait_for_timeout(300)
    check("phone: the card page with roles fits", no_hscroll())
    run("ドラゴン 飛行 色:u")
    check("phone: the help when nothing is found fits", no_hscroll() and page.locator("#zeroHelp .zh-btn").count() >= 1)
    if SHOTS: page.screenshot(path="zero_help_phone.png", full_page=True)
    page.set_viewport_size({"width": 1280, "height": 900})

    # English
    home()
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    run("card draw")
    check("English: card draw (two words) is the role, A→Z", names() == ["Dispute Test", "Mulldrifter Test", "Study Test"] and "Showing cards with the role “Card draw”." in note(), (names(), note()))
    run("red removal")
    check("English: red removal", names() == ["Big Bolt Test", "Lightning Bolt", "Shock"] and "Narrowed to red." in note(), (names(), note()))
    run("common red removal")
    check("English: the full name of a card is a name search", names() == ["Common Red Removal Test"], names())
    run("draw")
    check("English: words printed on cards stay text (draw)", "role" not in note().lower() and "Study Test" in names(), note())
    run("Clone")
    check("English: a role word that is a card's name", names()[:1] == ["Clone"], names())
    page.goto(SITE + "?card=bolt-ja-m10"); page.wait_for_selector("#cpRoles .role-chip")
    check("English: chips", page.locator("#cpRoles .role-chip").all_inner_texts() == ["Removal", "Creature removal", "Burn"])
    page.locator("#cpRoles .role-chip", has_text="Burn").click()
    page.wait_for_function("document.getElementById('searchInput').value === 'burn'"); page.wait_for_function(DONE)
    check("English: a chip searches the English slang", names()[:2] == ["Big Bolt Test", "Blue Bolt Test"], names())
    run("big blt test")
    check("English: no results - did you mean", "Did you mean" in page.locator("#zeroHelp").inner_text() and page.locator("#zeroHelp a.zh-card", has_text="Big Bolt Test").count() == 1, page.locator("#zeroHelp").inner_text())
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'ja'")

    # the lightweight mode: no similar cards; the role data isn't downloaded for the card page
    page.evaluate("localStorage.setItem('akuchie-lite', '1')")
    page.goto(SITE + "?card=bolt-ja-m10"); page.wait_for_selector("#cardViewCard .price-section"); page.wait_for_timeout(500)
    check("lightweight: no similar cards, no role data downloaded", page.locator("#similarBox").count() == 0 and page.evaluate("tagsState") == "idle")
    page.evaluate("localStorage.removeItem('akuchie-lite')")

    # without the role data: role words are searched as text, and the page says so
    PRICE_SITE["dir"] = PRICES_FULL
    home()
    run("ドロー")
    check("no role data: ドロー searched as text (as before), and the note says why", "ドローンテスト" in names() and "役割のデータを読み込めなかったため" in note(), (names(), note()))
    page.goto(SITE + "?card=bolt-ja-m10"); page.wait_for_selector("#cardViewCard .price-section"); page.wait_for_timeout(800)
    check("no role data: no role chips", not page.locator("#cpRoles").is_visible())

    PRICE_SITE["dir"] = None
    DB_MODE["variant"] = None
    page.evaluate("localStorage.clear()")

    # ---- 24. warujie.jp round 12 ----
    PRICE_SITE["dir"] = PRICES_ROLES
    DB_MODE["variant"] = "roles"
    page.set_viewport_size({"width": 1280, "height": 900})
    page.evaluate("localStorage.clear()")
    # Japanese shops: the Japan tab is one full-width column, one notice, every Japanese shop in one list
    page.goto(SITE + "?card=bolt-ja-m10"); page.wait_for_selector("#cardViewCard .shop-links")
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="jp"]')
    page.wait_for_function("document.querySelector('#cardViewCard .cp-market').dataset.market === 'jp'")
    jp = lambda: page.evaluate("[...document.querySelectorAll('#cardViewCard .jp-shop')].filter(a => a.offsetParent).map(a => [a.querySelector('.jp-name').textContent, (a.querySelector('.jp-alt') || {}).textContent || ''])")
    href = lambda name: page.locator("#cardViewCard .jp-shop", has=page.locator(".jp-name", has_text=name)).first.get_attribute("href")
    g = jp()
    check("JP tab: all 19 Japanese shops in one list, Japanese name first, English in grey", len(g) == 19 and [x[0] for x in g[:6]] == ["晴れる屋", "ビッグマジック", "カードラッシュ", "Tokyo MTG", "シングルスター", "カードショップ セラ"]
          and g[0][1] == "Hareruya" and dict(g)["ENNDAL GAMES"] == "", g)
    check("JP tab: the old link buttons and the listings column are gone", page.locator("#cardViewCard .shop-links").is_hidden() and page.locator("#offersBox").is_hidden()
          and page.locator("#cardViewCard .price-wip").count() == 0)
    mb, lb = page.locator("#cardViewCard .cp-market").bounding_box(), page.locator("#cardViewCard .jp-dir-list").bounding_box()
    xs = sorted(set(round(b["x"]) for b in [a.bounding_box() for a in page.locator("#cardViewCard .jp-shop").all()]))
    check("JP tab: the list takes the full width, three columns", abs(lb["width"] - mb["width"]) < 2 and len(xs) == 3, (mb, lb, xs))
    check("JP tab: no 'Load more' on a wide screen", page.locator("#cardViewCard .jp-dir-more").is_hidden())
    check("JP tab: each shop searches the card's Japanese name, in a new tab", href("シングルスター") == "https://www.singlestar.jp/product-list?keyword=%E7%A8%B2%E5%A6%BB"
          and href("カードショップ セラ") == "https://cardshop-serra.com/search?q=%E7%A8%B2%E5%A6%BB" and href("晴れる屋").startswith("https://www.hareruyamtg.com/ja/products/search?product=%E7%A8%B2%E5%A6%BB")
          and page.locator("#cardViewCard .jp-shop").first.get_attribute("target") == "_blank" and page.locator("#cardViewCard .jp-shop").first.get_attribute("rel") == "noopener", (href("シングルスター"), href("晴れる屋")))
    check("JP tab: a shop that only takes English names gets the English name", href("MTG Guild") == "https://mtg-guild.com/?mode=srh&keyword=Lightning%20Bolt", href("MTG Guild"))
    if SHOTS: page.locator("#cardViewCard .cp-market").screenshot(path="jp_dir.png")
    shown = lambda sel: page.evaluate(f"[...document.querySelectorAll('{sel}')].filter(a => a.offsetParent).map(a => a.textContent.replace('↗', '').trim())")
    for m, allowed in (("us", {"TCGplayer", "Card Kingdom", "Star City Games"}), ("eu", {"Cardmarket"})):
        page.click(f'#cardViewCard .price-tabs .seg-btn[data-pmarket="{m}"]')
        page.wait_for_function(f"document.querySelector('#cardViewCard .cp-market').dataset.market === '{m}'")
        row, above = shown("#cardViewCard .shop-links a"), shown("#cardViewCard .sp-shop a, #offersBox .of-shop a")
        check(f"{m.upper()} tab: 「ショップで探す」 only this market's shops not linked above (no Japanese ones), no Japanese list, listings back",
              set(row) <= allowed and not set(row) & set(above) and (m == "eu" or "Star City Games" in row) and page.locator("#cardViewCard .jp-dir").is_hidden()
              and page.locator("#offersBox").is_visible() and page.locator("#cardViewCard .jp-notice").count() == 0, (row, above))
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="jp"]')
    page.wait_for_function("document.querySelector('#cardViewCard .cp-market').dataset.market === 'jp'")
    page.goto(SITE + "?card=bolt-ja-m10"); page.wait_for_selector("#cardViewCard .jp-shop")
    check("JP tab: remembered, and the Japanese list with it", page.evaluate("document.querySelector('#cardViewCard .cp-market').dataset.market") == "jp" and len(jp()) == 19)
    # phone: eight shops, then "Load more"
    page.set_viewport_size({"width": 390, "height": 800}); page.wait_for_timeout(300)
    more = page.locator("#cardViewCard .jp-dir-more")
    xs = sorted(set(round(b["x"]) for b in [a.bounding_box() for a in page.locator("#cardViewCard .jp-shop:visible").all()]))
    check("phone: one column of eight shops, then 'Load more (11 more)'", len(jp()) == 8 and len(xs) == 1 and more.is_visible() and more.inner_text() == "さらに表示（残り11店）", (jp(), xs))
    hs = [a.bounding_box()["height"] for a in page.locator("#cardViewCard .jp-shop:visible").all()]
    check("phone: rows big enough to tap", min(hs) >= 44, hs)
    more.click(); page.wait_for_timeout(100)
    check("phone: 'Load more' shows the other 11 and goes away", len(jp()) == 19 and more.is_hidden())
    check("phone: no sideways scrolling", no_hscroll())
    nb = page.locator("#cardViewCard .jp-notice .wip-badge").bounding_box(); np_ = page.locator("#cardViewCard .jp-notice p").bounding_box()
    check("phone: the notice's badge sits above its text", np_["y"] >= nb["y"] + nb["height"] - 1, (nb, np_))
    if SHOTS: page.locator("#cardViewCard .cp-market").screenshot(path="jp_dir_phone.png")
    page.set_viewport_size({"width": 1280, "height": 900})
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="us"]')
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    page.goto(SITE + "?card=bolt-ja-m10"); page.wait_for_selector("#cardViewCard .shop-links")
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="jp"]'); page.wait_for_function("document.querySelector('#cardViewCard .cp-market').dataset.market === 'jp'")
    g = jp()
    check("English: English names first, the Japanese name in grey", g[0] == ["Hareruya", "晴れる屋"] and ["Single Star", "シングルスター"] in g and ["Tokyo MTG", ""] in g
          and "Japanese shop prices and stock" in page.locator("#cardViewCard .jp-notice").inner_text() and page.locator("#cardViewCard .jp-dir-head").inner_text().startswith("Find it in shops"), g)
    page.set_viewport_size({"width": 390, "height": 800}); page.wait_for_timeout(300)
    check("English phone: 'Load more (11 more)'", page.locator("#cardViewCard .jp-dir-more").inner_text() == "Load more (11 more)")
    page.set_viewport_size({"width": 1280, "height": 900})
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="us"]')
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'ja'")

    # the metagame and price tabs: one box that stays at the top
    for url, label in ((SITE + "?view=meta", "metagame"), (SITE + "?view=prices", "prices")):
        page.goto(url)
        view = "#metaView" if label == "metagame" else "#pricesView"
        bar = page.locator(f"{view} .meta-bar")
        if label == "metagame":
            page.wait_for_selector(f"{view} .meta-bar .result-count:not(:empty)")
            check(f"{label}: the header and its numbers in one box", bar.count() == 1 and bar.locator(".meta-head").count() == 1 and bar.locator(".result-count").count() == 1
                  and page.locator(f"{view} > .result-count").count() == 0)
        else:   # the owner moved the price movers' dates out of the box, so it is one row as tall as the deck price button
            page.wait_for_selector("#moverSummary:not(:empty)")
            check(f"{label}: the header box holds the toggles, the dates sit under it", bar.count() == 1 and bar.locator(".meta-head").count() == 1 and bar.locator(".result-count").count() == 0
                  and page.locator(f"{view} > #moverSummary").count() == 1)
        page.evaluate(f"document.querySelector('{view}').insertAdjacentHTML('beforeend', '<div class=test-spacer style=height:2400px></div>')")   # a long list, like the real data
        page.evaluate("window.scrollTo(0, 600)"); page.wait_for_timeout(250)
        tb = page.evaluate("document.querySelector('.topbar').getBoundingClientRect().bottom")
        bb = bar.bounding_box()
        check(f"{label}: the box stays just under the top bar when scrolling", abs(bb["y"] - tb) <= 2 and page.evaluate("scrollY") > 300, (bb, tb))
        if SHOTS: page.screenshot(path=f"sticky_{label}.png")
        page.set_viewport_size({"width": 390, "height": 800}); page.wait_for_timeout(300)
        page.evaluate("window.scrollTo(0, 900)"); page.wait_for_timeout(300)
        bb = bar.bounding_box()
        tb = page.evaluate("Math.max(0, document.querySelector('.topbar').getBoundingClientRect().bottom)")
        check(f"phone, {label}: the box stays under the top bar, short, and nothing scrolls sideways", abs(bb["y"] - tb) <= 2 and bb["height"] < 130 and no_hscroll(), (bb, tb))
        if SHOTS: page.screenshot(path=f"sticky_{label}_phone.png")
        page.set_viewport_size({"width": 1280, "height": 900})

    # home: the Try searches are in the 「効果の例」 box, with slang
    home()
    page.wait_for_selector("#hxList .hx-entry")
    check("home: no Try row under the search box", not page.locator("#heroTry").is_visible() and page.locator("#heroTry .try-pill").count() == 0)
    check("home: the effects box offers the old Try searches", page.evaluate("HERO_EFFECTS.some(f => f[0] === '飛行 絆魂') && HERO_EFFECTS.some(f => f[0] === '1枚捨てる') && HERO_SLANG.some(f => f[0] === '黒の除去') && HERO_SLANG.some(f => f[0] === 'サクり台')"))
    page.evaluate("Math.random = () => 0.01")   # slang first
    page.click("#hxNext")
    page.wait_for_function("document.querySelector('#hxList .hx-role')")
    ent = page.evaluate("[...document.querySelectorAll('#hxList .hx-entry')].map(e => [e.querySelector('.hx-effect').dataset.q, !!e.querySelector('.hx-role'), e.querySelector('.hx-name').childNodes[0].textContent, [...e.querySelectorAll('mark')].map(m => m.textContent)])")
    slang = [e for e in ent if e[1]]
    check("home: slang in the box, each with a card that does it and the words that do it highlighted", slang and all(e[3] for e in slang) and len(ent) == 3, ent)
    first = page.locator("#hxList .hx-entry").filter(has=page.locator(".hx-role")).first
    q = first.locator(".hx-effect").get_attribute("data-q")
    first.locator(".hx-effect").click(); page.wait_for_function(DONE)
    check("home: clicking slang searches it (as a role)", page.evaluate("document.getElementById('searchInput').value") == q and "役割" in note(), (q, note()))
    if SHOTS:
        home(); page.wait_for_selector("#hxList .hx-entry"); page.evaluate("Math.random = () => 0.01"); page.click("#hxNext"); page.wait_for_function("document.querySelector('#hxList .hx-role')")
        page.screenshot(path="home_effects.png")
    page.reload(); page.wait_for_selector("#hxList .hx-entry")
    seen = set()
    for _ in range(6):
        page.click("#hxNext"); page.wait_for_timeout(150); page.wait_for_selector("#hxList .hx-entry")
        seen.update(page.evaluate("[...document.querySelectorAll('#hxList .hx-effect')].map(b => b.dataset.q)"))
    check("home: shuffling gives different effects each time", len(seen) >= 6, seen)
    PRICE_SITE["dir"] = None
    DB_MODE["variant"] = None
    page.evaluate("localStorage.clear()")

    # ---- 26. round 14: order, recent searches, metagame trends, sample lists, export, app ----
    page.set_viewport_size({"width": 1280, "height": 900})
    home(); page.evaluate("localStorage.clear()"); home()
    check("search: the default order is called 'best match, A–Z', with 'most played' as a choice",
          page.evaluate("[...document.querySelectorAll('#sortSelect option')].map(o => [o.value, o.textContent])")[:2] == [["name", "一致・五十音順"], ["popular", "よく使われている順"]],
          page.evaluate("[...document.querySelectorAll('#sortSelect option')].map(o => [o.value, o.textContent])"))
    # recent searches
    for q in ("稲妻", "飛行", "稲妻"):
        top_search(q); page.wait_for_selector("#cardGrid .card-tile, #cardGrid .status-line"); page.wait_for_timeout(200)
    check("recent searches: kept in this browser, newest first, no repeats", page.evaluate("JSON.parse(localStorage.getItem('akuchie-recent'))") == ["稲妻", "飛行"],
          page.evaluate("localStorage.getItem('akuchie-recent')"))
    page.fill("#searchInput", ""); page.focus("#searchInput")
    page.wait_for_selector("#searchSuggest .recent-item")
    sug = page.locator("#searchSuggest")
    check("recent searches: an empty search box shows them, with a heading and 'clear'", sug.locator(".recent-item .s-main").all_inner_texts() == ["稲妻", "飛行"]
          and "最近の検索" in sug.inner_text() and sug.locator("[data-clear]").count() == 1, sug.inner_text())
    sug.locator(".recent-remove").first.click(); page.wait_for_timeout(100)
    check("recent searches: × takes one away (the box stays open)", sug.locator(".recent-item .s-main").all_inner_texts() == ["飛行"]
          and page.evaluate("JSON.parse(localStorage.getItem('akuchie-recent'))") == ["飛行"], sug.locator(".recent-item .s-main").all_inner_texts())
    sug.locator(".recent-item").first.click(); page.wait_for_function(DONE)
    check("recent searches: picking one searches it", page.evaluate("document.getElementById('searchInput').value") == "飛行" and len(names()) > 0)
    page.fill("#searchInput", ""); page.focus("#searchInput"); page.wait_for_selector("#searchSuggest .recent-item")
    page.click("#searchSuggest [data-clear]"); page.wait_for_timeout(100)
    check("recent searches: 'clear' forgets them all", page.evaluate("JSON.parse(localStorage.getItem('akuchie-recent'))") == [] and page.locator("#searchSuggest").is_hidden())
    page.locator("#searchInput").press_sequentially("ドロ"); page.wait_for_selector("#searchSuggest .role-suggest")
    check("recent searches: typing shows the usual suggestions again", page.locator("#searchSuggest .recent-item").count() == 0)
    page.keyboard.press("Escape")
    check("footer: the privacy note says recent searches stay in the browser", "最近の検索" in page.locator("footer").inner_text())
    # metagame trends
    META_MODE["mode"] = "fixture"
    DECKS_MODE["mode"] = "fixture"
    page.goto(SITE + "?view=meta&format=standard&days=30"); page.wait_for_selector("#metaBody .meta-row")
    rows = page.locator("#metaBody .meta-row")
    gr = rows.nth(0)
    check("metagame: each deck has a small 12-week line and how much it moved in four weeks", gr.locator(".meta-trend svg.spark path").count() == 1
          and gr.locator(".trend-d.up").inner_text() == "▲3.5pt" and "28.0%" in gr.locator(".meta-trend").get_attribute("title"),
          (gr.locator(".meta-trend").inner_html() if gr.locator(".meta-trend").count() else None))
    check("metagame: a falling deck shows ▼", rows.nth(2).locator(".trend-d.down").inner_text() == "▼2.5pt", rows.nth(2).locator(".meta-trend").inner_html())
    page.select_option("#metaSort", "trend"); page.wait_for_timeout(200)
    order = page.locator("#metaBody .meta-row .meta-name-text").all_inner_texts()
    check("metagame: 'rising' puts the fastest-growing deck first", order[:2] == ["Selesnya Cats", "グルール・ドラゴン"] and order[-1] == "赤単バーン", order)
    page.select_option("#metaSort", "share"); page.wait_for_timeout(100)
    if SHOTS: page.locator("#metaBody").screenshot(path="meta_trends.png")
    # the deck page: trend chart, sample lists, export
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Gruul%20Dragons"); page.wait_for_selector("#deckBody .deck-trend")
    tr = page.locator("#deckBody .deck-trend")
    check("deck page: the share over time, one point a week (no point for a week without events)", tr.locator("circle.td").count() == 11
          and "使用率の推移" in tr.locator("h2").inner_text() and "▲3.5pt" in tr.locator("h2").inner_text(), tr.inner_html()[:300])
    sel = page.locator("#deckListSel")
    check("deck page: several sample lists to choose from", sel.locator("option").count() == 2 and "1. 1st Place・Big Open" in sel.locator("option").first.inner_text()
          and "2件" in page.locator(".deck-pick").inner_text(), page.locator(".deck-pick").inner_text())
    page.select_option("#deckListSel", "1")
    page.wait_for_function("document.querySelector('#deckBody .deck-src-link') && document.querySelector('#deckBody .deck-src-link').href.endsWith('/def')")
    main = page.locator("#deckBody .deck-section").first
    check("deck page: choosing another list shows its cards and its source, and the address remembers it",
          "2nd Place" in chosen() and "list=1" in page.url and "メインデッキ60枚" in main.locator("h2").inner_text().replace("\n", ""),
          (page.url, main.locator("h2").inner_text()))
    check("deck page: 'other popular cards' leaves out what this list already plays", "English Only Thing" not in page.locator("#deckBody").inner_text().split("ほかによく使われるカード")[-1] if "ほかによく使われるカード" in page.locator("#deckBody").inner_text() else True)
    page.click("#deckExport summary"); page.click("#deckExport [data-export=arena]")
    page.wait_for_function("document.querySelector('#deckExport [data-export=arena]').textContent === 'コピーしました'")
    clip = page.evaluate("navigator.clipboard.readText()")
    check("deck page: export copies the list being shown", clip == "Deck\n4 Shivan Dragon\n4 Lightning Bolt\n4 English Only Thing\n24 Mountain\n24 Forest\n\nSideboard\n4 Qasali Pridemage\n", clip)
    page.wait_for_timeout(1300)
    page.click("#deckExport summary")
    with page.expect_download() as dl:
        page.click("#deckExport [data-export=file]")
    f = dl.value
    body = open(f.path(), "rb").read().decode("utf-8")
    check("deck page: the MTGO file (.txt, Windows line ends, sideboard after a blank line)", f.suggested_filename == "Gruul Dragons.txt"
          and body == "4 Shivan Dragon\r\n4 Lightning Bolt\r\n4 English Only Thing\r\n24 Mountain\r\n24 Forest\r\n\r\n4 Qasali Pridemage\r\n", (f.suggested_filename, body))
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Gruul%20Dragons&list=1"); page.wait_for_selector("#deckBody .deck-src-link")
    check("deck page: a link with list=1 opens that list", page.locator(".deck-src-link").get_attribute("href").endswith("/def") and page.locator("#deckListSel").input_value() == "1")
    if SHOTS: page.screenshot(path="deck_lists.png", full_page=True)
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Orzhov&u=1"); page.wait_for_selector("#deckBody .deck-group")
    check("deck page: a deck with one list has no list picker", page.locator("#deckListSel").count() == 0 and page.locator("#deckExport").count() == 1)
    # the app and the share tags
    head = page.evaluate("""() => ({ manifest: !!document.querySelector('link[rel=manifest]'), icon: !!document.querySelector('link[rel=icon]'),
        apple: !!document.querySelector('link[rel=apple-touch-icon]'), og: document.querySelector('meta[property="og:image"]').content,
        card: document.querySelector('meta[name="twitter:card"]').content, theme: document.querySelector('meta[name=theme-color]').content })""")
    check("app: manifest, icons and share tags in the page", head == {"manifest": True, "icon": True, "apple": True, "og": "https://warujie.jp/og.png", "card": "summary_large_image", "theme": "#121214"}, head)
    check("app: the install button stays hidden where the browser offers no install", page.locator("#appInstall").is_hidden())
    page.evaluate("localStorage.clear()")

    # ---- 27. round 15: names without punctuation; 日本語版 / 英語版 on the card page ----
    page.set_viewport_size({"width": 1280, "height": 900})
    DB_MODE["variant"] = None
    home(); page.evaluate("localStorage.clear()")
    page.fill("#heroInput", ""); page.focus("#heroInput"); page.locator("#heroInput").press_sequentially("Ragavan Nimble")
    page.wait_for_selector("#heroSuggest .suggest-item:not(.recent-item)")
    first = page.locator("#heroSuggest .suggest-item").first
    check("suggestions: a name typed without its comma (Ragavan Nimble -> Ragavan, Nimble Pilferer)", "敏捷なこそ泥、ラガバン" in first.inner_text()
          and first.locator("b").count() <= 1, page.locator("#heroSuggest").inner_text())
    page.fill("#heroInput", ""); page.locator("#heroInput").press_sequentially("敏捷なこそ泥ラガバン")
    page.wait_for_function("document.querySelector('#heroSuggest .s-main') && document.querySelector('#heroSuggest .s-main').textContent.includes('ラガバン')")
    check("suggestions: a Japanese name typed without its 、", page.locator("#heroSuggest .s-main").first.inner_text() == "敏捷なこそ泥、ラガバン"
          and page.locator("#heroSuggest .s-main b").first.inner_text() == "敏捷なこそ泥、ラガバン", page.locator("#heroSuggest").inner_html()[:300])
    page.fill("#heroInput", ""); page.locator("#heroInput").press_sequentially("urzas saga")
    page.wait_for_function("document.querySelector('#heroSuggest .s-main') && document.querySelector('#heroSuggest').textContent.includes('ウルザの物語')")
    check("suggestions: an apostrophe left out (urzas saga -> Urza's Saga)", "ウルザの物語" in page.locator("#heroSuggest .s-main").first.inner_text())
    page.keyboard.press("Escape")
    top_search("Ragavan Nimble Pilferer"); page.wait_for_selector("#cardGrid .card-tile")
    check("search: the whole name without its comma finds the card first", page.locator("#cardGrid .card-name-main").first.inner_text() == "敏捷なこそ泥、ラガバン",
          page.locator("#cardGrid .card-name-main").all_inner_texts())
    # ---- 28. round 16: language buttons under the picture, the same printing in each language ----
    page.goto(SITE + "?card=rag-ja-mh2"); page.wait_for_selector("#printSlot .print-lang")
    labels = page.locator("#printSlot .print-lang").all_inner_texts()
    check("card page: one button per language of this printing, JP first (JP EN FR DE)", labels == ["JP", "EN", "FR", "DE"], labels)
    check("card page: the buttons sit under the picture, not in the info column", page.locator(".cp-art #printSlot").count() == 1
          and page.locator(".cp-meta .print-lang").count() == 0)
    sizes = page.evaluate("[...document.querySelectorAll('#printSlot .print-lang')].map(b => [Math.round(b.getBoundingClientRect().width), Math.round(b.getBoundingClientRect().height)])")
    check("card page: language buttons all the same size", len(set(map(tuple, sizes))) == 1 and sizes[0][0] <= 44, sizes)
    check("card page: the printing shown is pressed", page.locator("#printSlot [aria-pressed=true]").inner_text() == "JP")
    ids = page.evaluate("Object.fromEntries([...document.querySelectorAll('#printSlot .print-lang')].map(b => [b.dataset.print, b.dataset.id]))")
    check("card page: every button is the same set and number (no jump to another set)", ids == {"ja": "rag-ja-mh2", "en": "rag-en-mh2", "fr": "rag-fr-mh2", "de": "rag-de-mh2"}, ids)
    check("card page: button names the language for screen readers", page.locator("#printSlot [data-print=fr]").get_attribute("aria-label") == "フランス語")
    page.click("#printSlot [data-print=en]")
    page.wait_for_function("location.search.includes('card=rag-en-mh2') && location.search.includes('print=en')")
    page.wait_for_selector("#printSlot [data-print=en][aria-pressed=true]")
    check("card page: EN shows the English printing in English (name, type, text)", page.locator(".cp-name").inner_text() == "Ragavan, Nimble Pilferer"
          and page.locator(".cp-name-sub").inner_text() == "敏捷なこそ泥、ラガバン" and "Treasure" in page.locator(".cp-text").inner_text(),
          (page.locator(".cp-name").inner_text(), page.locator(".cp-text").inner_text()))
    page.click("#printSlot [data-print=fr]")
    page.wait_for_function("location.search.includes('card=rag-fr-mh2') && location.search.includes('print=fr')")
    page.wait_for_selector("#printSlot [data-print=fr][aria-pressed=true]")
    check("card page: FR shows the French printing in French, the English name beside it", page.locator(".cp-name").inner_text() == "Ragavan, chapardeur agile"
          and page.locator(".cp-name-sub").inner_text() == "Ragavan, Nimble Pilferer" and "Trésor" in page.locator(".cp-text").inner_text()
          and "rag-fr-mh2.jpg" in (page.locator(".cp-art img").first.get_attribute("src") or ""),
          (page.locator(".cp-name").inner_text(), page.locator(".cp-name-sub").inner_text(), page.locator(".cp-art img").first.get_attribute("src")))
    page.click("#printSlot [data-print=ja]")
    page.wait_for_function("location.search.includes('card=rag-ja-mh2') && location.search.includes('print=ja')")
    page.wait_for_selector("#printSlot [data-print=ja][aria-pressed=true]")
    check("card page: JP goes back to the Japanese printing in Japanese", page.locator(".cp-name").inner_text() == "敏捷なこそ泥、ラガバン"
          and "宝物・トークン" in page.locator(".cp-text").inner_text())
    page.go_back(); page.wait_for_function("location.search.includes('card=rag-fr-mh2')"); page.wait_for_selector("#printSlot [data-print=fr][aria-pressed=true]")
    check("card page: back returns to the French printing", page.locator(".cp-name").inner_text() == "Ragavan, chapardeur agile")
    page.goto(SITE + "?card=rag-en-mh2-bl"); page.wait_for_selector("#printSlot .print-lang")
    page.wait_for_timeout(200)
    check("card page: a printing that exists only in English shows EN alone (no jump to another set's Japanese)",
          page.locator("#printSlot .print-lang").all_inner_texts() == ["EN"] and page.locator("#printSlot [data-id=rag-ja-mh2]").count() == 0,
          page.locator("#printSlot").inner_html())
    page.goto(SITE + "?card=rag-ja-mul"); page.wait_for_selector("#printSlot .print-lang")
    ids = page.evaluate("Object.fromEntries([...document.querySelectorAll('#printSlot .print-lang')].map(b => [b.dataset.print, b.dataset.id]))")
    check("card page: another set gets its own counterparts", ids == {"ja": "rag-ja-mul", "en": "rag-en-mul", "fr": "rag-fr-mul"}, ids)
    page.goto(SITE + "?card=eo-1"); page.wait_for_selector(".cp-name"); page.wait_for_timeout(300)
    check("card page: an English-only card shows only EN", page.locator("#printSlot .print-lang").all_inner_texts() in (["EN"], []), page.locator("#printSlot").inner_html())
    page.goto(SITE + "?card=rag-ja-mh2"); page.wait_for_selector(".cp-name")
    check("card page: without a choice, the page follows the site language as before", page.locator(".cp-name").inner_text() == "敏捷なこそ泥、ラガバン")
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(200)
    row = page.evaluate("(() => { const r = document.querySelector('#printSlot .print-langs').getBoundingClientRect(); const a = document.querySelector('.cp-art img').getBoundingClientRect(); return [r.top >= a.bottom - 1, r.right <= innerWidth]; })()")
    check("card page (phone): the buttons sit under the picture, inside the screen", row == [True, True], row)
    page.set_viewport_size({"width": 1280, "height": 900})

    # ---- 29. round 17: counterparts across the old split set codes; Japanese face names ----
    page.goto(SITE + "?card=arma-ja-4bb"); page.wait_for_selector("#printSlot .print-lang")
    ids = page.evaluate("Object.fromEntries([...document.querySelectorAll('#printSlot .print-lang')].map(b => [b.dataset.print, b.dataset.id]))")
    check("4th Edition (Japanese, 4bb): EN is the English 4th Edition (4ed), never Masters 25", ids == {"ja": "arma-ja-4bb", "en": "arma-en-4ed", "de": "arma-de-4bb"}, ids)
    page.click("#printSlot [data-print=en]")
    page.wait_for_function("location.search.includes('card=arma-en-4ed')"); page.wait_for_selector("#printSlot [data-print=en][aria-pressed=true]")
    ids = page.evaluate("Object.fromEntries([...document.querySelectorAll('#printSlot .print-lang')].map(b => [b.dataset.print, b.dataset.id]))")
    check("4th Edition (English, 4ed): JP goes back to the Japanese 4th Edition", ids == {"ja": "arma-ja-4bb", "en": "arma-en-4ed", "de": "arma-de-4bb"}, ids)
    page.goto(SITE + "?card=arma-en-a25"); page.wait_for_selector("#printSlot .print-lang"); page.wait_for_timeout(200)
    check("Masters 25 (English only): EN alone", page.locator("#printSlot .print-lang").all_inner_texts() == ["EN"], page.locator("#printSlot").inner_html())
    names = page.evaluate("""(() => {
      const c = { id: 'x', oracle_id: 'cove-oracle', lang: 'ja', name: 'Spellscorn Coven // Take It Back',
        card_faces: [{ name: 'Spellscorn Coven', printed_name: 'Spellscorn Coven' }, { name: 'Take It Back', printed_name: 'お返（かえ）し' }] };
      const before = displayNameJa(c);
      ORACLE_MAP.set('cove-oracle', { oracle_id: 'cove-oracle', name_en: 'Spellscorn Coven // Take It Back', name_ja: '呪文嘲りの集会 // お返し' });
      const after = displayNameJa(c), front = japaneseFrontName(c);
      const sos = { id: 'y', oracle_id: 'cove-oracle', lang: 'ja', card_faces: [{ name: 'Spellscorn Coven', printed_name: '呪文嘲りの集会' }, { name: 'Take It Back' }] };
      const r = [before, after, front, displayNameJa(sos)];
      ORACLE_MAP.delete('cove-oracle');
      return r;
    })()""")
    check("two-part card: an English face name in Scryfall's Japanese data is replaced by the database's Japanese name",
          names == ["Spellscorn Coven // お返し", "呪文嘲りの集会 // お返し", "呪文嘲りの集会", "呪文嘲りの集会 // お返し"], names)
    page.goto(SITE + "?card=cove-ja-woe"); page.wait_for_selector(".cp-name")
    check("two-part card page without a database name keeps what Scryfall has", page.locator(".cp-name").inner_text() == "Spellscorn Coven // お返し",
          page.locator(".cp-name").inner_text())

    # ---- 30. round 18: the language buttons survive the English picture swap ----
    page.goto(SITE + "?card=bolt-ja-m10"); page.wait_for_selector(".cp-img-note"); page.wait_for_selector("#printSlot .print-lang"); page.wait_for_timeout(400)
    check("placeholder Japanese printing: English picture, and the language buttons are still there",
          page.locator("#printSlot .print-lang").all_inner_texts() == ["JP", "EN", "IT"] and "/large/bolt-en-m10" in page.locator(".cp-art img").first.get_attribute("src"),
          (page.locator("#printSlot").inner_html()[:200], page.locator(".cp-art img").first.get_attribute("src")))
    page.click("#printSlot [data-print=it]")
    page.wait_for_function("location.search.includes('card=bolt-it-m10')"); page.wait_for_selector(".cp-img-note"); page.wait_for_timeout(400)
    check("Italian placeholder printing: still all buttons, IT pressed, the note names Italian",
          page.locator("#printSlot .print-lang").all_inner_texts() == ["JP", "EN", "IT"] and page.locator("#printSlot [aria-pressed=true]").inner_text() == "IT"
          and "イタリア語版の画像" in page.locator(".cp-img-note").inner_text() and page.locator(".cp-name").inner_text() == "Fulmine",
          (page.locator("#printSlot").inner_html()[:200], page.locator(".cp-img-note").inner_text()))
    page.click("#printSlot [data-print=ja]")
    page.wait_for_function("location.search.includes('card=bolt-ja-m10')"); page.wait_for_selector(".cp-img-note"); page.wait_for_timeout(400)
    check("back to Japanese: buttons still there, the note names Japanese", page.locator("#printSlot .print-lang").count() == 3
          and "日本語版の画像" in page.locator(".cp-img-note").inner_text(), page.locator("#printSlot").inner_html()[:200])

    # ---- 31. round 19: slang and everyday wording in the search box ----
    sl = page.evaluate("""(() => {
      const alt = q => { const u = prepareJapanese([q])[0]; return [u.alts.map(f => f.n), u.alias ? u.alias.to : null, u.kw]; };
      const roles = q => { const f = findRoleWords(tokenizeQuery(q)); return [f.roles.map(r => r.id), f.quotedRoles.map(r => r.id + '>' + r.word), f.derived.map(d => d.label)]; };
      const ps = q => { const r = parseSearch(q); return [r.words, r.filters.length, r.aliases.map(a => a.from + '>' + a.to)]; };
      return {
        deck: alt('山札の上'), dmg: alt('3ダメージ'), draw: alt('2ドロー'), toki: alt('戦場に出た時'), all: alt('全てのクリーチャー'),
        fly: alt('飛行持ち'), flyer: alt('フライヤー'), sac: alt('サクる'), mine: alt('自分のクリーチャー'), attack: alt('攻撃したとき'), plain: alt('飛行'),
        dot: [normJaSearch('宝物・トークン'), normJaSearch('宝物トークン')], split: prepareJapanese(['墓地から手札'])[0].chunks, karakuri: prepareJapanese(['からくり'])[0].chunks,
        counter: roles('カウンター'), blueCounter: roles('青のカウンター'), lord: roles('ロード'), sure: roles('確定除去'), etbc: roles('ETBクリーチャー'),
        etbm: roles('ETB持ち'), cheap: roles('軽量除去'), pw: roles('PW除去'), quoted: roles('"ランプ"'),
        unbl: ps('unblockable'), pwType: ps('PW'), sacEn: ps('sac'),
        sugg: roleSuggestions('ロー').map(s => s.word), rq: [roleQuery('lord'), roleQuery('counterspell')],
      };
    })()""")
    check("slang: 山札/トップ = ライブラリーの一番上", sl["deck"][0] == ["ライブラリーの一番上"], sl["deck"])
    check("slang: 3ダメージ = 3点のダメージ (with a note), 2ドロー = カードを2枚引く", sl["dmg"][0] == ["3点のダメージ"] and sl["dmg"][1] == "3点のダメージ" and sl["draw"][0] == ["カードを2つ引く"], (sl["dmg"], sl["draw"]))
    check("spelling: 出た時 = 出たとき, 全て = すべて (no note)", sl["toki"][0] == ["戦場に出たとき"] and sl["toki"][1] is None and sl["all"][0] == ["すべてのクリーチャー"] and sl["all"][1] is None, (sl["toki"], sl["all"]))
    check("keywords: 飛行持ち and フライヤー = 飛行 (flying)", sl["fly"][2] == "flying" and sl["flyer"][2] == "flying" and sl["plain"][0] == [], (sl["fly"], sl["flyer"], sl["plain"]))
    check("slang: サクる, 自分のクリーチャー, 攻撃したとき", sl["sac"][0] == ["生け贄に捧げ"] and sl["mine"][0] == ["あなたがコントロールするクリーチャー"] and sl["attack"][0] == ["攻撃するたび"], (sl["sac"], sl["mine"], sl["attack"]))
    check("・ is ignored in text: 宝物・トークン = 宝物トークン", sl["dot"][0] == sl["dot"][1] == "宝物トークン", sl["dot"])
    check("から splits a phrase (墓地から手札), not a word (からくり)", sl["split"] == ["墓地", "手札"] and sl["karakuri"] == ["からくり"], (sl["split"], sl["karakuri"]))
    check("カウンター alone: text, with 打ち消し offered; 青のカウンター: blue counterspells", sl["counter"][0] == [] and sl["counter"][1] == ["counterspell>打ち消し"]
          and sl["blueCounter"][0] == ["counterspell"] and sl["blueCounter"][2] == ["青"], (sl["counter"], sl["blueCounter"]))
    check("ロード alone: names, with the lord role offered as 部族ロード", sl["lord"][0] == [] and sl["lord"][1] == ["lord>部族ロード"] and sl["rq"] == ["部族ロード", "打ち消し"], (sl["lord"], sl["rq"]))
    check("new roles: 確定除去, PW除去; ETBクリーチャー = ETB + creatures; ETB持ち; 軽量除去 = 2 mana or less",
          sl["sure"][0] == ["sure-removal"] and sl["pw"][0] == ["pw-removal"] and sl["etbc"][0] == ["etb"] and sl["etbc"][2] == ["クリーチャー"]
          and sl["etbm"][0] == ["etb"] and sl["cheap"][0] == ["removal"] and len(sl["cheap"][2]) == 1, (sl["sure"], sl["etbc"], sl["etbm"], sl["cheap"]))
    check("a quoted role word is still offered as before", sl["quoted"][0] == [] and sl["quoted"][1] == ["ramp>ランプ"], sl["quoted"])
    check("English: unblockable = can't be blocked, sac = sacrifice; PW = planeswalkers (a filter)",
          sl["unbl"][0] == ["can't", "be", "blocked"] and sl["sacEn"][0] == ["sacrifice"] and sl["pwType"][1] == 1 and sl["pwType"][2] == ["PW>プレインズウォーカー"], (sl["unbl"], sl["sacEn"], sl["pwType"]))
    check("suggestions never offer an ambiguous word as a role (ロー -> not ロード)", "ロード" not in sl["sugg"], sl["sugg"])
    run("3ダメージ")
    check("the note says what the slang was read as", "「3ダメージ」は「3点のダメージ」としても検索しました" in page.locator("#matchNote").inner_text()
          and "稲妻" in page.locator("#cardGrid").inner_text(), page.locator("#matchNote").inner_text())
    run("カウンター")
    check("カウンター without the role data: searched as text, nothing offered", "役割" not in page.locator("#matchNote").inner_text(), page.locator("#matchNote").inner_text())

    # ---- 32. round 20: metagame tab - Japanese deck names, short rows on phones, notes ----
    page.set_viewport_size({"width": 1280, "height": 900})
    names = page.evaluate("""['Dimir Midrange', 'Mono Red Burn', 'Mono Green Landfall', '5 Color Creativity', 'WUBR Midrange', 'Selesnya Cats', 'Living End', 'Boros', 'Izzet Spellementals'].map(deckNameJa)""")
    check("deck names in Japanese: guild + deck word, mono colours, whole names; unknown words keep the English",
          names == ["ディミーア・ミッドレンジ", "赤単バーン", "緑単上陸", "5色独創力", "WUBR・ミッドレンジ", "", "死せる生", "ボロス", "イゼット・スペルメンタル"], names)
    page.goto(SITE + "?view=meta&format=standard"); page.wait_for_selector("#metaBody .meta-row")
    shown = page.locator("#metaBody .meta-name-text").all_inner_texts()
    check("metagame: deck names in Japanese, English kept where there is no Japanese", shown == ["グルール・ドラゴン", "Selesnya Cats", "赤単バーン", "オルゾフ（未分類）"], shown)
    rows = page.locator("#metaBody .meta-row")
    check("metagame: the English name sits small next to the Japanese one", rows.nth(0).locator(".meta-name-en").inner_text() == "Gruul Dragons"
          and rows.nth(1).locator(".meta-name-en").count() == 0)
    check("metagame: no note when most decks have a win rate", page.locator("#metaBody .meta-hint").count() == 0)
    page.locator("#metaFormats .seg-btn[data-format=modern]").click(); page.wait_for_selector("#metaBody .meta-row")
    hint = page.locator("#metaBody .meta-hint")
    check("metagame: few win rates -> a note says why (no other period has more, so no button)", hint.count() == 1 and "30試合以上" in hint.inner_text()
          and "1デッキ中0" in hint.inner_text() and hint.locator("button").count() == 0, hint.inner_text() if hint.count() else None)
    page.locator("#metaFormats .seg-btn[data-format=standard]").click(); page.wait_for_selector("#metaBody .meta-row")
    page.evaluate("metaState.data.windows['30'].formats.standard.archetypes.forEach(a => { a.wins = 5; a.losses = 5; }); renderMeta()")
    btn = page.locator("#metaBody .meta-hint .meta-hint-btn")
    check("metagame: …and offers the period with more win rates", btn.count() == 1 and btn.inner_text() == "直近90日で見ると2デッキに増えます →", btn.inner_text() if btn.count() else None)
    btn.click(); page.wait_for_timeout(200)
    check("metagame: the note's button switches to that period", "days=90" in page.url and page.get_attribute("#metaWindows .seg-btn[data-days='90']", "aria-pressed") == "true"
          and page.locator("#metaBody .meta-hint").count() == 0, page.url)
    check("metagame: the 見方 box starts closed", page.locator("#metaHelp").is_hidden())
    page.click("#metaHelpBtn")
    check("metagame: 見方 explains share, ▲▼, win rate and its line", page.locator("#metaHelp").is_visible() and "信頼区間" in page.locator("#metaHelp").inner_text()
          and "4週" in page.locator("#metaHelp").inner_text() and page.get_attribute("#metaHelpBtn", "aria-expanded") == "true")
    page.click("#metaHelpBtn")
    check("metagame: …and closes again", page.locator("#metaHelp").is_hidden())
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(SITE + "?view=meta&format=standard"); page.wait_for_selector("#metaBody .meta-row"); page.wait_for_timeout(200)
    hs = page.evaluate("[...document.querySelectorAll('#metaBody .meta-row')].map(r => Math.round(r.getBoundingClientRect().height))")
    check("phone, metagame: each deck is one short row", all(h <= 72 for h in hs), hs)
    first = page.locator("#metaBody .meta-row").first
    check("phone, metagame: key cards and bars stay hidden until the row is opened", first.locator(".meta-cards").is_hidden() and first.locator(".bar-track").is_hidden()
          and first.locator(".meta-num").first.is_visible())
    first.locator(".meta-toggle").click()
    check("phone, metagame: the ▾ opens the row (cards, bars, sample)", "open" in first.get_attribute("class") and first.locator(".meta-cards").is_visible()
          and first.locator(".bar-track").is_visible() and first.locator(".meta-toggle").get_attribute("aria-expanded") == "true")
    page.locator("#metaBody .meta-row").nth(2).locator(".meta-share").click()
    check("phone, metagame: tapping anywhere on a row opens it too", "open" in page.locator("#metaBody .meta-row").nth(2).get_attribute("class"))
    first.locator(".meta-toggle").click()
    check("phone, metagame: …and closes it", "open" not in first.get_attribute("class"))
    ctl = page.evaluate("['#metaWindows', '#metaSort', '#metaHelpBtn'].map(s => Math.round(document.querySelector(s).getBoundingClientRect().right))")
    check("phone, metagame: period, sort and 見方 are all on screen", all(r <= 390 for r in ctl) and no_hscroll(), ctl)
    first.locator("a.meta-name-text").click(); page.wait_for_selector("#deckBody .deck-group")
    check("phone, metagame: the deck name still opens the deck page; its title is Japanese with the English below",
          "view=deck" in page.url and page.locator(".deck-title").inner_text().startswith("グルール・ドラゴン") and page.locator(".deck-title-en").inner_text() == "Gruul Dragons")
    page.set_viewport_size({"width": 1280, "height": 900})

    # ---- 33. round 21: what a deck costs - cheapest printings in yen, 安い順, Arena wildcards, mana curve ----
    PRICE_SITE["dir"] = PRICES_FULL
    DECKS_MODE["mode"] = "fixture"
    cheap = json.loads(gzip.decompress(open(os.path.join(PRICES_FULL, "cheap.json.gz"), "rb").read()))["cards"]
    check("prices: the builder writes each card's cheapest price and Arena rarity", "Lightning Bolt" in cheap and len(cheap["Lightning Bolt"]) == 3, cheap.get("Lightning Bolt"))
    gruul = [(4, "Shivan Dragon"), (4, "Llanowar Elves"), (4, "Ragavan, Nimble Pilferer"), (4, "Lightning Bolt"), (4, "Urza's Saga"), (2, "Unknown New Card"),
             (3, "Qasali Pridemage"), (2, "Deathrite Shaman")]   # Mountain and Forest are basic lands: left out
    want, gone = 0.0, 0
    for n, name in gruul:
        r = cheap.get(name)
        opts = [x for x in ((r[0] / 100 * 150.0) if r and r[0] else None, (r[1] / 100 * 160.0) if r and r[1] else None) if x is not None]
        if opts: want += n * min(opts)
        else: gone += n
    want_txt = "約¥{:,}".format(int(round(round(want) / 100) * 100)) + ("〜" if gone else "")
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Gruul%20Dragons"); page.wait_for_selector("#deckBody .deck-group")
    page.wait_for_function("document.querySelector('.deck-cost .dcst-v')")
    cost_box = page.locator(".deck-cost").inner_text()
    check("deck page: what the deck costs, from each card's cheapest printing (US or EU, whichever is lower), basic lands left out",
          page.locator(".deck-cost .dcst-v").inner_text() == want_txt and ("価格のないカード{}枚を除く".format(gone) in cost_box if gone else "除く" not in cost_box), (cost_box, want_txt, gone))
    check("deck page: the mana curve counts the main deck without lands (12 one-drops, 4 at 6+)",
          page.locator(".cv-col").count() == 7 and page.locator(".cv-col").nth(1).locator(".cv-n").inner_text() == "12"
          and page.locator(".cv-col").nth(6).locator(".cv-n").inner_text() == "4", page.locator(".cv").inner_text())
    check("deck page: no Arena wildcards when some cards aren't on Arena", page.locator(".deck-cost .wcs").count() == 0)
    check("deck page: how the price is worked out is explained", "いちばん安い版" in page.locator(".deck-cost-note").inner_text())
    page.click("[data-dview=list]"); page.wait_for_selector("#deckBody .dl-row")
    bolt = page.locator("#deckBody .dl-row", has=page.locator(".dl-name", has_text="稲妻")).first
    r = cheap["Lightning Bolt"]; one = min(x for x in ((r[0] / 100 * 150.0) if r[0] else None, (r[1] / 100 * 160.0) if r[1] else None) if x is not None)
    check("deck page, list: each card's price for one copy", bolt.locator(".dl-yen").inner_text() == "¥{:,}".format(max(1, int(round(one))) if one < 1000 else int(round(one / 10) * 10)),
          (bolt.locator(".dl-yen").inner_text(), one))
    page.click("[data-dview=image]")
    wc = page.evaluate("""(() => { const keep = cheapStore.data; cheapStore.data = { cards: { 'Lightning Bolt': [100, 100, 'c'], 'Shivan Dragon': [200, null, 'r'], 'Llanowar Elves': [50, 50, 'u'], 'Ragavan, Nimble Pilferer': [5000, 4000, 'm'] } };
        const c = deckCost([[4, 'Lightning Bolt'], [3, 'Shivan Dragon'], [4, 'Llanowar Elves'], [1, 'Ragavan, Nimble Pilferer'], [20, 'Mountain']]);
        const html = wildcardsHtml(c, 'standard'), modern = wildcardsHtml(c, 'modern'), pioneer = wildcardsHtml(c, 'pioneer'); cheapStore.data = keep; return [c.wc, c.yen, html.includes('wc-m'), modern, pioneer.includes('wc-m')]; })()""")
    check("deck cost: Arena wildcards by rarity, basic lands left out; for Standard and Pioneer, not Modern",
          wc[0] == {"m": 1, "r": 3, "u": 4, "c": 4} and wc[1] == round(4 * 150 + 3 * 300 + 4 * 75 + 1 * min(7500, 6400)) and wc[2] and wc[3] == "" and wc[4], wc)
    page.goto(SITE + "?view=meta&format=standard"); page.wait_for_selector("#metaBody .meta-row")
    page.wait_for_function("document.querySelector('#metaBody .meta-cost')")
    gr = page.locator("#metaBody .meta-row").first
    col_txt = want_txt.replace("約", "").replace("〜", "+")
    check("metagame: each deck with a priced list shows its price in the price column (Orzhov's only card has no price: none shown)",
          gr.locator(".meta-price .meta-cost").inner_text() == col_txt and page.locator("#metaBody .meta-cost").count() == 1,
          (gr.locator(".meta-cost").inner_text(), col_txt))
    page.select_option("#metaSort", "cost"); page.wait_for_timeout(200)
    order = page.locator("#metaBody .meta-name-text").all_inner_texts()
    costs_shown = page.evaluate("[...document.querySelectorAll('#metaBody .meta-row')].map(r => { const c = r.querySelector('.meta-cost'); return c ? Number(c.textContent.replace(/[^0-9]/g, '')) : null; })")
    priced = [c for c in costs_shown if c is not None]
    check("metagame: 安い順 puts the cheapest deck first, decks without a price last (in share order)",
          priced == sorted(priced) and costs_shown[:len(priced)] == priced and order[len(priced):] == ["Selesnya Cats", "赤単バーン", "オルゾフ（未分類）"], (order, costs_shown))
    page.select_option("#metaSort", "share")
    PRICE_SITE["dir"] = None
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Gruul%20Dragons"); page.wait_for_selector("#deckBody .deck-group")
    page.wait_for_function("document.querySelector('.deck-cost') && document.querySelector('.deck-cost').textContent.includes('読み込めませんでした')")
    check("deck page: without the price file it says so, and the mana curve is still there", page.locator(".cv-col").count() == 7)

    # ---- 34. round 22: smaller price box, curve under the list, picker that stays, short names and rank arrows ----
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Gruul%20Dragons"); page.wait_for_selector("#deckBody .deck-group")
    page.wait_for_function("document.querySelector('.deck-cost') && !document.querySelector('.deck-cost').textContent.includes('読み込み中')")
    check("deck page: the price box is called 価格", page.locator(".deck-cost .dcst-l").first.inner_text() == "価格", page.locator(".deck-cost").inner_text())
    wc = page.evaluate("wildcardsHtml({ wc: { m: 1, r: 2, u: 3, c: 4 } }, 'standard')")
    wc_text = page.evaluate("(() => { const d = document.createElement('div'); d.innerHTML = wildcardsHtml({ wc: { m: 1, r: 2, u: 3, c: 4 } }, 'standard'); return d.textContent; })()")
    check("Arena wildcards: only the counts show, the rarity names are tooltips", 'title="神話レア"' in wc and wc_text == "1234", (wc, wc_text))
    secs = page.evaluate("[...document.querySelectorAll('#deckBody > *')].map(e => e.classList.contains('deck-curve') ? 'curve' : (e.querySelector('h2') ? e.querySelector('h2').firstChild.textContent : e.className))")
    check("deck page: the mana curve sits after the main deck and sideboard, not in the price boxes",
          "curve" in secs and secs.index("curve") > secs.index("サイドボード") and page.locator(".deck-cost .cv").count() == 0, secs)
    check("deck page: the sample-list picker is in a bar that stays at the top", page.evaluate("getComputedStyle(document.querySelector('.deck-pick-bar')).position") == "sticky"
          and page.locator(".deck-pick-bar #deckListSel").count() == 1)
    page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)"); page.wait_for_timeout(200)
    stuck = page.evaluate("[document.querySelector('.deck-pick-bar').getBoundingClientRect().top, parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--stick-top')) || 0]")
    check("deck page: …and it is still on screen after scrolling to the bottom", abs(stuck[0] - stuck[1]) <= 2, stuck)
    page.evaluate("window.scrollTo(0, 0)")
    shorts = page.evaluate("""['Izzet Spellementals', 'Dimir Midrange', 'Azorius Control', 'Mono Red Burn', 'Living End', 'Selesnya Cats', 'Jeskai Control'].map(deckNameShort)""")
    check("short deck names: guilds as colour pairs, ミッド, コン; none where nothing gets shorter",
          shorts == ["青赤スペルメンタル", "青黒ミッド", "白青コン", "", "", "", "ジェスカイコン"], shorts)
    page.goto(SITE + "?view=meta&format=standard"); page.wait_for_selector("#metaBody .meta-row")
    page.evaluate("""metaState.data.trends = metaState.data.trends || {};
        metaState.data.trends.standard = { weeks: ['a','b','c','d','e','f','g','h'], decks: [1,1,1,1,1,1,1,1], share: {
          'Gruul Dragons': [1,1,1,1,10,10,10,10], 'Selesnya Cats': [5,5,5,5,5,5,5,5], 'Mono Red Burn': [8,8,8,8,2,2,2,2], 'Orzhov|u': [0,0,0,0,1,1,1,1] } };
        metaRankCache.clear(); renderMeta();
        metaRankCache.clear(); renderMeta();""")
    mv = page.evaluate("[...document.querySelectorAll('#metaBody .meta-row')].map(r => [r.querySelector('.meta-name-text').innerText, (r.querySelector('.rank-mv') || {}).className || '', r.querySelector('.rank-n').innerText])")
    want_mv = {"グルール・ドラゴン": "rank-mv up", "Selesnya Cats": "rank-mv same", "赤単バーン": "rank-mv down", "オルゾフ（未分類）": "rank-mv up"}
    check("metagame: an arrow by each rank: ▲ moved up, ▼ down, grey — same (4 weeks against the 4 before)",
          all(want_mv.get(n) == c for n, c, _ in mv) and [r for _, _, r in mv] == ["1", "2", "3", "4"], mv)
    check("metagame: …the — is grey and says the rank is the same", page.locator(".rank-mv.same").first.get_attribute("title").startswith("使用率の変化は2pt未満"))
    page.evaluate("metaState.data.trends.standard.share['Selesnya Cats'] = [5,5,5,5,7,7,7,7.5]; metaRankCache.clear(); renderMeta();")
    sel = page.locator("#metaBody .meta-row").nth(1).locator(".rank-mv")
    check("metagame: same rank but the share rose 2pt or more -> ▲", sel.get_attribute("class") == "rank-mv up" and "2.1pt上がりました" in sel.get_attribute("title"), sel.get_attribute("title"))
    page.evaluate("metaState.data.trends.standard.share['Selesnya Cats'] = [5,5,5,5,2.9,2.9,2.9,2.9]; metaRankCache.clear(); renderMeta();")
    check("metagame: same rank but the share fell 2pt or more -> ▼", page.locator("#metaBody .meta-row").nth(1).locator(".rank-mv").get_attribute("class") == "rank-mv down")
    page.evaluate("metaState.data.trends.standard.share['Selesnya Cats'] = [5,5,5,5,6.9,6.9,6.9,6.9]; metaRankCache.clear(); renderMeta();")
    check("metagame: same rank and under 2pt -> grey —", page.locator("#metaBody .meta-row").nth(1).locator(".rank-mv").get_attribute("class") == "rank-mv same")
    page.evaluate("""Object.assign(metaState.data.trends.standard.share, { 'Selesnya Cats': [5,5,5,5,4,4,4,4], 'Mono Red Burn': [4.5,4.5,4.5,4.5,4.6,4.6,4.6,4.6] });
        metaRankCache.clear(); renderMeta();""")
    mv = page.evaluate("[...document.querySelectorAll('#metaBody .meta-row')].map(r => [r.querySelector('.meta-name-text').innerText, (r.querySelector('.rank-mv') || {}).className || ''])")
    check("metagame: a rank that moved with under 2pt of share change still gets the grey —",
          dict(mv).get("Selesnya Cats") == "rank-mv same" and dict(mv).get("赤単バーン") == "rank-mv same", mv)
    page.select_option("#metaSort", "cost"); page.wait_for_timeout(200)
    check("metagame: no rank arrows when sorted by something other than share", page.locator("#metaBody .rank-mv").count() == 0)
    page.select_option("#metaSort", "share"); page.wait_for_timeout(200)
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(200)
    row = page.locator("#metaBody .meta-row").first
    check("phone, metagame: deck names are short (赤緑ドラゴン) while the row is closed", row.locator(".meta-name-text").inner_text() == "赤緑ドラゴン", row.locator(".meta-name-text").inner_text())
    row.locator(".meta-toggle").click()
    check("phone, metagame: …and in full when it is opened", row.locator(".meta-name-text").inner_text() == "グルール・ドラゴン", row.locator(".meta-name-text").inner_text())
    check("phone, metagame: rank arrows fit, no sideways scroll", row.locator(".rank-mv").is_visible() and no_hscroll())
    page.set_viewport_size({"width": 1280, "height": 900})

    # ---- 35. round 23: phone metagame - short format and period buttons, ⓘ only, price column; one-line price box ----
    PRICE_SITE["dir"] = PRICES_FULL
    page.goto(SITE + "?view=meta&format=standard"); page.wait_for_selector("#metaBody .meta-row")
    check("metagame: desktop keeps the full format names and a 価格 column", page.locator("#metaFormats .seg-btn").first.inner_text() == "スタンダード"
          and "価格" in page.locator(".meta-cols").inner_text() and page.locator("#metaHelpBtn").inner_text() == "ⓘ 見方")
    page.wait_for_function("document.querySelector('#metaBody .meta-price .meta-cost')")
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(200)
    check("phone, metagame: formats as St Pi Mo Lg Vt Pa, periods as 30日 90日",
          page.locator("#metaFormats .seg-btn").all_inner_texts() == ["St", "Pi", "Mo", "Lg", "Vt", "Pa"] and page.locator("#metaWindows .seg-btn").all_inner_texts() == ["30日", "90日"],
          (page.locator("#metaFormats .seg-btn").all_inner_texts(), page.locator("#metaWindows .seg-btn").all_inner_texts()))
    fr = page.evaluate("[...document.querySelectorAll('#metaFormats .seg-btn')].map(b => Math.round(b.getBoundingClientRect().right))")
    check("phone, metagame: all six formats fit on screen", max(fr) <= 390 - 16, fr)
    check("phone, metagame: the help button is just ⓘ (named for screen readers) and fits", page.locator("#metaHelpBtn").inner_text() == "ⓘ"
          and page.get_attribute("#metaHelpBtn", "aria-label") == "見方" and page.evaluate("document.querySelector('#metaHelpBtn').getBoundingClientRect().right") <= 390 - 16)
    row = page.locator("#metaBody .meta-row").first
    pr, sh = row.locator(".meta-price").bounding_box(), row.locator(".meta-share").bounding_box()
    check("phone, metagame: the price sits in its own column left of the share", row.locator(".meta-price").inner_text().startswith("¥") and pr["x"] + pr["width"] <= sh["x"] + 1, (pr, sh))
    pip = page.evaluate("(() => { const p = document.querySelector('#metaBody .meta-row .meta-name .pips img.pip, #metaBody .meta-row .meta-name .pips .pip'); return p ? p.getBoundingClientRect().width : 0; })()")
    check("phone, metagame: small mana symbols (11px) next to the deck name", 0 < pip <= 12, pip)
    page.evaluate("document.querySelector('#metaBody .meta-row .meta-name-text').textContent = '青赤スペルメンタル・リアニメイト'; fitMetaNames()")
    fit = page.evaluate("(() => { const a = document.querySelector('#metaBody .meta-row .meta-name-text'); return [parseFloat(getComputedStyle(a).fontSize), a.getBoundingClientRect().height, a.scrollWidth <= a.clientWidth + 1]; })()")
    check("phone, metagame: a long deck name gets a smaller font and stays on one line", fit[0] < 13.5 and fit[0] >= 9 and fit[1] < 20, fit)
    page.locator("#metaBody .meta-row").first.locator(".meta-toggle").click()
    check("phone, metagame: …and its full size when the row is opened", page.evaluate("document.querySelector('#metaBody .meta-row .meta-name-text').style.fontSize") == "")
    page.locator("#metaBody .meta-row").first.locator(".meta-toggle").click()
    page.set_viewport_size({"width": 1280, "height": 900})
    page.evaluate("setLang('en')"); page.wait_for_timeout(200)
    check("metagame in English: the column says Share, not Share of field", "Share of field" not in page.locator(".meta-cols").inner_text() and "Share" in page.locator(".meta-cols").inner_text())
    page.evaluate("setLang('ja')"); page.wait_for_timeout(200)
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Gruul%20Dragons"); page.wait_for_selector("#deckBody .deck-group")
    page.wait_for_function("document.querySelector('.deck-cost .dcst-v')")
    box = page.locator(".deck-cost .dcst-price")
    PRICE_SITE["dir"] = None
    check("deck page: the price box is just 価格 and the value, on one line", "いちばん安い版" not in box.inner_text() and box.bounding_box()["height"] < 48, (box.inner_text(), box.bounding_box()))

    # ---- 36. round 24: hiragana game words; English-only cards for Japanese phrases ----
    hr = page.evaluate("""(() => ({
      read: ['はかい', 'くりーちゃーをはかい', 'ぜんたいじょきょ', 'かーどを2まいひく', 'らがばん', '破壊', 'かえる'].map(jaFromReading),
      parts: prepareJapanese(['墓地から手札'])[0].enParts, none: prepareJapanese(['墓地から謎'])[0].enParts,
      bare: prepareJapanese(['はかい'])[0].bare, role: splitRoleToken('じょきょ'),
    }))()""")
    check("hiragana game words read as kanji, unknown words left alone",
          hr["read"] == ["破壊", "クリーチャーを破壊", "全体除去", "カードを2枚引く", None, None, None], hr["read"])
    check("hiragana: nothing dropped as a particle (はかい stays はかい), じょきょ is the removal role", hr["bare"] == "はかい" and hr["role"]["role"] == "removal", (hr["bare"], hr["role"]))
    check("墓地から手札 in English for cards with no Japanese text (graveyard, hand); not when a part has no English", hr["parts"] == ["graveyard", "hand"] and hr["none"] is None, (hr["parts"], hr["none"]))

    # ---- 37. round 25: reliability - punctuation, colons and minus signs, own names, English names, card shapes, colors ----
    rl = page.evaluate("""(() => {
      const row = { name_ja: '石の雨', type_ja: 'ソーサリー', oracle_ja: '土地１つを対象とし、それを破壊する。', alt_names_ja: '' };
      const crit = { name_ja: '灰色熊', type_ja: 'クリーチャー — 熊', oracle_ja: '灰色熊が死亡したとき、カード１枚を引く。', alt_names_ja: '古い熊' };
      const dfc = { name_ja: '甲冑 // 乙女', type_ja: 'クリーチャー — 人間 // 土地', oracle_ja: '甲冑が攻撃するたび、甲冑を変身させる。 // 乙女はタップ状態で戦場に出る。', alt_names_ja: '' };
      const p = q => { const r = parseSearch(q); return { f: r.filters.length, ja: r.ja, words: r.words, neg: r.filters.some(f => f.negate), al: r.aliases.map(a => a.from + '>' + a.to) }; };
      return {
        norm: [normJaSearch('対象とし、それを「破壊」する。'), normJaSearch('対象とし、それ', true), normText('−1/−0')],
        chunks: prepareJapanese(['土地1つを対象とし、それを破壊する'])[0].chunks, n: prepareJapanese(['土地1つを対象とし、それを破壊する'])[0].n,
        self: [rowJaText(row), rowJaText(crit), rowJaText(Object.assign({}, crit, { oracle_ja: '古い熊が死亡したとき' })), rowJaText(dfc)],
        tap: p('{T}:アーティファクト1つを対象とする'), loy: p('-2:カード2枚を引く'), minus: p('-1/-0の修整を受ける'), neg: p('-飛行'), op: p('t:クリーチャー'),
        mana: p('{2}{B}, クリーチャー1体を生け贄に捧げる'),
        key: [nameKey('Lim-Dûl'), nameKey('Mjölnir')],
        shapes: ['分割カード', '両面', 'MDFC', 'split card', 'double faced cards', 'is:transform', 'split second'].map(p),
        narrow: ['白 天使', '白の天使', '3マナのクリーチャー', '黒のクリーチャー', '"白" 天使', '-白の天使', '白のクリーチャーを破壊'].map(p),
      };
    })()""")
    check("punctuation (、。「」) is left out of the searched text; a typed 、 still splits the parts",
          rl["norm"] == ["対象としそれを破壊する", "対象とし、それ", "-1/-0"] and rl["chunks"] == ["土地1つ", "対象", "それ", "破壊"] and rl["n"] == "土地1つを対象としそれを破壊する", (rl["norm"], rl["chunks"], rl["n"]))
    check("a card's own name in its text reads as このクリーチャー / この土地 (also its older name); instants and sorceries keep it",
          rl["self"] == ["土地１つを対象とし、それを破壊する。", "このクリーチャーが死亡したとき、カード１枚を引く。", "このクリーチャーが死亡したとき",
                         "このクリーチャーが攻撃するたび、このクリーチャーを変身させる。 // この土地はタップ状態で戦場に出る。"], rl["self"])
    check("{T}:... and -2:... and -1/-0... are card text; -飛行 and t:クリーチャー still work",
          rl["tap"]["f"] == 0 and rl["tap"]["ja"] and rl["loy"]["f"] == 0 and not rl["loy"]["neg"] and rl["minus"]["f"] == 0 and rl["minus"]["ja"]
          and rl["neg"]["neg"] and rl["op"]["f"] == 1, (rl["tap"], rl["loy"], rl["minus"], rl["neg"], rl["op"]))
    check("mana symbols beside Japanese words are part of the Japanese text", rl["mana"]["ja"] == ["{2}{B},", "クリーチャー1体を生け贄に捧げる"] and not rl["mana"]["words"], rl["mana"])
    check("names: accents and hyphens left out (lim dul finds Lim-Dûl, mjolnir finds Mjölnir)", rl["key"] == ["limdul", "mjolnir"], rl["key"])
    check("card shapes: 分割カード, 両面, MDFC, split card, double faced cards, is:transform are filters; split second is not",
          all(x["f"] == 1 and not x["ja"] and not x["words"] for x in rl["shapes"][:6]) and rl["shapes"][1]["al"] == ["両面>両面カード"]
          and rl["shapes"][3]["al"] == ["split card>分割カード"] and rl["shapes"][6]["f"] == 0, rl["shapes"])
    nw = rl["narrow"]
    check("colors and mana values narrow: 白 天使, 3マナのクリーチャー, 黒のクリーチャー; not in quotes, not -白の天使, not inside a sentence",
          nw[0]["f"] == 1 and nw[0]["ja"] == ["天使"] and nw[0]["al"] == ["白>白のカード"]
          and nw[2]["f"] == 1 and nw[2]["ja"] == [] and nw[3]["f"] == 1 and nw[3]["ja"] == [] and nw[3]["al"] == ["黒のクリーチャー>黒のクリーチャー・カード"]
          and nw[4]["f"] == 0 and nw[5]["f"] == 1 and nw[5]["neg"] and nw[6]["f"] == 0, nw)
    search("白")
    check("the note says what a color word did: 「白」で白のカードに絞り込みました。", "「白」で白のカードに絞り込みました。" in page.locator("#matchNote").inner_text(), page.locator("#matchNote").inner_text())

    # ---- 38. round 26: even sizes - mana symbols on one scale, buttons in a row the same height, metagame numbers on one line ----
    def widths(sel): return page.evaluate("s => [...document.querySelectorAll(s)].filter(e => e.offsetParent).map(e => Math.round(e.getBoundingClientRect().width * 10) / 10)", sel)
    def heights(sel): return page.evaluate("s => [...document.querySelectorAll(s)].filter(e => e.offsetParent).map(e => Math.round(e.getBoundingClientRect().height))", sel)
    def tops(row_sel, parts):   # the centre of each part's first line, relative to the row
        return page.evaluate("""([rs, parts]) => { const row = document.querySelector(rs); const r0 = row.getBoundingClientRect().top;
          return parts.map(p => { const e = row.querySelector(p); if (!e || !e.offsetParent) return null; const rg = document.createRange(); rg.selectNodeContents(e);
            const r = rg.getClientRects()[0] || e.getBoundingClientRect(); return Math.round(((r.top + r.bottom) / 2 - r0) * 10) / 10; }); }""", [row_sel, parts])
    PRICE_SITE["dir"] = PRICES_FULL; META_MODE["mode"] = "fixture"; DECKS_MODE["mode"] = "fixture"
    DB_MODE["variant"] = "roles"
    home()
    search("加速の石")   # {3}, and {T}: Add {C}{C} in its text
    page.click("#viewToggle .view-btn[data-view=text]"); page.wait_for_selector("#cardGrid .text-row")
    DB_MODE["variant"] = None
    pw = widths("#cardGrid .tr-meta img.pip")
    check("sizes: mana costs beside list text are 16px", pw and set(pw) == {16}, pw)
    sym = page.evaluate("[...document.querySelectorAll('#cardGrid .tr-text img.sym')].map(e => [e.getBoundingClientRect().width, parseFloat(getComputedStyle(e.parentElement).fontSize)])")
    check("sizes: symbols inside card text are as tall as the text (1em)", sym and all(abs(a - b) < 0.6 for a, b in sym), sym)
    tb = heights("#filterOpenBtn, #viewToggle, #sortSelect")
    check("sizes: the results toolbar's buttons and menu are one height (34px)", len(set(tb)) == 1 and tb[0] == 34, tb)
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(200)
    tb = heights("#filterOpenBtn, #viewToggle, #sortSelect")
    clipped = page.evaluate("(() => { const s = document.getElementById('sortSelect'); const c = document.createElement('canvas').getContext('2d'); const cs = getComputedStyle(s); c.font = cs.fontSize + ' ' + cs.fontFamily; return c.measureText(s.options[s.selectedIndex].text).width + parseFloat(cs.paddingLeft) + 18 > s.clientWidth; })()")
    check("sizes, phone: the toolbar is one height (36px) and the sort menu's text fits", len(set(tb)) == 1 and tb[0] == 36 and not clipped, (tb, clipped))
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(SITE + "?card=elf-ja"); page.wait_for_selector("#cardView .cp-cost img.pip")
    check("sizes: the card page's mana cost is 20px", set(widths(".cp-cost img.pip")) == {20}, widths(".cp-cost img.pip"))
    page.goto(SITE + "?view=meta&format=standard"); page.wait_for_selector("#metaBody .meta-row .meta-price .meta-cost")
    check("sizes: deck colours in the metagame table are 16px on wide screens", set(widths("#metaBody .meta-name img.pip")) == {16}, widths("#metaBody .meta-name img.pip"))
    mh = heights("#metaFormats .seg-btn, #metaWindows .seg-btn, #metaSort, #metaHelpBtn")
    check("sizes: the metagame header's buttons and sort menu are one height (30px)", set(mh) == {30}, mh)
    check("metagame: the help button still reads ⓘ 見方", page.locator("#metaHelpBtn").inner_text() == "ⓘ 見方", page.locator("#metaHelpBtn").inner_text())
    t = tops("#metaBody .meta-row", [".meta-name-text", ".meta-price .meta-cost", ".meta-share .meta-num", ".meta-wr .meta-num"])
    check("metagame: name, price, share and win rate read along one line", None not in t and max(t) - min(t) <= 2, t)
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(300)
    check("phone, metagame: deck colours stay 11px", set(widths("#metaBody .meta-row:not(.open) .meta-name img.pip")) == {11}, widths("#metaBody .meta-name img.pip"))
    t = tops("#metaBody .meta-row", [".meta-name-text", ".meta-price .meta-cost", ".meta-share .meta-num", ".meta-wr .meta-num", ".meta-rank"])
    check("phone, metagame: name, price, share, win rate and rank on one line", None not in t and max(t) - min(t) <= 2, t)
    mh = heights("#metaFormats .seg-btn, #metaWindows .seg-btn, #metaSort, #metaHelpBtn")
    check("phone, metagame: header buttons and menu one height (28px)", set(mh) == {28}, mh)
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Gruul%20Dragons"); page.wait_for_selector("#deckBody .deck-group")
    check("sizes: a deck page's title colours are 20px; 書き出す and 画像/リスト one height",
          set(widths(".deck-title img.sym")) == {20} and len(set(heights("#deckExport > summary, .deck-tools > .view-toggle"))) == 1,
          (widths(".deck-title img.sym"), heights("#deckExport > summary, .deck-tools > .view-toggle")))
    home(); page.wait_for_selector("#homeMetaBody .hb-deck .hb-name img.sym")
    hs = widths(".hb-deck .hb-name img.sym")
    check("sizes: the home page's top decks use 16px colours", hs and set(hs) == {16}, hs)

    # ---- 39. phones: the English deck page's facts line wraps instead of widening the page ----
    PRICE_SITE["dir"] = PRICES_FULL
    page.set_viewport_size({"width": 360, "height": 800})
    page.evaluate("setLang('en', true)")
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Gruul%20Dragons"); page.wait_for_selector("#deckBody .deck-group")
    page.wait_for_function("document.querySelector('.deck-cost .dcst-v')"); page.wait_for_timeout(200)
    check("phone, English deck page: '… match wins (… matches)' wraps at the ·, no sideways scroll",
          "match wins" in page.locator(".deck-meta").inner_text() and no_hscroll(), (page.locator(".deck-meta").inner_text(), page.evaluate("document.documentElement.scrollWidth")))
    page.evaluate("setLang('ja', true)")
    PRICE_SITE["dir"] = None
    page.set_viewport_size({"width": 1280, "height": 900})

    # ---- 40. a compact advanced search: same filters, fewer lines ----
    ADV = """(() => { const q = s => [...document.querySelectorAll(s)].filter(e => e.offsetParent);
      const box = e => e.getBoundingClientRect(); const p = document.getElementById('filterPanel');
      const c = document.createElement('canvas').getContext('2d');
      return { w: box(p).width, h: box(p).height, inner: p.scrollHeight - p.clientHeight,
        mvTops: [...new Set(q('#filterPanel .mv-chip').map(e => Math.round(box(e).top)))].length,
        colorLeft: Math.round(box(q('#filterPanel .chip')[0]).left), mvLeft: Math.round(box(q('#filterPanel .mv-chip')[0]).left),
        colorW: Math.round(box(q('#filterPanel .chip')[0]).width), mvW: Math.round(box(q('#filterPanel .mv-chip')[0]).width),
        titleTops: q('#filterPanel .filter-title').map(e => Math.round(box(e).top)),
        fieldFont: q('#filterPanel .list-filter, #formatSelect').map(e => parseFloat(getComputedStyle(e).fontSize)),
        cut: q('#filterPanel .list-filter').filter(i => { const cs = getComputedStyle(i); c.font = cs.fontSize + ' ' + cs.fontFamily;
          return c.measureText(i.placeholder).width > i.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) + 1; }).map(i => i.id) }; })()"""
    page.set_viewport_size({"width": 1280, "height": 900})
    home(); open_adv(); page.wait_for_timeout(150)
    a = page.evaluate(ADV)
    check("advanced search, home: all nine mana values on one line, no hint cut off", a["mvTops"] == 1 and not a["cut"], a)
    if a["w"] >= 760:   # titles: colour, mana value, rarity, card type, role, creature type, keyword, format
        tt = a["titleTops"]
        check("advanced search, home: colour, mana value and rarity share the first line; four lines at most",
              len(set(tt[:3])) == 1 and len(set(tt)) <= 4 and a["h"] <= 360, a)
    check("advanced search: colour and mana value buttons are 34px with 24px symbols",
          set(page.evaluate("[...document.querySelectorAll('#filterPanel .chip, #filterPanel .mv-chip')].map(b => [b.getBoundingClientRect().width, (b.querySelector('img, .mv-txt')).getBoundingClientRect().width].join())")) == {"34,24"})
    rar = page.evaluate("""[...document.querySelectorAll('#filterPanel .opt-chip[data-group=rarity]')].map(b => [b.innerText.trim(), b.title,
      getComputedStyle(b.querySelector('.rar-txt')).backgroundColor])""")
    field = page.evaluate("getComputedStyle(document.getElementById('roleFilter')).backgroundColor")
    check("advanced search: rarity reads C U R M, with the full names as tooltips, all one plain colour while off",
          [r[0] for r in rar] == ["C", "U", "R", "M"] and [r[1] for r in rar] == ["コモン", "アンコモン", "レア", "神話レア"] and {r[2] for r in rar} == {field}, (rar, field))
    page.click('#filterPanel .opt-chip[data-value="mythic"]'); page.wait_for_timeout(200)
    on = page.evaluate("""(() => { const d = document.createElement('span'); d.className = 'dot mythic'; document.body.appendChild(d);
      const want = getComputedStyle(d).backgroundColor; d.remove();
      return [getComputedStyle(document.querySelector('#filterPanel .opt-chip[data-value=mythic] .rar-txt')).backgroundColor, want,
              [...document.querySelectorAll('#activeFilters .filter-pill')].map(p => p.innerText).join('|')]; })()""")
    check("advanced search: a chosen rarity fills with the cards' rarity colour; its pill says the full name", on[0] == on[1] and "神話レア" in on[2], on)
    page.locator("#activeFilters .filter-pill", has_text="神話レア").click(); page.wait_for_timeout(200)
    open_adv(); page.wait_for_timeout(150)
    page.focus("#roleFilter"); page.keyboard.type("r"); page.wait_for_timeout(150)
    dw, iw = page.evaluate("[document.getElementById('roleList').getBoundingClientRect().width, document.getElementById('roleFilter').getBoundingClientRect().width]")
    check("advanced search, home: the role suggestions are at least as wide as their field", page.locator("#roleList").is_visible() and dw >= iw - 1, (dw, iw))
    page.fill("#roleFilter", ""); page.press("#roleFilter", "Escape")
    top_search("テスト"); page.wait_for_timeout(300)
    a = page.evaluate(ADV)
    page.click('#sideAdvSlot .opt-chip[data-value="rare"]'); page.wait_for_timeout(200)
    bg = page.evaluate("getComputedStyle(document.querySelector('#sideAdvSlot .opt-chip[data-value=rare] .rar-txt')).backgroundColor")
    rows = page.evaluate("new Set([...document.querySelectorAll('#sideAdvSlot .opt-chip[data-group=rarity]')].map(b => Math.round(b.getBoundingClientRect().top))).size")
    check("advanced search, sidebar: the chosen rarity (R) turns gold; C U R M on one line", bg == "rgb(209, 169, 63)" and rows == 1, (bg, rows))
    page.click('#sideAdvSlot .opt-chip[data-value="rare"]'); page.wait_for_timeout(200)
    check("advanced search, sidebar: mana values on one line, lined up with the colours, nothing to scroll inside",
          a["w"] == 262 and a["mvTops"] == 1 and a["colorLeft"] == a["mvLeft"] and a["colorW"] == a["mvW"] and a["inner"] <= 1 and not a["cut"], a)
    page.set_viewport_size({"width": 880, "height": 900}); page.wait_for_timeout(250); open_adv(); page.wait_for_timeout(150)
    a = page.evaluate(ADV)
    check("advanced search, 880px: the panel fills the column instead of the old 360px drawer", a["w"] > 800 and a["mvTops"] == 1 and not a["cut"] and no_hscroll(), a)
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(250); open_adv(); page.wait_for_timeout(150)
    a = page.evaluate(ADV)
    col = page.evaluate("document.querySelector('#resultsAdvSlot').getBoundingClientRect().width")
    check("phone, advanced search: as wide as the page column, mana values on one line, colours lined up, 16px fields, no sideways scroll",
          abs(a["w"] - col) <= 1 and a["mvTops"] == 1 and a["colorLeft"] == a["mvLeft"] and set(a["fieldFont"]) == {16} and not a["cut"] and no_hscroll(), (a, col))
    page.set_viewport_size({"width": 1280, "height": 900})

    # ---- 41. search tuning: names by reading, nicknames, names typed slightly wrong, a type beside a color, the order ----
    DB_MODE["variant"] = "roles"
    home()
    names = lambda: page.locator("#cardGrid .card-name-main, #cardGrid .tr-name").all_inner_texts()
    note = lambda: page.locator("#matchNote").inner_text()
    run("いなずま")
    check("search tuning: a name typed in hiragana by its reading (いなずま) finds 稲妻 first", names()[:1] == ["稲妻"], names())
    run("ボルト")
    check("search tuning: a nickname (ボルト) shows the card first, with a note", names()[:1] == ["稲妻"] and "「ボルト」は「稲妻」としても検索しました。" in note(), (names(), note()))
    run("ラガヴァン")
    check("search tuning: a name typed slightly wrong (ラガヴァン) finds the card, and the note says what was searched",
          "敏捷なこそ泥、ラガバン" in names() and "「ラガヴァン」は「ラガバン」として検索しました。" in note(), (names(), note()))
    run("赤 インスタント")
    check("search tuning: 赤 インスタント = red instants only, with a note for each word",
          names() and set(names()) <= {"稲妻", "ショック", "大きな稲妻テスト", "加速"} and "インスタント・カードに絞り込みました" in note(), (names(), note()))
    tu = page.evaluate("""(() => ({
      yomi: [yomiKey('えむらくーる'), yomiKey('らがゔぁん'), yomiQuery('はかい'), yomiQuery('いなずま'), yomiQuery('いな')],
      loose: looseKana('ラガヴァン') === looseKana('ラガバン') && looseKana('ジェース') !== looseKana('ジェイス'),
      order: [{ name_ja: '稲妻', name_kana: 'いなずま', _nameJa: '稲妻', _nameEn: 'lightning bolt' }, { name_ja: 'A.I.M.の科学者', name_kana: 'AIMのかがくしゃ', _nameJa: 'a.i.m.の科学者', _nameEn: 'a.i.m. scientists' },
              { name_ja: '', name_kana: '', _nameJa: '', _nameEn: 'black lotus' }].map(jaSortKey).map(k => k[0]),
      none: closestJaName('ああああああああ'),
      gojuon: [['ごぶりんしょっこうだん', 'ゴブリン職工団'], ['ごぶりんじゅんしぶたい', 'ゴブリン巡視部隊'], ['ごぶりんしゅうぜんや', 'ゴブリン修繕屋'], ['はいぼく', '敗北'], ['ばいぼく', '倍ぼく']]
        .map(([k, n]) => ({ name_ja: n, name_kana: k, _nameJa: n, _nameEn: n })).sort((a, b) => jaSortKey(a) < jaSortKey(b) ? -1 : 1).map(r => r.name_ja),
    }))()""")
    check("search tuning: readings with ー and ゔ (えむらくうる, らがばん); game words in hiragana are not read as names; two letters are too few",
          tu["yomi"] == ["えむらくうる", "らがばん", None, "いなずま", None], tu["yomi"])
    check("search tuning: ヴァ is read as バ when a name is compared loosely", tu["loose"], tu)
    check("search tuning: あいうえお order - kana names, then names that start with a letter (A.I.M.の科学者), then English-only cards", tu["order"] == ["0", "1", "2"], tu["order"])
    check("search tuning: no close name for nonsense", tu["none"] is None, tu)
    check("search tuning: あいうえお order as in a dictionary - ゛ and small kana only break ties (しゅう, じゅん, しょっ; は before ば)",
          tu["gojuon"] == ["ゴブリン修繕屋", "ゴブリン巡視部隊", "ゴブリン職工団", "敗北", "倍ぼく"], tu["gojuon"])
    DB_MODE["variant"] = None

    # ---- 42. the deck price page: paste a list (Arena, MTGO, typed; Japanese or English names), see what it costs ----
    PRICE_SITE["dir"] = PRICES_FULL
    DECKS_MODE["mode"] = "fixture"
    page.set_viewport_size({"width": 1280, "height": 900})
    cheap = json.loads(gzip.decompress(open(os.path.join(PRICES_FULL, "cheap.json.gz"), "rb").read()))["cards"]
    page.goto(SITE + "?view=import"); page.wait_for_selector("#importText")
    page.wait_for_function("typeof LOCAL_DB !== 'undefined' && LOCAL_DB")
    check("deck price page: opens with an empty box and help on what it reads", page.locator(".imp-empty").count() == 1 and page.locator("#importSample").count() == 1
          and page.title().startswith("デッキの価格を調べる") and page.locator("#tabPrices").get_attribute("aria-selected") == "true")
    check("deck price page: a switch at the top between the want list and the pasted deck, on デッキの価格",
          page.locator("#impWhich a").all_inner_texts() == ["ウォントリスト", "デッキの価格"] and page.locator("#impWhich a[aria-current=page]").inner_text() == "デッキの価格"
          and page.locator("#impWhich a").first.get_attribute("href") == "?view=want" and page.locator(".imp-title").inner_text() == "デッキの価格を調べる"
          and page.locator("#impLabel").inner_text() == "デッキリスト", page.locator("#impWhich").inner_text())
    parsed = page.evaluate("""(() => { const P = s => parseDeckText(s).lines.map(l => [l.count, l.name, l.part]);
      return {
        arena: (() => { const r = parseDeckText('About\\nName Gruul Smash\\n\\nCommander\\n1 Ragavan, Nimble Pilferer\\n\\nCompanion\\n1 Qasali Pridemage\\n\\nDeck\\n4 Lightning Bolt (M10) 146\\n2 Shivan Dragon (M10) 156 *F*\\n\\nSideboard\\n1 Qasali Pridemage\\n3 Llanowar Elves'); return [r.title, r.lines.map(l => [l.count, l.name, l.part])]; })(),
        mtgo: P('4 Lightning Bolt\\n20 Mountain\\n\\n2 Shivan Dragon\\nSB: 1 Urza\\'s Saga'),
        typed: P('４ 稲妻\\n稲妻 x2\\n3x Llanowar Elves\\n2枚 ウルザの物語\\nシヴ山のドラゴン\\n// a comment\\n火/氷'),
        jaArena: P('デッキ\\n4 稲妻 (M10) 146\\n\\nサイドボード\\n2 ラノワールのエルフ'),
        groups: P('Creatures (4)\\n4 Shivan Dragon\\n\\nInstants (4)\\n4 Lightning Bolt\\n\\nSideboard (2)\\n2 Llanowar Elves'),
      }; })()""")
    check("deck import: an MTG Arena export - deck name, Commander, Companion, Deck, Sideboard; set codes and foil marks left off",
          parsed["arena"] == ["Gruul Smash", [[1, "Ragavan, Nimble Pilferer", "commander"], [1, "Qasali Pridemage", "companion"], [4, "Lightning Bolt", "main"],
                                             [2, "Shivan Dragon", "main"], [1, "Qasali Pridemage", "side"], [3, "Llanowar Elves", "side"]]], parsed["arena"])
    check("deck import: Magic Online text - the sideboard after a blank line, SB: lines", parsed["mtgo"] == [[4, "Lightning Bolt", "main"], [20, "Mountain", "main"], [2, "Shivan Dragon", "side"], [1, "Urza's Saga", "side"]], parsed["mtgo"])
    check("deck import: typed lines - full-width numbers, x2 after the name, 3x, 2枚, no number (one copy), comments, Fire/Ice",
          parsed["typed"] == [[4, "稲妻", "main"], [2, "稲妻", "main"], [3, "Llanowar Elves", "main"], [2, "ウルザの物語", "main"], [1, "シヴ山のドラゴン", "main"], [1, "火 // 氷", "main"]], parsed["typed"])
    check("deck import: the Japanese MTG Arena's デッキ / サイドボード", parsed["jaArena"] == [[4, "稲妻", "main"], [2, "ラノワールのエルフ", "side"]], parsed["jaArena"])
    check("deck import: card-type headings from deck sites are skipped, and their blank lines don't start the sideboard",
          parsed["groups"] == [[4, "Shivan Dragon", "main"], [4, "Lightning Bolt", "main"], [2, "Llanowar Elves", "side"]], parsed["groups"])
    found = page.evaluate("""['稲妻', 'lightning bolt', 'ragavan nimble pilferer', '敏捷なこそ泥 ラガバン', 'らのわーるのえるふ', 'Urzas Saga', 'Nothing Like This']
      .map(n => { const r = importRow(n); return r ? r.name_en : null; })""")
    check("deck import: cards by Japanese or English name, any case, without punctuation, in hiragana",
          found == ["Lightning Bolt", "Lightning Bolt", "Ragavan, Nimble Pilferer", "Ragavan, Nimble Pilferer", "Llanowar Elves", "Urza's Saga", None], found)
    merged = page.evaluate("""(() => { const r = readImport('Companion\\n1 Qasali Pridemage\\nDeck\\n4 稲妻\\n2 Lightning Bolt\\nSideboard\\n1 Qasali Pridemage'); return [r.main.map(x => [x.count, x.name]), r.side.map(x => [x.count, x.name])]; })()""")
    check("deck import: the same card on two lines is added up; Arena's companion isn't counted twice", merged == [[[6, "Lightning Bolt"]], [[1, "Qasali Pridemage"]]], merged)

    newcard = page.evaluate("""loadCheapest().then(() => { const r = readImport('2 deathrite shaman'); return [r.main.map(x => [x.count, x.name, !!x.row]), r.missing.length]; })""")
    check("deck import: a card too new for the card database is still found by its English name in the price file",
          newcard == [[[2, "Deathrite Shaman", False]], 0], newcard)
    LIST = "Deck\n4 稲妻\n4 Shivan Dragon (M10) 156\n3 ラノワールのエルフ\n4 Lightnig Bolt\n20 Mountain\n\nSideboard\n2 Qasali Pridemage"
    page.fill("#importText", LIST)
    page.wait_for_function("document.querySelector('#importBody .deck-cost .dcst-v') && document.querySelector('#importBody [data-iview=list]')")
    page.click("#importBody [data-iview=list]"); page.wait_for_selector("#importBody .dl-yen:not(:empty)")
    def yen1(name):
        r = cheap.get(name)
        opts = [x for x in ((r[0] / 100 * 150.0) if r and r[0] else None, (r[1] / 100 * 160.0) if r and r[1] else None) if x is not None]
        return min(opts) if opts else None
    parts = [(4, "Lightning Bolt"), (4, "Shivan Dragon"), (3, "Llanowar Elves"), (2, "Qasali Pridemage")]
    want = sum(n * yen1(nm) for n, nm in parts if yen1(nm) is not None)
    gone = 4 + sum(n for n, nm in parts if yen1(nm) is None)   # the line not found, and cards with no price
    want_txt = "約¥{:,}〜".format(int(round(round(want) / 100) * 100))
    body = page.locator("#importBody").inner_text()
    check("deck price page: the total in yen, each card's cheapest printing, basic lands left out (the same sum as the deck pages); the card not found makes it 〜",
          page.locator("#importBody .deck-cost .dcst-v").inner_text() == want_txt
          and "価格のないカード{}枚を除く".format(gone) in page.locator("#importBody .deck-cost").inner_text(), (page.locator("#importBody .deck-cost").inner_text(), want_txt))
    check("deck price page: main deck and sideboard counted, the deck's facts line says so", "メイン 31枚" in body and "サイドボード 2枚" in body, body[:200])
    check("deck price page: no breakdown of the cheapest printings (the owner didn't want it)", page.locator(".imp-breakdown, .ib-row").count() == 0)
    miss = page.locator(".imp-miss")
    check("deck price page: a card it can't find is listed with what it may be", miss.count() == 1 and "4 Lightnig Bolt" in miss.inner_text()
          and "見つからなかったカード 4枚" in miss.inner_text() and page.locator(".imp-fix").first.inner_text() == "Lightning Bolt", miss.inner_text() if miss.count() else "")
    page.locator(".imp-fix").first.click()
    page.wait_for_function("!document.querySelector('.imp-miss')")
    check("deck price page: picking the suggestion fixes that line (count kept) and the price follows",
          "4 Lightning Bolt" in page.input_value("#importText").split("\n") and page.locator(".imp-miss").count() == 0
          and page.locator("#importBody .dl-row", has=page.locator(".dl-name", has_text="稲妻")).first.locator(".want-c").inner_text() == "8枚", page.input_value("#importText"))
    page.click("#importExport summary"); page.click("#importExport [data-iexport=arena]")
    page.wait_for_function("document.querySelector('#importExport [data-iexport=arena]').textContent === 'コピーしました'")
    clip = page.evaluate("navigator.clipboard.readText()")
    check("deck price page: export for MTG Arena in English names, whatever language was pasted",
          clip == "Deck\n8 Lightning Bolt\n4 Shivan Dragon\n3 Llanowar Elves\n20 Mountain\n\nSideboard\n2 Qasali Pridemage\n", clip)
    page.wait_for_timeout(1300)
    page.click("#importExport summary"); page.click("#importExport [data-iexport=link]")
    page.wait_for_function("document.querySelector('#importExport [data-iexport=link]').textContent === 'コピーしました'")
    link = page.evaluate("navigator.clipboard.readText()")
    check("deck price page: the link to the list carries it", "?view=import&list=" in link and "Lightning%20Bolt" in link, link[:120])
    page.wait_for_timeout(1300)
    page.reload(); page.wait_for_selector("#importBody .deck-cost")
    check("deck price page: the pasted list is still there after a reload (kept in this browser only)", "4 Lightning Bolt" in page.input_value("#importText")
          and page.evaluate("localStorage.getItem('warujie-deck-import')") == page.input_value("#importText"))
    page.goto(SITE + "?view=import"); page.fill("#importText", "")
    page.goto(link.replace("https://warujie.jp/", SITE).replace(link.split("?")[0], SITE)); page.wait_for_selector("#importBody .deck-cost .dcst-v")
    check("deck price page: opening the link shows that list and its price, then the address is plain again",
          page.locator("#importBody .deck-cost .dcst-v").inner_text() == page.evaluate("costText(deckCost([[8,'Lightning Bolt'],[4,'Shivan Dragon'],[3,'Llanowar Elves'],[2,'Qasali Pridemage']]))")
          and page.url.endswith("?view=import"), page.url)
    page.click("[data-iview=image]"); page.wait_for_selector("#importBody .deck-card")
    check("deck price page: the picture view shows the cards with their counts", page.locator("#importBody .deck-card .dc-count").count() >= 4)
    page.click("[data-iview=list]")
    page.locator("#importBody .dl-name", has_text="稲妻").first.click(); page.wait_for_selector("#cardView .card-name, #cardView h1")
    check("deck price page: a card's name opens its card page", "card=" in page.url, page.url)
    page.go_back(); page.wait_for_selector("#importBody .deck-cost")
    check("deck price page: no price button, the list prices itself", page.locator("#importForm button[type=submit], .imp-go").count() == 0 and page.locator("#importClear").is_visible())
    page.press("#importText", "Enter")
    check("deck price page: Enter in the box doesn't reload the page", "view=import" in page.url and page.locator("#importBody .deck-cost").count() == 1, page.url)
    page.click("#importClear")
    check("deck price page: 消す empties the box and the saved list", page.input_value("#importText") == "" and page.evaluate("localStorage.getItem('warujie-deck-import')") is None and page.locator(".imp-empty").count() == 1)
    page.fill("#importText", "hello\nworld"); page.wait_for_timeout(600)
    check("deck price page: text with no card in it says nothing was found", "見つからなかったカード" in page.locator("#importBody").inner_text(), page.locator("#importBody").inner_text()[:200])
    page.fill("#importText", "")
    # the ways in: the price tab's button, and a deck page's 編集して計算
    page.goto(SITE + "?view=meta&format=standard"); page.wait_for_selector("#metaBody .meta-row")
    check("metagame tab: no link to the deck price page (it moved to the price tab)", page.locator("#metaView a[data-import]").count() == 0)
    page.goto(SITE + "?view=prices"); page.wait_for_selector("#pricesView .imp-open")
    ob = page.locator("#pricesView .imp-open").bounding_box(); toggle = page.locator("#moverWindows .seg-btn").first.bounding_box(); up = page.locator('#moverBody .mover-col[data-dir="up"]').bounding_box()
    check("price tab: a デッキの価格を調べる button of its own, out of the bar, above the winners, bigger than the toggles",
          page.locator("#pricesView .imp-open b").inner_text().strip() == "デッキの価格を調べる" and page.locator("#pricesView .imp-open").get_attribute("href") == "?view=import"
          and page.locator("#pricesView .meta-bar .imp-open").count() == 0 and ob["y"] + ob["height"] <= up["y"] and ob["height"] >= toggle["height"] * 1.5, (ob, toggle, up))
    bar = page.locator("#pricesView .meta-bar").bounding_box()
    summ = page.locator("#moverSummary").bounding_box()
    check("price tab, desktop: the deck price button sits right of a shorter price movers bar, the same height, the dates below both",
          ob["x"] >= bar["x"] + bar["width"] and abs(ob["y"] - bar["y"]) < 1 and abs(ob["height"] - bar["height"]) < 1 and ob["height"] <= 62
          and page.locator("#pricesView .meta-bar #moverSummary").count() == 0 and summ["y"] >= bar["y"] + bar["height"] and no_hscroll(), (ob, bar, summ))
    page.mouse.wheel(0, 400); page.wait_for_timeout(300)
    ob2 = page.locator("#pricesView .imp-open").bounding_box(); bar2 = page.locator("#pricesView .meta-bar").bounding_box()
    check("price tab, desktop: the bar and the deck price button stay under the top bar together when scrolling", abs((ob2["y"] - bar2["y"]) - (ob["y"] - bar["y"])) < 1 and bar2["y"] < bar["y"], (ob2, bar2, bar))
    page.mouse.wheel(0, -400); page.wait_for_timeout(200)
    if SHOTS: page.screenshot(path="prices_deck_button.png", full_page=False)
    page.click("#pricesView .imp-open"); page.wait_for_selector("#importView .imp-empty")
    check("price tab: the button opens the deck price page, and the tab bar marks 価格",
          "view=import" in page.url and page.locator("#importView").is_visible() and page.locator("#tabPrices").get_attribute("aria-selected") == "true"
          and page.locator("#tabMeta").get_attribute("aria-selected") == "false")
    page.click("#tabPrices"); page.wait_for_selector("#pricesView .imp-open")
    check("deck price page: the 価格 tab goes back to the price movers", "view=prices" in page.url and page.locator("#pricesView").is_visible())
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Gruul%20Dragons"); page.wait_for_selector("#deckBody .deck-group")
    page.wait_for_function("document.querySelector('#deckBody .deck-cost .dcst-v')")
    deck_cost = page.locator("#deckBody .deck-cost .dcst-v").inner_text()
    page.click("#deckBody .deck-edit"); page.wait_for_selector("#importBody .deck-cost .dcst-v")
    check("deck page: 編集して計算 opens the shown list on the deck price page, with the deck's name and the same price",
          page.locator("#importBody .deck-cost .dcst-v").inner_text() == deck_cost and page.input_value("#impName").startswith("グルール・ドラゴン")
          and "Unknown New Card" in page.locator(".imp-miss").inner_text(), (page.locator("#importBody .deck-cost").inner_text(), deck_cost))
    page.goto(SITE + "?view=import"); page.fill("#importText", "4 稲妻\n2 Shivan Dragon\n\nSideboard\n2 Lightning Bolt\n1 Qasali Pridemage"); page.wait_for_selector("#importBody .imp-buy")
    buy = page.locator("#importBody .imp-buy")
    check("deck price page: 晴れる屋で買う links to Hareruya's buy-from-a-list page, in a new tab",
          buy.inner_text().startswith("晴れる屋で買う") and buy.get_attribute("href") == "https://www.hareruyamtg.com/ja/deck/bulk" and buy.get_attribute("target") == "_blank"
          and "noopener" in buy.get_attribute("rel"), buy.evaluate("e => e.outerHTML"))
    with page.context.expect_page() as newtab:
        buy.click()
    newtab.value.close()
    page.wait_for_selector(".imp-buy-note")
    clip = page.evaluate("navigator.clipboard.readText()")
    check("deck price page: the tap copies the whole list (sideboard too, same card added up) in English names and says to paste it there",
          clip == "6 Lightning Bolt\n2 Shivan Dragon\n1 Qasali Pridemage\n" and "貼り付けてください" in page.locator(".imp-buy-note").inner_text(), clip)
    for w in (390, 360):
        page.set_viewport_size({"width": w, "height": 844}); page.wait_for_timeout(250)
        page.click("#importExport summary"); page.wait_for_timeout(250)
        r = page.evaluate("(() => { const b = document.querySelector('#importExport .deck-export-menu').getBoundingClientRect(); return [b.left, b.right, document.documentElement.clientWidth]; })()")
        check(f"phone ({w}px), deck price page: the export menu stays on the screen", r[0] >= 0 and r[1] <= r[2], r)
        page.click("#importExport summary"); page.wait_for_timeout(150)
    page.goto(SITE + "?view=deck&format=standard&days=30&deck=Gruul%20Dragons"); page.wait_for_selector("#deckBody .deck-group")
    page.click("#deckExport summary"); page.wait_for_timeout(250)
    r = page.evaluate("(() => { const b = document.querySelector('#deckExport .deck-export-menu').getBoundingClientRect(); return [b.left, b.right, document.documentElement.clientWidth]; })()")
    check("phone, deck page: the export menu stays on the screen too", r[0] >= 0 and r[1] <= r[2], r)
    page.click("#deckExport summary")
    page.set_viewport_size({"width": 1280, "height": 900}); page.wait_for_timeout(200)
    page.click("#deckExport summary"); page.wait_for_timeout(250)
    r = page.evaluate("(() => { const m = document.querySelector('#deckExport .deck-export-menu').getBoundingClientRect(), b = document.querySelector('#deckExport summary').getBoundingClientRect(); return [m.right, b.right]; })()")
    check("desktop, deck page: the export menu still opens right-aligned under its button", abs(r[0] - r[1]) < 1, r)
    page.click("#deckExport summary")
    page.goto(SITE + "?view=import"); page.wait_for_selector("#importBody .deck-cost")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_timeout(400)
    check("deck price page in English", page.locator(".imp-title").inner_text() == "Price a deck list" and "Main deck" in page.locator("#importBody").inner_text()
          and "Buy at Hareruya" in page.locator("#importBody").inner_text() and page.title().startswith("Price a deck list")
          and page.locator("#impWhich a").all_inner_texts() == ["Want list", "Deck prices"], page.locator("#importBody").inner_text()[:200])
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_timeout(300)
    check("footer: the privacy note says pasted deck lists stay in the browser", "貼り付けたデッキリスト" in page.locator(".attribution").inner_text())
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(300)
    fs = page.evaluate("parseFloat(getComputedStyle(document.getElementById('importText')).fontSize)")
    check("phone, deck price page: no sideways scroll, a 16px box (no zoom on iPhone)", no_hscroll() and fs == 16, fs)
    page.set_viewport_size({"width": 1280, "height": 900})
    PRICE_SITE["dir"] = None
    page.goto(SITE + "?view=import"); page.wait_for_function("document.querySelector('#importBody .deck-cost') && document.querySelector('#importBody .deck-cost').textContent.includes('読み込めませんでした')")
    check("deck price page: without the price files it says so, and still lists the cards", page.locator("#importBody .dl-row, #importBody .deck-card").count() >= 4)
    page.fill("#importText", ""); page.wait_for_timeout(500)
    PRICE_SITE["dir"] = PRICES_FULL

    # ---- 43. the want list: ☆ on results and card pages, the tray, its own list on the deck price page ----
    PRICE_SITE["dir"] = PRICES_FULL
    DB_MODE.update({"present": True, "extra": False, "search": False, "variant": None})
    page.set_viewport_size({"width": 1280, "height": 900})
    home()
    page.evaluate("['warujie-want', 'warujie-want-list', 'warujie-want-view', 'akuchie-view', 'akuchie-lite', 'akuchie-lang', 'akuchie-deck-view'].forEach(k => localStorage.removeItem(k))")
    # a deck pasted before (the live site's deck price page) stays the deck: the want list starts empty
    page.evaluate("localStorage.setItem('warujie-deck-import', '2 Shivan Dragon\\n')"); home()
    listtext = lambda: page.evaluate("localStorage.getItem('warujie-want-list')")
    decktext = lambda: page.evaluate("localStorage.getItem('warujie-deck-import')")
    check("want list: a ☆ button in the top bar that opens a tray, with no count while the list is empty",
          page.locator("#wantBtn").is_visible() and page.evaluate("document.getElementById('wantBtn').tagName") == "BUTTON"
          and page.locator("#wantBtn").get_attribute("aria-expanded") == "false" and not page.locator("#wantN").is_visible())
    check("want list: a deck pasted on the deck price page before is not in it", decktext() == "2 Shivan Dragon\n" and listtext() is None, decktext())
    top_search("稲妻"); page.wait_for_selector("#cardGrid .card-tile .want-tog")
    tog = page.locator("#cardGrid .card-tile[data-id='bolt-ja-m10'] .want-tog, #cardGrid .card-tile .want-tog").first
    check("want list: every search result has a ☆, not pressed yet", tog.get_attribute("aria-pressed") == "false" and tog.get_attribute("aria-label") == "ウォントリストに追加")
    url_before = page.url
    tog.click(); page.wait_for_timeout(200)
    check("want list: the ☆ adds a line to the list (English name and printing) without opening the card, and the top bar counts it",
          page.url == url_before and tog.get_attribute("aria-pressed") == "true" and page.locator("#wantN").inner_text() == "1"
          and listtext() == "1 Lightning Bolt (M10) 146\n" and decktext() == "2 Shivan Dragon\n", listtext())
    check("want list: a note says it was added, with a button to see the list", "ウォントリストに追加しました" in page.locator("#wantToast").inner_text()
          and page.locator("#wantToast button").inner_text() == "リストを見る")
    tog.click(); page.wait_for_timeout(200)
    check("want list: pressing ☆ again takes it out, and offers undo", tog.get_attribute("aria-pressed") == "false" and not page.locator("#wantN").is_visible()
          and listtext() is None and decktext() == "2 Shivan Dragon\n" and page.locator("#wantToast button").inner_text() == "元に戻す")
    page.click("#wantToast button"); page.wait_for_timeout(200)
    check("want list: undo puts it back", tog.get_attribute("aria-pressed") == "true" and page.locator("#wantN").inner_text() == "1" and listtext() == "1 Lightning Bolt (M10) 146\n")
    page.click("#viewToggle [data-view=text]"); page.wait_for_selector("#cardGrid .text-row .want-tog")
    check("want list: the text view's rows have the ☆ too, already pressed for a card in the list",
          page.locator("#cardGrid .text-row .want-tog").first.get_attribute("aria-pressed") == "true")
    page.click("#viewToggle [data-view=image]"); page.wait_for_selector("#cardGrid .card-tile")

    page.goto(SITE + "?card=rag-en-mh2"); page.wait_for_selector("#cpWant .want-tog")
    star = page.locator("#cpWant .want-tog")
    check("want list: the card page has the same ☆ as search results, not pressed yet",
          star.get_attribute("aria-pressed") == "false" and star.get_attribute("aria-label") == "ウォントリストに追加" and star.inner_text().strip() == "")
    star.click(); page.wait_for_timeout(200)
    check("want list: the card page's ☆ adds the card after the others", star.get_attribute("aria-pressed") == "true" and page.locator("#wantN").inner_text() == "2"
          and listtext() == "1 Lightning Bolt (M10) 146\n1 Ragavan, Nimble Pilferer (MH2) 138\n", listtext())
    page.wait_for_selector("#printSlot .print-lang")
    art, box, langs = page.locator("#cardViewCard .cp-art img").first.bounding_box(), page.locator("#cpWant").bounding_box(), page.locator("#printSlot .print-langs").bounding_box()
    check("want list: on the card page it is a row of its own between the picture and the language buttons",
          page.evaluate("document.querySelector('.cp-art').contains(document.getElementById('cpWant'))") and box["y"] > art["y"] + art["height"]
          and langs["y"] >= box["y"] + box["height"], (art, box, langs))
    sz = page.evaluate("""(() => { const w = document.getElementById('cpWant').getBoundingClientRect(), a = document.querySelector('#cardViewCard .cp-art img').getBoundingClientRect(),
        l = document.querySelector('.print-lang'); return [w.width, a.width, w.height, l ? l.getBoundingClientRect().height : 28]; })()""")
    check("want list: on the card page the ☆ row is as wide as the picture and as tall as the language buttons", abs(sz[0] - sz[1]) < 1.5 and abs(sz[2] - sz[3]) < 1.5, sz)
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(250)
    sz = page.evaluate("""(() => { const w = document.getElementById('cpWant').getBoundingClientRect(), a = document.querySelector('#cardViewCard .cp-art img').getBoundingClientRect(),
        l = document.querySelector('.print-lang'); return [w.width, a.width, w.height, l ? l.getBoundingClientRect().height : 26]; })()""")
    order = page.evaluate("(() => { const a = document.querySelector('#cardViewCard .cp-art img').getBoundingClientRect(), w = document.getElementById('cpWant').getBoundingClientRect(), l = document.querySelector('#printSlot .print-langs').getBoundingClientRect(); return [a.bottom, w.top, w.bottom, l.top]; })()")
    check("phone, card page: the ☆ row is as wide as the picture and as tall as the language buttons, between the two",
          abs(sz[0] - sz[1]) < 1.5 and abs(sz[2] - sz[3]) < 1.5 and order == sorted(order), [sz, order])
    page.set_viewport_size({"width": 1280, "height": 900}); page.wait_for_timeout(200)
    star.click(); page.wait_for_timeout(200)
    check("want list: the card page's ☆ again takes the card out, with undo", star.get_attribute("aria-pressed") == "false" and page.locator("#wantN").inner_text() == "1"
          and page.locator("#wantToast button").inner_text() == "元に戻す")
    page.click("#wantToast button"); page.wait_for_timeout(200)
    check("want list: undo brings it back in the same place", star.get_attribute("aria-pressed") == "true" and listtext() == "1 Lightning Bolt (M10) 146\n1 Ragavan, Nimble Pilferer (MH2) 138\n", listtext())

    # the tray
    page.click("#wantBtn"); page.wait_for_selector("#wantTray .wt-row")
    tray = page.locator("#wantTray")
    tb = tray.bounding_box()
    check("tray: the top bar's ☆ opens it from the right, full height, over the page",
          tray.is_visible() and page.locator("#wantBtn").get_attribute("aria-expanded") == "true" and page.locator("#wantTrayBg").is_visible()
          and abs(tb["x"] + tb["width"] - 1280) < 2 and tb["y"] <= 1 and tb["height"] >= 899 and 380 <= tb["width"] <= 430, tb)
    check("tray: its title, how many cards, and each card with − n ＋ and a trash can",
          "ウォントリスト" in tray.locator(".wt-h").inner_text() and "2枚" in tray.locator(".wt-sub").inner_text() and "2種類" in tray.locator(".wt-sub").inner_text()
          and tray.locator(".wt-row").count() == 2 and tray.locator(".wt-row .want-step").count() == 2 and tray.locator(".wt-row .want-trash").count() == 2,
          tray.inner_text()[:300])
    rrow = tray.locator(".wt-row[data-want-row='rag-oracle']")
    page.wait_for_function("document.querySelector(\"#wantTray .wt-row[data-want-row='rag-oracle'] .wt-yen\") && !document.querySelector(\"#wantTray .wt-row[data-want-row='rag-oracle'] .wt-yen\").textContent.includes('最安')", timeout=8000)
    check("tray: the card's Japanese name, its English name and the price of the printing its ☆ line names (MH2 #138: the lower of $40 and €35)",
          "敏捷なこそ泥、ラガバン" in rrow.inner_text() and "Ragavan, Nimble Pilferer" in rrow.inner_text() and rrow.locator(".wt-yen").inner_text() == "¥5,600", rrow.inner_text())
    rrow.locator("[data-want-act=more]").click(); page.wait_for_timeout(150)
    rrow = tray.locator(".wt-row[data-want-row='rag-oracle']")
    check("tray: ＋ adds a copy on the card's line", rrow.locator(".want-c").inner_text() == "2枚" and page.locator("#wantN").inner_text() == "3"
          and listtext() == "1 Lightning Bolt (M10) 146\n2 Ragavan, Nimble Pilferer (MH2) 138\n", listtext())
    rrow.locator("[data-want-act=more]").click(); page.wait_for_timeout(150)
    tray.locator(".wt-row[data-want-row='rag-oracle'] [data-want-act=less]").click(); page.wait_for_timeout(150)
    check("tray: − takes one off", tray.locator(".wt-row[data-want-row='rag-oracle'] .want-c").inner_text() == "2枚" and page.locator("#wantN").inner_text() == "3")
    tray.locator(".wt-row[data-want-row='bolt-oracle'] .want-trash").click(); page.wait_for_timeout(150)
    check("tray: the trash can takes the card out, with undo", tray.locator(".wt-row").count() == 1 and page.locator("#wantToast button").inner_text() == "元に戻す"
          and listtext() == "2 Ragavan, Nimble Pilferer (MH2) 138\n", listtext())
    page.click("#wantToast button"); page.wait_for_timeout(150)
    check("tray: undo puts it back where it was", tray.locator(".wt-row").count() == 2 and listtext() == "1 Lightning Bolt (M10) 146\n2 Ragavan, Nimble Pilferer (MH2) 138\n", listtext())
    tray.locator("[data-tview=image]").click(); page.wait_for_selector("#wantTray .wt-grid .wt-card")
    tile = tray.locator(".wt-card[data-want-row='rag-oracle']")
    pic_box, step_box = tile.locator(".dc-pic").bounding_box(), tile.locator(".want-step").bounding_box()
    check("tray, pictures: two cards a row, the picture with − n ＋ and the trash can under it",
          tray.locator(".wt-card").count() == 2 and tile.locator(".want-c").inner_text() == "2枚" and tile.locator(".want-trash").count() == 1
          and step_box["y"] > pic_box["y"] + pic_box["height"]
          and page.evaluate("getComputedStyle(document.querySelector('#wantTray .wt-grid')).gridTemplateColumns.split(' ').length") == 2, (pic_box, step_box))
    check("tray: the picture view is remembered", page.evaluate("localStorage.getItem('warujie-want-view')") == "image")
    page.keyboard.press("Escape"); page.wait_for_timeout(150)
    check("tray: Esc closes it, and the ☆ button has the focus again", not tray.is_visible() and page.locator("#wantBtn").get_attribute("aria-expanded") == "false"
          and page.evaluate("document.activeElement && document.activeElement.id") == "wantBtn")
    page.click("#wantBtn"); page.wait_for_selector("#wantTray .wt-card")
    page.mouse.click(200, 500); page.wait_for_timeout(150)
    check("tray: a click on the page beside it closes it", not tray.is_visible())
    page.click("#wantBtn"); page.wait_for_selector("#wantTray .wt-card")
    tray.locator("[data-tview=list]").click(); page.wait_for_selector("#wantTray .wt-row")
    page.evaluate("navigator.clipboard.writeText('')")
    buy = tray.locator("[data-thareruya]")
    check("tray: 晴れる屋で買う links to Hareruya's buy-from-a-list page", buy.get_attribute("href") == "https://www.hareruyamtg.com/ja/deck/bulk" and buy.get_attribute("target") == "_blank")
    with page.context.expect_page() as newtab:
        buy.click()
    newtab.value.close()
    page.wait_for_timeout(200)
    clip = page.evaluate("navigator.clipboard.readText()")
    check("tray: 晴れる屋で買う copies the list as plain lines", clip == "1 Lightning Bolt\n2 Ragavan, Nimble Pilferer\n" and "晴れる屋" in page.locator("#wantToast").inner_text(), clip)
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(250)
    tb = tray.bounding_box()
    check("phone, tray: the whole width of the screen, no sideways scroll", abs(tb["width"] - 390) < 2 and tb["x"] < 1 and no_hscroll(), tb)
    page.set_viewport_size({"width": 1280, "height": 900}); page.wait_for_timeout(200)

    # the deck price page shows the want list on ?view=want
    tray.locator(".wt-go").click(); page.wait_for_selector("#importBody .want-bar .dcst-v")
    check("tray: 価格を見る・書き出す opens the want list on the deck price page, and closes the tray",
          page.url.endswith("?view=want") and not tray.is_visible() and page.input_value("#importText") == "1 Lightning Bolt (M10) 146\n2 Ragavan, Nimble Pilferer (MH2) 138\n"
          and page.input_value("#impName") == "" and page.get_attribute("#impName", "placeholder") == "ウォントリスト" and page.locator(".imp-title").inner_text() == "ウォントリスト"
          and page.locator("#impWhich a[aria-current=page]").inner_text() == "ウォントリスト" and page.title().startswith("ウォントリスト — ")
          and page.locator("#tabPrices").get_attribute("aria-selected") == "true",
          page.input_value("#importText"))
    # the lines name M10 #146 ($1.20: ¥180) and MH2 #138 (the lower of $40 and €35: ¥5,600)
    page.wait_for_function("document.querySelector('#importBody .want-bar .dcst-v').textContent === '約¥11,400'", timeout=8000)
    check("deck price page: its total counts the printings the lines name",
          page.locator("#importBody .want-bar .dcst-v").first.inner_text() == "約¥11,400" == page.evaluate("costText(deckCost([[1,'Lightning Bolt'],[2,'Ragavan, Nimble Pilferer']], [180, 5600]))"))
    order = page.evaluate("[...document.querySelector('#importBody .want-bar').querySelectorAll('.dcst-price, .view-toggle, [data-hareruya], #importExport')].map(e => Math.round(e.getBoundingClientRect().left))")
    check("deck price page: the total and リスト/画像 on the left, 晴れる屋で買う and 書き出す on the right, in one bar",
          len(order) == 4 and order == sorted(order) and order[2] > 900, order)
    page.click("#importExport summary"); page.click("#importExport [data-iexport=print]")
    page.wait_for_function("document.querySelector('#importExport [data-iexport=print]').textContent === 'コピーしました'")
    clip = page.evaluate("navigator.clipboard.readText()")
    check("deck price page: copy with printings for Moxfield and Archidekt", clip == "1 Lightning Bolt (M10) 146\n2 Ragavan, Nimble Pilferer (MH2) 138\n", clip)
    page.wait_for_timeout(1300)
    page.click("#importExport summary")
    sites = page.evaluate("[...document.querySelectorAll('#importExport [data-isite]')].map(a => [a.dataset.isite, a.href, a.target, a.rel])")
    check("deck price page: links to Moxfield and Archidekt, in a new tab", sites == [["Moxfield", "https://moxfield.com/decks/personal", "_blank", "noopener"], ["Archidekt", "https://archidekt.com/sandbox", "_blank", "noopener"]], sites)
    page.evaluate("navigator.clipboard.writeText('')")
    with page.context.expect_page() as newtab:
        page.click("#importExport [data-isite=Archidekt]")
    newtab.value.close()
    page.wait_for_selector("#importBody .imp-buy-note")
    clip = page.evaluate("navigator.clipboard.readText()")
    check("deck price page: the deck-site link copies the list with printings and says where to paste it",
          clip == "1 Lightning Bolt (M10) 146\n2 Ragavan, Nimble Pilferer (MH2) 138\n" and "Archidekt" in page.locator("#importBody .imp-buy-note").inner_text(), clip)
    page.fill("#importText", "1 Lightning Bolt (M10) 146\n2 Ragavan, Nimble Pilferer (MH2) 138\n4 稲妻\n"); page.wait_for_timeout(500)
    check("deck price page: editing the text changes the list everywhere (the top bar counts 7)", page.locator("#wantN").inner_text() == "7")
    page.click("#wantBtn"); page.wait_for_selector("#wantTray .wt-row")
    check("tray: the same card on two lines is one card with their copies added up",
          tray.locator(".wt-row").count() == 2 and tray.locator(".wt-row[data-want-row='bolt-oracle'] .want-c").inner_text() == "5枚")
    tray.locator(".wt-row[data-want-row='bolt-oracle'] [data-want-act=less]").click(); page.wait_for_timeout(150)
    check("tray: − comes off the card's last line, and the box on the page follows",
          page.input_value("#importText") == "1 Lightning Bolt (M10) 146\n2 Ragavan, Nimble Pilferer (MH2) 138\n3 稲妻\n", page.input_value("#importText"))
    page.keyboard.press("Escape")
    page.mouse.wheel(0, 0)
    page.set_viewport_size({"width": 1280, "height": 420}); page.wait_for_timeout(200)
    page.evaluate("window.scrollTo(0, document.querySelector('#importBody .deck-section').getBoundingClientRect().top + scrollY - 40)"); page.wait_for_timeout(200)
    bar = page.evaluate("[document.querySelector('#importBody .want-bar').getBoundingClientRect().top, document.querySelector('.topbar').getBoundingClientRect().bottom, scrollY]")
    check("deck price page: the bar stays under the top bar while scrolling", bar[2] > 50 and abs(bar[0] - bar[1]) < 2, bar)
    page.evaluate("window.scrollTo(0, 0)")
    page.set_viewport_size({"width": 1280, "height": 900}); page.wait_for_timeout(200)
    want_now = listtext()
    check("want list: none of it touched the pasted deck", decktext() == "2 Shivan Dragon\n", decktext())
    page.click("#impWhich a[data-which=deck]"); page.wait_for_function("document.querySelector('#impName') && document.querySelector('#impName').placeholder === '貼り付けたデッキ'")
    check("switch: デッキの価格 shows the pasted deck, its title and words, on ?view=import",
          page.url.endswith("?view=import") and page.input_value("#importText") == "2 Shivan Dragon\n" and page.locator(".imp-title").inner_text() == "デッキの価格を調べる"
          and page.locator("#impWhich a[aria-current=page]").inner_text() == "デッキの価格" and page.title().startswith("デッキの価格を調べる")
          and "シヴ山のドラゴン" in page.locator("#importBody").inner_text() and page.locator("#importBody .imp-buy-note").count() == 0,
          page.input_value("#importText"))
    page.fill("#importText", "3 Shivan Dragon\n"); page.wait_for_timeout(500)
    check("switch: editing the deck leaves the want list and its count alone", decktext() == "3 Shivan Dragon\n" and listtext() == want_now and page.locator("#wantN").inner_text() == "6")
    page.go_back(); page.wait_for_selector("#importBody .want-bar .dcst-v")
    check("switch: Back goes to the want list again", page.url.endswith("?view=want") and page.input_value("#importText") == want_now)
    page.goto(SITE + "?view=import&list=" + "4%20Ragavan%2C%20Nimble%20Pilferer"); page.wait_for_selector("#importBody .want-bar")
    check("deck price page: a deck's list or a shared link takes the place of the pasted deck, with undo, and not the want list",
          page.input_value("#importText") == "4 Ragavan, Nimble Pilferer" and page.locator("#wantToast button").inner_text() == "元に戻す" and "入れ替え" in page.locator("#wantToast").inner_text()
          and listtext() == want_now and page.locator("#wantN").inner_text() == "6")
    page.click("#wantToast button"); page.wait_for_timeout(300)
    check("deck price page: undo brings the deck back", page.input_value("#importText") == "3 Shivan Dragon\n" and decktext() == "3 Shivan Dragon\n")
    page.click("#importClear"); page.wait_for_timeout(300)
    check("deck price page: 消す clears the deck only", decktext() is None and listtext() == want_now and page.locator("#wantN").inner_text() == "6")
    page.goto(SITE + "?view=want"); page.wait_for_selector("#importBody .want-bar")
    check("want list: ?view=want opens it directly", page.input_value("#importText") == want_now and page.locator("#impWhich a[aria-current=page]").inner_text() == "ウォントリスト")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_timeout(300)
    page.click("#wantBtn"); page.wait_for_selector("#wantTray .wt-row")
    check("tray in English", "Want list" in tray.locator(".wt-h").inner_text() and tray.locator(".wt-go").inner_text() == "See prices and export"
          and page.locator(".imp-title").inner_text() == "Want list" and page.title().startswith("Want list — ")
          and page.locator("#impWhich a").all_inner_texts() == ["Want list", "Deck prices"], tray.inner_text()[:200])
    page.keyboard.press("Escape")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_timeout(300)
    check("footer: the privacy note says the want list stays in the browser", "ウォントリスト" in page.locator(".attribution").inner_text())
    # the separate list from before (staging only) moves into the text once
    page.evaluate("""localStorage.setItem('warujie-want', JSON.stringify([{o: 'x', n: 'Counterspell', c: 2, id: '', s: '', cn: '', l: ''}]))""")
    page.reload(); page.wait_for_selector("#importBody .want-bar")
    check("want list: a list kept the old way moves into the list once", page.evaluate("localStorage.getItem('warujie-want')") is None
          and "2 Counterspell" in page.input_value("#importText"), page.input_value("#importText"))
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(300)
    check("phone, deck price page: no sideways scroll, the top bar button shows", no_hscroll() and page.locator("#wantBtn").is_visible())
    page.set_viewport_size({"width": 1280, "height": 900}); page.wait_for_timeout(200)
    page.click("#wantBtn"); page.wait_for_selector("#wantTray .wt-row")
    tray.locator(".wt-clear").click()
    check("tray: 全部消す asks for a second tap first", tray.locator(".wt-row").count() >= 2 and tray.locator(".wt-clear").inner_text() == "もう一度押すと全部消えます")
    tray.locator(".wt-clear").click(); page.wait_for_selector("#wantTray .wt-empty")
    check("tray: the second tap empties the list (the page's box too), and the tray says how to add cards", listtext() is None and page.input_value("#importText") == ""
          and not page.locator("#wantN").is_visible() and "☆" in tray.locator(".wt-empty").inner_text())
    page.click("#wantToast button"); page.wait_for_selector("#wantTray .wt-row")
    check("tray: even clearing can be undone", tray.locator(".wt-row").count() >= 2 and page.input_value("#importText") != "")
    page.keyboard.press("Escape")
    page.evaluate("setList('want', '')"); page.wait_for_selector("#importBody .imp-empty")
    check("want list: empty, the page says how to fill it with ☆", "☆" in page.locator("#importBody .imp-empty").inner_text() and page.locator("#importSample").count() == 0)
    page.evaluate("['warujie-deck-import', 'warujie-want-list', 'warujie-want-view'].forEach(k => localStorage.removeItem(k))")

    # ---- 44. everyday words: slang inside a sentence, words the cards say differently, a creature type beside ロード ----
    ev = page.evaluate("""(() => {
      const f = q => { const u = prepareJapanese([q])[0]; return { chunks: u.chunks, alts: u.alts.map(a => a.n), to: u.alias && u.alias.to }; };
      const keep = [CREATURE_TYPE_WORDS, tagsState]; CREATURE_TYPE_WORDS = new Set(['エルフ', 'elf', 'ロード']); tagsState = 'ready';
      const roles = ['エルフ ロード', 'エルフロード', 'エルフのロード', 'ロード', 'elf lord', '騎士ロード'].map(q => parseSearch(q).roles.map(r => r.id).join(','));
      [CREATURE_TYPE_WORDS, tagsState] = keep;
      return { etb: f('ETBでカードを引く'), dies: f('死亡時にカードを引く'), when: f('戦場に出たときトークン'), drain: f('クリーチャーが死ぬたびにドレイン'),
        words: ['シャッフル', 'ディスカード', 'ミル', 'ミルコ', '3枚ミル', 'レジェンド', '奪う', 'パクる', 'インスタントタイミング', 'パートナー', 'トランプル付与', '飛行を与える',
                'コストが1少なくなる', '2マナ安く', 'ドローを禁止'].map(q => f(q).to), roles, kw: JA_KEYWORDS['共闘'] };
    })()""")
    check("slang inside a sentence: ETBでカードを引く, 死亡時に, ドレイン read as the cards' words",
          ev["etb"]["to"] == "戦場に出たときカードを引く" and ev["dies"]["alts"][:2] == ["死亡したときカードを引く", "死亡するたびカードを引く"]
          and ev["drain"]["to"] == "クリーチャーが死亡するたびにライフを失", (ev["etb"], ev["dies"], ev["drain"]))
    check("とき and たび end a part: 戦場に出たときトークン is 戦場・出・トークン", ev["when"]["chunks"] == ["戦場", "出", "トークン"], ev["when"])
    check("words the cards say differently: シャッフル, ディスカード, ミル (not ミルコ), レジェンド, 奪う, パートナー, X付与, 1マナ安く, ドローを禁止",
          ev["words"] == ["ライブラリーを切り直す", "捨てる", "切削", None, "3つ切削", "伝説の", "コントロールを得る", "コントロールを得る", "瞬速", "共闘",
                          "トランプルを得る", "飛行を得る", "コストが{1}少なくなる", "{2}少なく", "引くことができない"] and ev["kw"] == "partner", ev["words"])
    check("ロード beside a creature type is the lord role (エルフ ロード, エルフロード, elf lord); alone it stays a word",
          ev["roles"] == ["lord", "lord", "lord", "", "lord", ""], ev["roles"])

    # ---- 45. the printings in the database: e: finds every card printed in a set; ボーダーレス, 旧枠, 日本語版 ----
    DB_MODE["variant"] = "prints"
    # earlier sections leave the text view (and other choices) saved; these checks count picture tiles
    page.evaluate("['akuchie-view', 'akuchie-lite', 'akuchie-lang', 'akuchie-deck-view'].forEach(k => localStorage.removeItem(k))")
    home()
    names_on = lambda: sorted(page.locator("#cardGrid .card-name-main").all_inner_texts())
    def found(q, n):
        top_search(q)
        page.wait_for_function("document.querySelector('#resultCount').textContent.includes('件見つかりました')")
        page.wait_for_function(f"document.querySelectorAll('#cardGrid .card-tile').length === {n}")
        return names_on()
    for q, want in (("e:mul", ["敏捷なこそ泥、ラガバン"]), ("e:mh2", ["ウルザの物語", "敏捷なこそ泥、ラガバン"]),
                    ("e:lea", ["シヴ山のドラゴン", "ラノワールのエルフ", "稲妻"]), ("セット:モダンホライゾン2", ["ウルザの物語", "敏捷なこそ泥、ラガバン"]),
                    ("ボーダーレス", ["English Only Thing", "シヴ山のドラゴン", "敏捷なこそ泥、ラガバン"]), ("日本語版 ボーダーレス", ["シヴ山のドラゴン"]),
                    ("is:showcase", ["敏捷なこそ泥、ラガバン"]), ("旧枠", ["シヴ山のドラゴン", "ラノワールのエルフ", "稲妻"]),
                    ("日本語版 旧枠", ["稲妻"]), ("lang:ja is:oldframe", ["稲妻"]), ("extended art", ["ウルザの物語"]), ("拡張アート", ["ウルザの物語"]),
                    ("-日本語版", ["English Only Thing"]), ("旧枠 ドラゴン", ["シヴ山のドラゴン"])):
        check(f"printings: {q} finds the cards with such a printing", found(q, len(want)) == sorted(want), names_on())
    found("lang:ja", 6)
    check("printings: lang:ja finds every card printed in Japanese", "English Only Thing" not in names_on(), names_on())
    found("ボーダーレス", 3)
    check("printings: the note says what ボーダーレス did", "「ボーダーレス」でボーダーレス版のあるカードに絞り込みました。" in page.locator("#matchNote").inner_text(),
          page.locator("#matchNote").inner_text())
    found("日本語版 ボーダーレス", 1)
    check("printings: beside 日本語版 the note says a Japanese borderless printing", "日本語のボーダーレス版のあるカード" in page.locator("#matchNote").inner_text(),
          page.locator("#matchNote").inner_text())
    DB_MODE["variant"] = None
    home()
    found("e:m10", 4)
    check("printings: an older database without the fields still finds e:m10 by the shown printing's set",
          names_on() == sorted(["クァーサルの群れ魔道士", "シヴ山のドラゴン", "ラノワールのエルフ", "稲妻"]), names_on())

    # the card page's language buttons from the printings file: no Scryfall search, the other language fetched when pressed
    PRINTINGS_MODE["file"] = True
    n0 = len(calls)
    page.goto(SITE + "?card=rag-ja-mh2"); page.wait_for_selector("#printSlot .print-lang")
    labels = page.locator("#printSlot .print-lang").all_inner_texts()
    check("printings file: the language buttons come from the file (JP EN FR DE), without a Scryfall search",
          labels == ["JP", "EN", "FR", "DE"] and not any("include_multilingual" in c for c in calls[n0:]), (labels, [c for c in calls[n0:] if "scryfall" in c]))
    page.click("#printSlot [data-print=fr]")
    page.wait_for_function("location.search.includes('card=rag-fr-mh2') && location.search.includes('print=fr')")
    page.wait_for_selector("#printSlot [data-print=fr][aria-pressed=true]")
    check("printings file: FR fetches that one printing and shows it in French", "LANG-LOOKUP /cards/mh2/138/fr" in calls[n0:]
          and page.locator(".cp-name").inner_text() == "Ragavan, chapardeur agile" and page.locator("#printSlot .print-lang").all_inner_texts() == ["JP", "EN", "FR", "DE"],
          (page.locator(".cp-name").inner_text(), [c for c in calls[n0:] if "LOOKUP" in c]))
    page.click("#printSlot [data-print=ja]")
    page.wait_for_function("location.search.includes('card=rag-ja-mh2') && location.search.includes('print=ja')")
    page.wait_for_selector("#printSlot [data-print=ja][aria-pressed=true]")
    check("printings file: JP goes back to the Japanese printing", page.locator(".cp-name").inner_text() == "敏捷なこそ泥、ラガバン")
    page.goto(SITE + "?card=arma-ja-4bb"); page.wait_for_selector("#printSlot .print-lang")
    check("printings file: Japanese 4th Edition (4bb) lists the English 4th Edition", page.locator("#printSlot .print-lang").all_inner_texts() == ["JP", "EN", "DE"],
          page.locator("#printSlot .print-lang").all_inner_texts())
    page.click("#printSlot [data-print=en]")
    page.wait_for_function("location.search.includes('card=arma-en-4ed')"); page.wait_for_selector("#printSlot [data-print=en][aria-pressed=true]")
    check("printings file: EN there opens the English 4th Edition (4ed), never Masters 25", "LANG-LOOKUP /cards/4ed/4/en" in calls[n0:]
          and page.locator("#printSlot .print-lang").all_inner_texts() == ["JP", "EN", "DE"])
    n1 = len(calls)
    page.goto(SITE + "?card=rag-ja-mul"); page.wait_for_selector("#printSlot .print-lang")
    ids = page.evaluate("Object.fromEntries([...document.querySelectorAll('#printSlot .print-lang')].map(b => [b.dataset.print, b.dataset.id]))")
    check("printings file: a printing the file doesn't have yet asks Scryfall as before", ids == {"ja": "rag-ja-mul", "en": "rag-en-mul", "fr": "rag-fr-mul"}
          and any("include_multilingual" in c for c in calls[n1:]), ids)
    check("printings file: fetched at most once per page load", sum(1 for c in calls[n0:] if c.endswith("/printings.json.gz")) <= 3,
          sum(1 for c in calls[n0:] if c.endswith("/printings.json.gz")))
    PRINTINGS_MODE["file"] = False

    # ---- 46. after the database check (2026-10-17): printing words as players write them, set names in part,
    # reminder text, English "Japanese" texts, English pages on English printings, ordinals ----
    DB_MODE["variant"] = "prints"
    home()
    for q, want in (("ボーダーレス版", ["English Only Thing", "シヴ山のドラゴン", "敏捷なこそ泥、ラガバン"]), ("ショーケース版あり", ["敏捷なこそ泥、ラガバン"]),
                    ("旧枠のドラゴン", ["シヴ山のドラゴン"]), ("日本語版のボーダーレス", ["シヴ山のドラゴン"]),
                    ("セット:ホライゾン", ["ウルザの物語", "敏捷なこそ泥、ラガバン"])):
        check(f"printing words: {q} reads as the printing word", found(q, len(want)) == sorted(want), names_on())
    found("ボーダーレス版", 3)
    check("printing words: the note names the word as typed (ボーダーレス版)", "「ボーダーレス版」でボーダーレス版のあるカードに絞り込みました。" in page.locator("#matchNote").inner_text(),
          page.locator("#matchNote").inner_text())
    found("日本語版のカード", 6)
    check("printing words: 日本語版のカード finds every card printed in Japanese", "English Only Thing" not in names_on(), names_on())
    pw = page.evaluate("""(() => { const p = q => { const r = parseSearch(q); return [r.filters.length, r.ja.length + r.words.length]; };
      return { serial: p('シリアル番号'), dragon: p('ボーダーレスのドラゴン'), plain: p('旧枠組み'), lang: p('日本語の勉強'), card: p('ボーダーレスのカード') }; })()""")
    check("printing words: シリアル番号 and ボーダーレスのカード are filters alone; ボーダーレスのドラゴン a filter and a word; other words stay words",
          pw == {"serial": [1, 0], "dragon": [1, 1], "plain": [0, 1], "lang": [0, 1], "card": [1, 0]}, pw)
    rm = page.evaluate("""(() => {
      const mk = o => indexRow(LOCAL_FIELDS.map(f => (o[f] === undefined ? '' : o[f])));
      const flyer = mk({ id: 'rm-1', oracle_id: 'rm-o1', name_en: 'Reminder Flyer', name_ja: '注釈の鳥', type_ja: 'クリーチャー — 鳥', type_en: 'Creature — Bird', keywords: 'Flying',
        oracle_en: 'Flying', oracle_ja: '飛行（このクリーチャーは飛行や到達を持たないクリーチャーによってはブロックされない。）' });
      const reach = mk({ id: 'rm-2', oracle_id: 'rm-o2', name_en: 'Reach Spider', name_ja: '注釈の蜘蛛', type_ja: 'クリーチャー — 蜘蛛', type_en: 'Creature — Spider', keywords: 'Reach',
        oracle_en: 'Reach', oracle_ja: '到達' });
      const said = mk({ id: 'rm-3', oracle_id: 'rm-o3', name_en: 'Said Bird', name_ja: '注釈の鷹', type_ja: 'クリーチャー — 鳥', type_en: 'Creature — Bird', keywords: 'Flying',
        oracle_en: 'Flying', oracle_ja: '飛行（このクリーチャーは飛行や到達を持たないクリーチャーによってはブロックされない。）\\nあなたがコントロールしているクリーチャーは到達を持つ。' });
      const eng = mk({ id: 'rm-4', oracle_id: 'rm-o4', name_en: 'English Text', name_ja: '英語の文', type_ja: 'Sorcery', type_en: 'Sorcery', oracle_en: 'Draw a card.', oracle_ja: 'Draw a card.' });
      const sc = (row, q) => { const r = evaluateRow(row, buildSearchPlan(q)); return r ? r.score : null; };
      return { flyer: sc(flyer, '到達'), reach: sc(reach, '到達'), said: sc(said, '到達'), fly: sc(flyer, '飛行'), two: sc(flyer, '到達 飛行'), twoSaid: sc(said, '到達 飛行'),
        eng: [eng.oracle_ja, eng.type_ja], ja: [reach.oracle_ja, reach.type_ja] }; })()""")
    check("reminder text: a word only in （…） scores after the cards whose own text or keyword has it (到達 in 飛行's reminder)",
          rm["flyer"] == 1.5 and rm["reach"] == 1 and rm["said"] == 1 and rm["fly"] == 1 and rm["two"] == 1.5 and rm["twoSaid"] == 1, rm)
    check("a Japanese text or type line that is English counts as none (Edge of Eternities)", rm["eng"] == ["", ""] and rm["ja"] == ["到達", "クリーチャー — 蜘蛛"], rm)
    pl = page.evaluate("['3st Place', '2st Place', '22th Place', '11st Place', '1st Place', '103rd Place', 'Top 8', ''].map(placeText)")
    check("metagame: a finish with a wrong ordinal from the source reads right (3st -> 3rd, 22th -> 22nd)",
          pl == ["3rd Place", "2nd Place", "22nd Place", "11th Place", "1st Place", "103rd Place", "Top 8", ""], pl)
    DB_MODE["variant"] = None

    # English: a link to a Japanese printing opens the English card of that printing (the printings file says there is one)
    PRINTINGS_MODE["file"] = True
    page.evaluate("setLang('en', true)")
    n0 = len(calls)
    page.goto(SITE + "?card=rag-ja-mh2"); page.wait_for_function("location.search.includes('card=rag-en-mh2')")
    page.wait_for_selector("#printSlot [data-print=en][aria-pressed=true]")
    check("English: a link to the Japanese printing opens the same printing in English", "LANG-LOOKUP /cards/mh2/138/en" in calls[n0:]
          and page.locator(".cp-name").inner_text() == "Ragavan, Nimble Pilferer" and "print=" not in page.url, (page.url, page.locator(".cp-name").inner_text()))
    page.click("#printSlot [data-print=ja]")
    page.wait_for_function("location.search.includes('card=rag-ja-mh2') && location.search.includes('print=ja')")
    page.wait_for_selector("#printSlot [data-print=ja][aria-pressed=true]")
    check("English: JP still shows the Japanese printing when asked for", page.locator(".cp-name").inner_text() == "敏捷なこそ泥、ラガバン", page.locator(".cp-name").inner_text())
    page.goto(SITE + "?card=rag-ja-mh2&print=ja"); page.wait_for_selector("#printSlot [data-print=ja][aria-pressed=true]")
    check("English: a link with print=ja keeps the Japanese printing", "card=rag-ja-mh2" in page.url and page.locator(".cp-name").inner_text() == "敏捷なこそ泥、ラガバン")
    page.goto(SITE + "?card=rag-ja-mul"); page.wait_for_selector("#printSlot .print-lang"); page.wait_for_timeout(300)
    check("English: a printing the file doesn't list in English stays as it is", "card=rag-ja-mul" in page.url, page.url)
    home(); page.wait_for_function("document.querySelector('#hxList a.hx-item img')")
    hx = [a.get_attribute("data-card") for a in page.locator("#hxList a.hx-item").all()]
    has_en = lambda i: any(c["lang"] == "en" and c["oracle_id"] == BY_ID[i]["oracle_id"] for c in CARDS) if i in BY_ID else False
    check("English home: the effect examples link to the English printing they picture", hx and all(BY_ID.get(i, {}).get("lang") == "en" or not has_en(i) for i in hx),
          [(i, BY_ID.get(i, {}).get("lang")) for i in hx])
    page.evaluate("setLang('ja', true)")
    page.goto(SITE + "?card=rag-ja-mh2"); page.wait_for_selector("#printSlot [data-print=ja][aria-pressed=true]")
    check("Japanese: the Japanese printing stays", "card=rag-ja-mh2" in page.url and page.locator(".cp-name").inner_text() == "敏捷なこそ泥、ラガバン")
    PRINTINGS_MODE["file"] = False

    # ---- 47. the deck price page's picture view: − n ＋ and the art picker under each card ----
    page.set_viewport_size({"width": 1280, "height": 900})
    page.evaluate("['warujie-deck-import', 'akuchie-deck-view', 'akuchie-lang'].forEach(k => localStorage.removeItem(k))")
    page.evaluate("localStorage.setItem('warujie-deck-import', '4 Ragavan, Nimble Pilferer\\nLightning Bolt x2\\n\\nSideboard\\n1 Lightning Bolt\\n')")
    page.goto(SITE + "?view=import"); page.wait_for_selector("#importBody .want-bar")
    page.click("#importBody [data-iview='image']"); page.wait_for_selector("#importBody .imp-card")
    cards = page.locator("#importBody .imp-card")
    check("picture view: every card has − n ＋ and an art button under it",
          cards.count() == 3 and page.locator("#importBody .imp-act .want-c").all_inner_texts() == ["4枚", "2枚", "1枚"]
          and page.locator("#importBody .imp-act .imp-art").count() == 3, page.locator("#importBody .imp-act .want-c").all_inner_texts())
    check("picture view: the buttons sit under the picture, inside the card's width",
          page.evaluate("[...document.querySelectorAll('#importBody .imp-card')].every(c => { const p = c.querySelector('.dc-pic').getBoundingClientRect(), a = c.querySelector('.imp-act').getBoundingClientRect(); return a.top >= p.bottom && a.left >= p.left - 1 && a.right <= p.right + 1; })"))
    rag = "#importBody [data-ip='main'][data-in='Ragavan, Nimble Pilferer']"
    page.click(rag + "[data-imp-act='more']"); page.wait_for_timeout(250)
    check("＋ under a card adds one to its line, the box follows, and the focus stays on ＋",
          page.input_value("#importText").startswith("5 Ragavan, Nimble Pilferer\n") and page.locator(rag + "[data-imp-act='more']").evaluate("b => b === document.activeElement")
          and "×5" in page.locator("#importBody .imp-card").first.inner_text(), page.input_value("#importText"))
    page.click("#importBody [data-ip='main'][data-in='Lightning Bolt'][data-imp-act='less']"); page.wait_for_timeout(250)
    check("− changes that part only, the way the line was written (Bolt x2 → x1; the sideboard's stays)",
          page.input_value("#importText") == "5 Ragavan, Nimble Pilferer\nLightning Bolt x1\n\nSideboard\n1 Lightning Bolt\n", page.input_value("#importText"))
    page.click("#importBody [data-ip='side'][data-in='Lightning Bolt'][data-imp-act='less']"); page.wait_for_timeout(250)
    check("− on the last copy takes the card out, with undo", "Sideboard\n1 Lightning Bolt" not in page.input_value("#importText")
          and page.locator("#importBody .imp-card").count() == 2 and page.locator("#wantToast button").inner_text() == "元に戻す")
    page.click("#wantToast button"); page.wait_for_timeout(300)
    check("undo brings it back", page.input_value("#importText").endswith("Sideboard\n1 Lightning Bolt\n") and page.locator("#importBody .imp-card").count() == 3)
    n_calls = len(calls)
    page.click(rag + "[data-imp-act='art']"); page.wait_for_selector("#artPicker .ap-item")
    pick = page.locator("#artPicker")
    check("art button: opens a picker over the page with every printing, newest first",
          pick.is_visible() and pick.get_attribute("role") == "dialog" and "絵柄を選ぶ" in pick.locator(".wt-h").inner_text()
          and pick.locator(".ap-item").count() == 3 and "MUL #21" in pick.locator(".ap-item").first.inner_text(), pick.inner_text()[:300])
    check("art picker: one Scryfall search for the printings and one for the Japanese ones",
          sum("/cards/search" in c and "oracleid" in urllib.parse.unquote_plus(c) for c in calls[n_calls:]) == 2, calls[n_calls:])
    check("art picker: Japanese printings say so, prices show, the picture shown now is marked",
          pick.locator(".ap-item .print-tag.ja").count() == 2 and "¥8,250" in pick.inner_text()
          and pick.locator(".ap-item.current").count() == 1 and "#138" in pick.locator(".ap-item.current").inner_text()
          and "選択中" in pick.locator(".ap-item.current").inner_text())
    pick.locator(".ap-item", has_text="#345").click(); page.wait_for_timeout(300)
    check("picking a printing writes it on the card's line and closes the picker",
          page.input_value("#importText").startswith("5 Ragavan, Nimble Pilferer (MH2) 345\n") and not pick.is_visible()
          and not page.evaluate("document.documentElement.classList.contains('art-open')"), page.input_value("#importText"))
    first = page.locator("#importBody .imp-card").first
    check("the card shows the picked art and opens that printing, with undo, and the focus is back on its art button",
          "rag-en-mh2-bl" in first.locator(".dc-pic img").get_attribute("src") and first.locator("a.deck-card").get_attribute("data-card") == "rag-en-mh2-bl"
          and "絵柄を変えました" in page.locator("#wantToast").inner_text()
          and page.locator(rag + "[data-imp-act='art']").evaluate("b => b === document.activeElement"))
    page.click(rag + "[data-imp-act='art']"); page.wait_for_selector("#artPicker .ap-item.current")
    check("art picker: the printing picked is the one marked", "#345" in pick.locator(".ap-item.current").inner_text())
    page.keyboard.press("Escape"); page.wait_for_timeout(150)
    check("art picker: Esc closes it and the focus goes back", not pick.is_visible() and page.locator(rag + "[data-imp-act='art']").evaluate("b => b === document.activeElement"))
    page.click(rag + "[data-imp-act='art']"); page.wait_for_selector("#artPicker .ap-item")
    page.mouse.click(5, 5); page.wait_for_timeout(150)
    check("art picker: a tap beside it closes it", not pick.is_visible())
    n_calls = len(calls)
    page.reload(); page.wait_for_selector("#importBody .imp-card")
    page.wait_for_function("document.querySelector('#importBody .imp-card .dc-pic img') && document.querySelector('#importBody .imp-card .dc-pic img').src.includes('rag-en-mh2-bl')", timeout=8000)
    later = calls[n_calls:]
    check("after a reload the card still shows the picked art: the Japanese printings asked in one search, the rest by set and number",
          sum("/cards/search" in c and "lang%3Aja+%28" in c for c in later) == 1 and sum("/cards/collection" in c for c in later) >= 1, later)
    page.click("#wantBtn"); page.wait_for_selector("#wantTray .wt-empty")
    check("tray: the pasted deck is not in it", "☆" in page.locator("#wantTray .wt-empty").inner_text())
    page.keyboard.press("Escape")
    page.evaluate("setList('want', '1 Ragavan, Nimble Pilferer (MH2) 345\\n')")
    page.click("#wantBtn"); page.wait_for_selector("#wantTray .wt-row")
    page.wait_for_function("[...document.querySelectorAll('#wantTray .wt-row img')].some(i => i.src.includes('rag-en-mh2-bl'))", timeout=5000)
    check("tray: a want list line with a printing shows that printing's picture", page.input_value("#importText").startswith("5 Ragavan, Nimble Pilferer (MH2) 345\n"))
    page.keyboard.press("Escape")
    page.goto(SITE + "?view=want"); page.wait_for_selector("#importBody .imp-card")
    page.click(rag + "[data-imp-act='more']"); page.wait_for_timeout(250)
    check("want list page: ＋ under a card changes the want list (the top bar counts it) and not the deck",
          listtext() == "2 Ragavan, Nimble Pilferer (MH2) 345\n" and page.locator("#wantN").inner_text() == "2"
          and decktext().startswith("5 Ragavan, Nimble Pilferer (MH2) 345\n"), listtext())
    page.click(rag + "[data-imp-act='art']"); page.wait_for_selector("#artPicker .ap-item")
    pick.locator(".ap-item", has_text="#138").click(); page.wait_for_timeout(300)
    check("want list page: the art picker writes on the want list", listtext() == "2 Ragavan, Nimble Pilferer (MH2) 138\n" and decktext().startswith("5 Ragavan, Nimble Pilferer (MH2) 345\n"), listtext())
    page.evaluate("setList('want', '')")
    page.goto(SITE + "?view=import"); page.wait_for_selector("#importBody .imp-card")
    page.click("#importBody [data-ip='main'][data-in='Lightning Bolt'][data-imp-act='art']"); page.wait_for_selector("#artPicker .ap-item")
    check("art picker: a Japanese printing with no real scan shows the English picture",
          "bolt-en-m10" in (pick.locator(".ap-item img").first.get_attribute("src") or ""), pick.locator(".ap-item img").first.get_attribute("src"))
    pick.locator(".ap-item").first.click(); page.wait_for_timeout(300)
    check("picking keeps a count written last: Lightning Bolt (M10) 146 x1", "\nLightning Bolt (M10) 146 x1\n" in page.input_value("#importText")
          and page.locator("#importBody .imp-act .want-c").all_inner_texts()[:2] == ["5枚", "1枚"], page.input_value("#importText"))
    ok = page.evaluate("""() => {
      const cases = [['4 稲妻', 'mh2', '345', '4 稲妻 (MH2) 345'],
        ['1 Ragavan, Nimble Pilferer (MH2) 138 *F*', 'mul', '21', '1 Ragavan, Nimble Pilferer (MUL) 21 *F*'],
        ['1x Lightning Bolt (2X2) 117 [Burn]', 'm10', '146', '1x Lightning Bolt (M10) 146 [Burn]'],
        ['SB: 2 Lightning Bolt', 'sta', '42', 'SB: 2 Lightning Bolt (STA) 42'],
        ['1 Ragavan, Nimble Pilferer', 'war', '1★', '1 Ragavan, Nimble Pilferer (WAR) 1★']];
      return cases.map(([raw, s, cn, want]) => {
        const got = lineWithPrint(raw, s, cn), l = parseDeckText(got).lines[0];
        return got === want && l.s === s && l.cn === cn ? 'ok' : got + ' / ' + JSON.stringify(l);
      });
    }""")
    check("lineWithPrint: the printing goes on the line, which still reads the same (foil mark, Archidekt category, SB:, ★ numbers)", ok == ["ok"] * 5, ok)
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(300)
    check("phone, picture view: three cards across that don't overlap, the buttons fit under each, no sideways scroll",
          no_hscroll() and page.evaluate("[...document.querySelectorAll('#importBody .imp-act')].every(a => a.scrollWidth <= a.clientWidth + 1 && a.getBoundingClientRect().right <= a.closest('.imp-card').getBoundingClientRect().right + 1)")
          and page.evaluate("""(() => { const r = [...document.querySelectorAll('#importBody .imp-card')].map(c => c.getBoundingClientRect());
            const w = (document.documentElement.clientWidth - 32) / 3 + 1;
            return r.length > 0 && r.every(x => x.width <= w && x.right <= document.documentElement.clientWidth - 8)
              && r.every((x, i) => r.every((y, j) => i === j || x.right <= y.left || y.right <= x.left || x.bottom <= y.top || y.bottom <= x.top)); })()"""))
    page.click(rag + "[data-imp-act='art']"); page.wait_for_selector("#artPicker .ap-item")
    box = page.evaluate("(() => { const r = document.getElementById('artPicker').getBoundingClientRect(); return [r.left, r.right, r.bottom, innerWidth, innerHeight]; })()")
    cols = page.evaluate("getComputedStyle(document.querySelector('#artPicker .ap-grid')).gridTemplateColumns.split(' ').length")
    check("phone: the picker is a sheet from the bottom, three printings across", abs(box[0]) < 1 and abs(box[1] - box[3]) < 1 and abs(box[2] - box[4]) < 1 and cols == 3 and no_hscroll(), [box, cols])
    page.keyboard.press("Escape")
    page.set_viewport_size({"width": 1280, "height": 900}); page.wait_for_timeout(200)
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_selector("#importBody .imp-card")
    page.click(rag + "[data-imp-act='art']"); page.wait_for_selector("#artPicker .ap-item")
    check("English: the picker and the buttons in English", "Choose the art" in pick.inner_text() and pick.locator(".ap-item .print-tag.ja").count() == 0
          and page.locator(rag + "[data-imp-act='art']").get_attribute("aria-label") == "Change the art of Ragavan, Nimble Pilferer", pick.inner_text()[:200])
    page.keyboard.press("Escape")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_timeout(300)
    page.evaluate("['warujie-deck-import', 'warujie-want-list', 'akuchie-deck-view'].forEach(k => localStorage.removeItem(k))")
    # ---- 48. the list's name in a box to type in; − n ＋ and the art button in the list view too ----
    page.set_viewport_size({"width": 1280, "height": 900})
    page.evaluate("['warujie-deck-import', 'warujie-want-list', 'akuchie-deck-view', 'akuchie-lang'].forEach(k => localStorage.removeItem(k))")
    page.evaluate("localStorage.setItem('warujie-want-list', '1 Lightning Bolt (M10) 146\\n2 Ragavan, Nimble Pilferer (MH2) 138\\n')")
    page.evaluate("localStorage.setItem('akuchie-deck-view', 'list')")
    page.goto(SITE + "?view=want"); page.wait_for_selector("#importBody .imp-row")
    nm = page.locator("#impName")
    box = page.evaluate("(() => { const i = document.getElementById('impName'), c = getComputedStyle(i); return [i.tagName, i.type, c.borderTopStyle, parseFloat(c.borderTopWidth), document.querySelector('.imp-name svg') ? 1 : 0, i.getBoundingClientRect().height]; })()")
    check("name box: the list's name is a text box with a border and a pen, showing ウォントリスト until it has a name",
          box[:3] == ["INPUT", "text", "solid"] and box[3] >= 1 and box[4] == 1 and box[5] >= 40 and nm.input_value() == "" and nm.get_attribute("placeholder") == "ウォントリスト"
          and nm.get_attribute("aria-label") == "リストの名前", box)
    nm.click(); page.keyboard.type("モダン用"); page.wait_for_timeout(900)
    check("name box: typing writes the name on top of the list, as MTG Arena does (About / Name), and the box keeps the focus through the redraw",
          page.input_value("#importText") == "About\nName モダン用\n\n1 Lightning Bolt (M10) 146\n2 Ragavan, Nimble Pilferer (MH2) 138\n"
          and page.evaluate("document.activeElement && document.activeElement.id") == "impName" and nm.input_value() == "モダン用"
          and page.evaluate("localStorage.getItem('warujie-want-list')").startswith("About\nName モダン用\n"), page.input_value("#importText"))
    check("name box: the cards still read the same with the name on top", page.locator("#importBody .imp-row").count() == 2 and page.locator("#wantN").inner_text() == "3")
    # Japanese input: nothing changes while a word is being converted, the whole word goes in at the end
    page.evaluate("""(() => { const i = document.getElementById('impName'); i.value = 'モダン用の'; i.dispatchEvent(new InputEvent('input', { bubbles: true, isComposing: true })); })()""")
    page.wait_for_timeout(150)
    composing = page.input_value("#importText").split("\n")[1]
    page.evaluate("(() => { const i = document.getElementById('impName'); i.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true, data: 'の' })); })()")
    page.wait_for_timeout(150)
    check("name box: while Japanese is being converted the list waits, then takes the word", composing == "Name モダン用" and page.input_value("#importText").split("\n")[1] == "Name モダン用の", composing)
    page.keyboard.press("Enter"); page.wait_for_timeout(800)
    check("name box: Enter finishes, and the name stays after the page is drawn again",
          page.evaluate("document.activeElement && document.activeElement.id") != "impName" and nm.input_value() == "モダン用の")
    page.click("#wantBtn"); page.wait_for_selector("#wantTray .wt-row")
    check("tray: its title is the want list's name", tray.locator(".wt-h").inner_text().strip() == "モダン用の", tray.locator(".wt-h").inner_text())
    page.keyboard.press("Escape")
    page.goto(SITE + "?card=elf-ja"); page.wait_for_selector("#cpWant .want-tog")
    page.click("#cpWant .want-tog"); page.wait_for_timeout(200)
    check("name box: a ☆ adds the card under the name, not into it", listtext().startswith("About\nName モダン用の\n\n1 Lightning Bolt") and "Llanowar Elves" in listtext()
          and page.locator("#wantN").inner_text() == "4", listtext())
    page.goto(SITE + "?view=want"); page.wait_for_selector("#importBody .imp-row")
    page.click("#importExport summary"); page.click("#importExport [data-iexport=link]")
    page.wait_for_function("document.querySelector('#importExport [data-iexport=link]').textContent === 'コピーしました'")
    link = page.evaluate("navigator.clipboard.readText()")
    check("name box: the link that carries the list carries its name", "About%0AName%20%E3%83%A2%E3%83%80%E3%83%B3" in link, link[:160])
    page.wait_for_timeout(1300)
    nm.fill(""); page.wait_for_timeout(800)
    check("name box: emptying it takes the name lines out and shows ウォントリスト again",
          page.input_value("#importText").startswith("1 Lightning Bolt (M10) 146\n") and "About" not in page.input_value("#importText") and nm.get_attribute("placeholder") == "ウォントリスト")
    ok = page.evaluate("""() => {
      const r = [];
      r.push(textWithName('4 稲妻\\n', 'Burn') === 'About\\nName Burn\\n\\n4 稲妻\\n');
      r.push(textWithName('About\\nName Burn\\n\\n4 稲妻\\n', 'Red') === 'About\\nName Red\\n\\n4 稲妻\\n');
      r.push(textWithName('About\\nName Burn\\n\\nDeck\\n4 稲妻\\n', '') === 'Deck\\n4 稲妻\\n');
      const p = parseDeckText('About\\nName Burn\\n\\n4 Lightning Bolt\\n20 Mountain\\n\\n2 Shivan Dragon');
      r.push(p.title === 'Burn' && p.lines.map(l => l.part).join() === 'main,main,side');
      const w = parseDeckText(withLineAdded('About\\nName Burn\\n', '1 Lightning Bolt'));
      r.push(w.title === 'Burn' && w.lines.length === 1 && w.lines[0].part === 'main');
      return r;
    }""")
    check("name lines: written and taken out as Arena writes them; a name on top keeps the MTGO sideboard rule; a ☆ on a list with only a name lands under it",
          ok == [True] * 5, ok)
    # the list view: the same buttons as under the pictures
    rows = page.locator("#importBody .imp-row")
    check("list view: every row has − n ＋ in place of the count, and the art button at the end",
          rows.count() == 3 and page.locator("#importBody .imp-row .want-step").count() == 3 and page.locator("#importBody .imp-row .imp-art").count() == 3
          and page.locator("#importBody .imp-row .dl-count").count() == 0
          and page.evaluate("[...document.querySelectorAll('#importBody .imp-row')].every(r => r.firstElementChild.classList.contains('want-step') && r.lastElementChild.classList.contains('imp-art'))"))
    rag = "#importBody .imp-row [data-ip='main'][data-in='Ragavan, Nimble Pilferer']"
    page.click(rag + "[data-imp-act='more']"); page.wait_for_timeout(250)
    check("list view: ＋ adds a copy on the card's line and keeps the focus", "\n3 Ragavan, Nimble Pilferer (MH2) 138\n" in page.input_value("#importText")
          and page.locator(rag + "[data-imp-act='more']").evaluate("b => b === document.activeElement") and page.locator("#wantN").inner_text() == "5", page.input_value("#importText"))
    page.click("#importBody .imp-row [data-ip='main'][data-in='Lightning Bolt'][data-imp-act='less']"); page.wait_for_timeout(250)
    check("list view: − on the last copy takes the card out, with undo", "Lightning Bolt" not in page.input_value("#importText") and page.locator("#wantToast button").inner_text() == "元に戻す")
    page.click("#wantToast button"); page.wait_for_timeout(250)
    page.click(rag + "[data-imp-act='art']"); page.wait_for_selector("#artPicker .ap-item")
    check("list view: the art button opens the same picker", page.locator("#artPicker").is_visible() and page.locator("#artPicker .ap-item").count() == 3)
    page.keyboard.press("Escape")
    yen_right = page.evaluate("[...document.querySelectorAll('#importBody .imp-row .imp-art')].map(b => Math.round(b.getBoundingClientRect().right))")
    check("list view: the art buttons line up at the right of each column", len(set(yen_right)) <= 2, yen_right)
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(300)
    nb = page.evaluate("(() => { const r = document.getElementById('impName').getBoundingClientRect(); return [r.left, r.right, innerWidth, parseFloat(getComputedStyle(document.getElementById('impName')).fontSize)]; })()")
    check("phone: the name box and the list rows fit, no sideways scroll, a box big enough not to zoom",
          no_hscroll() and nb[1] <= nb[2] - 8 and nb[3] >= 16
          and page.evaluate("[...document.querySelectorAll('#importBody .imp-row')].every(r => r.scrollWidth <= r.clientWidth + 1)"), nb)
    page.set_viewport_size({"width": 1280, "height": 900}); page.wait_for_timeout(200)
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_selector("#importBody .imp-row")
    check("English: the name box says Want list until it has a name", nm.get_attribute("placeholder") == "Want list" and nm.get_attribute("aria-label") == "Name of the list")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_timeout(300)
    page.evaluate("['warujie-deck-import', 'warujie-want-list', 'akuchie-deck-view'].forEach(k => localStorage.removeItem(k))")

    # ---- 49. the price follows the printing a line names: the art picked, ☆ lines, Moxfield's foil marks ----
    page.set_viewport_size({"width": 1280, "height": 900})
    page.evaluate("['warujie-deck-import', 'warujie-want-list', 'akuchie-deck-view', 'akuchie-lang', 'akuchie-lite'].forEach(k => localStorage.removeItem(k))")
    page.evaluate("localStorage.setItem('warujie-want-list', '2 Ragavan, Nimble Pilferer\\n1 Lightning Bolt\\n')")
    page.evaluate("localStorage.setItem('akuchie-deck-view', 'list')")
    def yen_txt(y): return "¥{:,}".format(max(1, int(round(y))) if y < 1000 else int(round(y / 10) * 10))
    def total_txt(y, more=False): return ("約¥{:,}" + ("〜" if more else "")).format(int(round(round(y) / 100) * 100))
    def cheap_yen(name):
        r = cheap.get(name)
        opts = [x for x in ((r[0] / 100 * 150.0) if r and r[0] else None, (r[1] / 100 * 160.0) if r and r[1] else None) if x is not None]
        return min(opts) if opts else None
    def rowyen(name, part="main"):
        return page.evaluate("""([n, p]) => { const r = [...document.querySelectorAll('#importBody .imp-row')].find(r => { const b = r.querySelector('[data-imp-act=more]'); return b && b.dataset.in === n && b.dataset.ip === p; });
          const y = r && r.querySelector('.dl-yen'); return y ? [y.textContent, y.title] : null; }""", [name, part])
    def total(): return page.locator("#importBody .want-bar .dcst-v").first.inner_text()
    RAG_N = "Ragavan, Nimble Pilferer"
    CHEAP_T, PRINT_T = "1枚あたり・いちばん安い版の価格", "1枚あたり・この版の価格（米国と欧州の安いほう）"
    rag_cheap, bolt_cheap = cheap_yen(RAG_N), cheap_yen("Lightning Bolt")
    page.goto(SITE + "?view=want"); page.wait_for_selector("#importBody .imp-row .dl-yen:not(:empty)")
    page.wait_for_function("document.querySelector('#importBody .want-bar .dcst-v')")
    check("printing prices: a line that names no printing is priced at the card's cheapest, as before",
          rowyen(RAG_N) == [yen_txt(rag_cheap), CHEAP_T] and total() == total_txt(2 * rag_cheap + bolt_cheap), (rowyen(RAG_N), total()))
    page.click("#importBody .imp-row [data-ip='main'][data-in='Ragavan, Nimble Pilferer'][data-imp-act='art']"); page.wait_for_selector("#artPicker .ap-item")
    pp = page.evaluate("[...document.querySelectorAll('#artPicker .ap-item')].map(b => [b.querySelector('.print-meta').textContent.split('・')[0], (b.querySelector('.print-price') || {}).textContent, (b.querySelector('.print-price') || {}).title])")
    check("art picker: each printing shows the price it would count at in the list, in yen (the lower of US and EU)",
          ["MH2 #345", "¥8,250", PRINT_T] in pp and ["MH2 #138", "¥5,600", PRINT_T] in pp and ["MUL #21", "¥6,150", PRINT_T] in pp, pp)
    check("art picker: its note says the price follows", "価格もその版のものになります" in page.locator("#artPicker .ap-note").inner_text(), page.locator("#artPicker .ap-note").inner_text())
    n0 = len(calls)
    page.locator("#artPicker .ap-item", has_text="#345").click(); page.wait_for_timeout(500)
    check("printing prices: picking an art prices the card at that printing at once, the total too (the user's report, 2026-10-17)",
          rowyen(RAG_N) == ["¥8,250", PRINT_T] and total() == total_txt(2 * 8250 + bolt_cheap), (rowyen(RAG_N), total()))
    check("printing prices: the picked printing's price was already in, no new request", not any("/cards/collection" in c for c in calls[n0:]), calls[n0:])
    page.click("#importBody [data-iview=image]"); page.wait_for_selector("#importBody .imp-card .dc-yen")
    cy = page.evaluate("[...document.querySelectorAll('#importBody .imp-card')].map(c => { const y = c.querySelector('.dc-yen'); return [c.querySelector('.dc-name').textContent, y && y.textContent, y && y.title]; })")
    check("printing prices: the picture view shows the same price", ["敏捷なこそ泥、ラガバン", "¥8,250", PRINT_T] in cy, cy)
    page.click("#importBody [data-iview=list]"); page.wait_for_selector("#importBody .imp-row")
    page.click("#wantToast button"); page.wait_for_timeout(500)
    check("printing prices: undo puts the cheapest price back", rowyen(RAG_N) == [yen_txt(rag_cheap), CHEAP_T], rowyen(RAG_N))
    # a list pasted with printings: foil, a printing Scryfall doesn't have, a Japanese printing with a real scan
    page.fill("#importText", "Deck\n2 Ragavan, Nimble Pilferer (MH2) 138 *F*\n1 Lightning Bolt (XYZ) 999\n\nSideboard\n1 Ragavan, Nimble Pilferer (MUL) 21\n")
    page.wait_for_function("""(() => { const r = [...document.querySelectorAll('#importBody .imp-row')].find(r => { const b = r.querySelector('[data-imp-act=more]'); return b && b.dataset.ip === 'side'; });
      return r && r.querySelector('.dl-yen').textContent === '¥6,150'; })()""", timeout=8000)
    check("printing prices: a *F* line counts at the foil price", rowyen(RAG_N) == ["¥9,000", PRINT_T], rowyen(RAG_N))
    check("printing prices: a Japanese printing counts at its English printing's price (same set and number)", rowyen(RAG_N, "side") == ["¥6,150", PRINT_T], rowyen(RAG_N, "side"))
    check("printing prices: a printing Scryfall doesn't know keeps the cheapest price", rowyen("Lightning Bolt") == [yen_txt(bolt_cheap), CHEAP_T], rowyen("Lightning Bolt"))
    check("printing prices: the total adds them up, and says which lines count how",
          total() == total_txt(2 * 9000 + bolt_cheap + 6150) and page.locator("#importBody .want-bar .dcst-v").first.get_attribute("title") == "選んだ版はその版で、ほかはいちばん安い版で・サイドボード込み"
          and "版を指定した行" in page.locator("#importBody .deck-cost-note").inner_text() and "*F* の行はフォイルの価格" in page.locator("#importBody .deck-cost-note").inner_text(), total())
    unit = page.evaluate("""() => {
      const r = [];
      r.push(parseDeckText('1 Ragavan, Nimble Pilferer (MH2) 138 *F*\\n1 Ragavan, Nimble Pilferer (MH2) 138 *E*\\n1 Ragavan, Nimble Pilferer (MH2) 138\\n1 Bolt *F*').lines.map(l => l.f).join());
      r.push([pricesYen({ usd: '1.00', eur: '0.50' }, ''), pricesYen({ usd: null, usd_foil: '2.00' }, ''), pricesYen({ usd: '1.00', usd_etched: '3.00' }, 'e'),
              pricesYen({ usd: '1.00' }, 'f'), pricesYen({ usd: null, eur: null }, ''), pricesYen(null, '')].join());
      const e = entryYen({ name: 'Ragavan, Nimble Pilferer', lines: [{ s: 'mh2', cn: '345', count: 1, f: '' }, { s: '', cn: '', count: 1, f: '' }] }, rowByEnglishName('Ragavan, Nimble Pilferer'));
      r.push([Math.round(e.each), e.print].join());
      r.push(entryYen({ name: 'Mountain', lines: [{ s: 'mh2', cn: '138', count: 4 }] }, rowByEnglishName('Mountain')).each);
      r.push(deckCost([[2, 'Ragavan, Nimble Pilferer']]).yen);
      return r;
    }""")
    check("printing prices: *F* foil and *E* etched are read; US or EU, whichever is lower; a foil-only printing at its foil price; two lines of one card at their own prices; basic lands free",
          unit[:4] == ["f,e,,f", "80,300,450,150,,", "{},true".format(round((8250 + rag_cheap) / 2)), None], unit)
    check("printing prices: the deck pages keep the cheapest printing (no prices of their own)", unit[4] == round(2 * rag_cheap), unit)
    # the tray: the same prices, 最安 only where it is the cheapest
    page.click("#wantBtn"); page.wait_for_selector("#wantTray .wt-row .wt-yen")
    ty = page.evaluate("[...document.querySelectorAll('#wantTray .wt-row')].map(r => [r.querySelector('.wt-title').textContent, (r.querySelector('.wt-yen') || {}).textContent])")
    check("tray: a card is priced as its lines' printings (here 2 foil and 1 other), 最安 only where it is the cheapest",
          ty == [["敏捷なこそ泥、ラガバン", yen_txt((2 * 9000 + 6150) / 3)], ["稲妻", "最安 " + yen_txt(bolt_cheap)]], ty)
    page.keyboard.press("Escape")
    # the lightweight mode prices the printings too (no pictures, still the price)
    page.evaluate("localStorage.setItem('akuchie-lite', '1')")
    page.goto(SITE + "?view=want"); page.wait_for_selector("#importBody .imp-row .dl-yen:not(:empty)")
    page.wait_for_function("""(() => { const r = [...document.querySelectorAll('#importBody .imp-row')].find(r => r.querySelector('[data-imp-act=more]').dataset.ip === 'side'); return r && r.querySelector('.dl-yen').textContent === '¥6,150'; })()""", timeout=8000)
    check("lightweight mode: the printings' prices still count", rowyen(RAG_N) == ["¥9,000", PRINT_T] and page.evaluate("document.documentElement.dataset.lite") == "1", rowyen(RAG_N))
    page.evaluate("localStorage.removeItem('akuchie-lite')")
    page.evaluate("['warujie-deck-import', 'warujie-want-list', 'akuchie-deck-view'].forEach(k => localStorage.removeItem(k))")

    # the order stays put when a count changes (the owner's report, 2026-10-17: Flare of Malice passed Baleful Mastery at 5)
    page.evaluate("localStorage.setItem('warujie-want-list', '4 Llanowar Elves\\n4 Ragavan, Nimble Pilferer\\n')")
    page.goto(SITE + "?view=want"); page.wait_for_selector("#importBody .imp-row")
    order = lambda: page.evaluate("[...document.querySelectorAll('#importBody .imp-row [data-imp-act=more]')].map(b => b.dataset.in)")
    before = order()
    page.click("#importBody .imp-row [data-in='Ragavan, Nimble Pilferer'][data-imp-act='more']"); page.wait_for_timeout(300)
    after_list = order()
    page.click("#importBody [data-iview=image]"); page.wait_for_selector("#importBody .imp-card")
    page.click("#importBody .imp-card [data-in='Ragavan, Nimble Pilferer'][data-imp-act='more']"); page.wait_for_timeout(300)
    after_pics = page.evaluate("[...document.querySelectorAll('#importBody .imp-card [data-imp-act=more]')].map(b => b.dataset.in)")
    check("order: one more copy never moves a card past another of the same mana value, in either view",
          before == after_list == after_pics == ["Llanowar Elves", "Ragavan, Nimble Pilferer"] and "6 Ragavan" in listtext(), (before, after_list, after_pics))
    check("order: deck pages still put most copies first", page.evaluate("deckSort([{ cmc: 1, count: 1, label: 'a' }, { cmc: 1, count: 4, label: 'b' }], false).map(x => x.label).join()") == "b,a")
    page.click("#importBody [data-iview=list]"); page.wait_for_selector("#importBody .imp-row")
    page.evaluate("['warujie-deck-import', 'warujie-want-list', 'akuchie-deck-view'].forEach(k => localStorage.removeItem(k))")

    # ---- 50. a green ＋ beside each card name in the suggestions: one copy into the want list, or into the list on the price page ----
    page.goto(SITE + "?card=drag-ja"); page.wait_for_selector(".cp-name")
    page.wait_for_function("typeof LOCAL_DB !== 'undefined' && LOCAL_DB")
    page.focus("#searchInput"); page.locator("#searchInput").press_sequentially("ラノ")
    page.wait_for_selector("#searchSuggest .sug-add")
    sugrow = page.locator("#searchSuggest .sug-row", has_text="ラノワールのエルフ")
    add = sugrow.locator(".sug-add")
    look = add.evaluate("b => { const c = getComputedStyle(b), r = b.getBoundingClientRect(), it = b.closest('li').querySelector('.suggest-item').getBoundingClientRect(); return [c.backgroundColor, Math.round(r.width), Math.round(r.height), b.getAttribute('aria-label'), b.dataset.n, Math.round(r.left - it.right), Math.round(b.closest('li').getBoundingClientRect().right - r.right)]; }")
    check("suggestions: each card name has a green ＋ at its end, saying what it does",
          look[0] == "rgb(181, 230, 85)" and look[1] == 30 and look[2] == 30 and look[3] == "ウォントリストに1枚追加：ラノワールのエルフ" and look[4] == "0" and 0 <= look[5] <= 8 and look[6] <= 12, look)
    url0 = page.url
    add.click(); page.wait_for_timeout(250)
    check("suggestions: ＋ puts one copy in the want list without opening the card; the menu stays open, the box keeps the focus, and a note says so",
          listtext() == "1 Llanowar Elves\n" and page.url == url0 and page.locator("#searchSuggest").is_visible()
          and page.evaluate("document.activeElement.id") == "searchInput" and page.locator("#wantN").inner_text() == "1"
          and page.locator("#wantToast span").inner_text() == "ラノワールのエルフをウォントリストに追加しました（1枚）" and page.locator("#wantToast button").inner_text() == "リストを見る"
          and add.get_attribute("data-n") == "1" and add.get_attribute("aria-label") == "ウォントリストに1枚追加：ラノワールのエルフ（いま1枚）", (listtext(), page.url))
    add.click(); page.wait_for_timeout(250)
    badge = add.evaluate("b => getComputedStyle(b, '::after').content")
    check("suggestions: ＋ again adds another copy on the same line, and the ＋ shows how many", listtext() == "2 Llanowar Elves\n" and add.get_attribute("data-n") == "2" and badge == '"2"', (listtext(), badge))
    check("suggestions: the card's ☆ elsewhere shows it as added", page.evaluate("wantFindFor({ k: 'elf-oracle', n: 'Llanowar Elves' }).count") == 2)
    sugrow.locator(".suggest-item").click()
    page.wait_for_function("document.querySelector('.cp-name') && document.querySelector('.cp-name').textContent === 'ラノワールのエルフ'")
    check("suggestions: the name itself still opens the card", "card=elf-ja" in page.url)
    # on the price page: into the list on screen
    page.evaluate("localStorage.setItem('warujie-deck-import', 'Deck\\n4 Lightning Bolt\\n\\nSideboard\\n2 Qasali Pridemage\\n')")
    page.goto(SITE + "?view=import"); page.wait_for_selector("#importBody .deck-section")
    page.focus("#searchInput"); page.locator("#searchInput").press_sequentially("シヴ")
    page.wait_for_selector("#searchSuggest .sug-add")
    add = page.locator("#searchSuggest .sug-row", has_text="シヴ山のドラゴン").locator(".sug-add")
    check("suggestions on the price page: ＋ adds to the deck shown", add.get_attribute("aria-label") == "デッキに1枚追加：シヴ山のドラゴン", add.get_attribute("aria-label"))
    add.click(); page.wait_for_function("document.getElementById('importText').value.includes('1 Shivan Dragon')")
    page.wait_for_function("[...document.querySelectorAll('#importBody .dl-name, #importBody .dc-name')].some(e => e.textContent.includes('シヴ山のドラゴン'))")
    check("suggestions on the price page: the card goes into the main deck (not the sideboard) and the page prices it; the want list is left alone; undo offered",
          page.input_value("#importText") == "Deck\n4 Lightning Bolt\n1 Shivan Dragon\n\nSideboard\n2 Qasali Pridemage\n" and listtext() == "2 Llanowar Elves\n"
          and page.locator("#wantToast span").inner_text() == "シヴ山のドラゴンをデッキに追加しました（1枚）" and page.locator("#wantToast button").inner_text() == "元に戻す", page.input_value("#importText"))
    page.locator("#searchInput").press_sequentially("x"); page.locator("#searchInput").press("Backspace"); page.wait_for_selector("#searchSuggest .sug-add")
    add = page.locator("#searchSuggest .sug-row", has_text="シヴ山のドラゴン").locator(".sug-add")
    add.click(); page.wait_for_function("document.getElementById('importText').value.includes('2 Shivan Dragon')")
    check("suggestions on the price page: ＋ again counts up the deck's line", "\n2 Shivan Dragon\n" in page.input_value("#importText") and add.get_attribute("data-n") == "2", page.input_value("#importText"))
    page.click("#wantToast button"); page.wait_for_timeout(300)
    check("suggestions on the price page: undo takes it back", "1 Shivan Dragon" in page.input_value("#importText"), page.input_value("#importText"))
    page.press("#searchInput", "Escape")
    page.goto(SITE + "?view=want"); page.wait_for_selector("#importBody .imp-row")
    page.focus("#searchInput"); page.locator("#searchInput").press_sequentially("ラノ"); page.wait_for_selector("#searchSuggest .sug-add")
    add = page.locator("#searchSuggest .sug-row", has_text="ラノワールのエルフ").locator(".sug-add")
    check("suggestions on the want list page: ＋ adds to the want list, with its count", add.get_attribute("aria-label") == "ウォントリストに1枚追加：ラノワールのエルフ（いま2枚）", add.get_attribute("aria-label"))
    add.click(); page.wait_for_function("document.getElementById('importText').value === '3 Llanowar Elves\\n'")
    check("suggestions on the want list page: the list on screen follows, with undo", page.locator("#wantToast button").inner_text() == "元に戻す" and listtext() == "3 Llanowar Elves\n")
    page.press("#searchInput", "Escape")
    # phone: the home page's box
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(SITE); page.wait_for_selector("#heroInput")
    page.wait_for_function("typeof LOCAL_DB !== 'undefined' && LOCAL_DB")
    page.focus("#heroInput"); page.locator("#heroInput").press_sequentially("ラノ"); page.wait_for_selector("#heroSuggest .sug-add")
    ph = page.evaluate("(() => { const b = document.querySelector('#heroSuggest .sug-add'), r = b.getBoundingClientRect(), li = b.closest('li'), ul = li.closest('ul'); return [Math.round(r.width), Math.round(r.right), Math.round(li.getBoundingClientRect().right), li.scrollWidth <= li.clientWidth + 1, ul.scrollWidth <= ul.clientWidth + 1, b.dataset.n]; })()")
    check("phone: the ＋ is big enough to tap and sits inside the menu with its count, no sideways scroll", ph[0] == 34 and ph[1] <= ph[2] and ph[3] and ph[4] and ph[5] == "3" and no_hscroll(), ph)
    page.locator("#heroSuggest .sug-add").first.click(); page.wait_for_selector("#wantToast:not([hidden])")
    tw = page.evaluate("(() => { const r = document.getElementById('wantToast').getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height), Math.round(r.left), Math.round(r.right)]; })()")
    check("phone: the note for a longer message uses the screen's width (not a tall narrow box) and stays on screen", tw[0] >= 300 and tw[1] <= 80 and tw[2] >= 0 and tw[3] <= 390, tw)
    if SHOTS: page.screenshot(path="suggest_add_phone.png")
    page.set_viewport_size({"width": 1280, "height": 900}); page.wait_for_timeout(200)
    page.press("#heroInput", "Escape")
    page.goto(SITE + "?card=drag-ja"); page.wait_for_selector(".cp-name")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_timeout(300)
    page.fill("#searchInput", ""); page.focus("#searchInput"); page.locator("#searchInput").press_sequentially("Llano"); page.wait_for_selector("#searchSuggest .sug-add")
    check("desktop: the ＋ and its count fit in the menu, no sideways scroll there",
          page.evaluate("(() => { const ul = document.getElementById('searchSuggest'); return ul.scrollWidth <= ul.clientWidth + 1; })()"))
    check("English: the ＋ says it in English", page.locator("#searchSuggest .sug-add").first.get_attribute("aria-label") == "Add one to your want list: Llanowar Elves (now 4)",
          page.locator("#searchSuggest .sug-add").first.get_attribute("aria-label"))
    page.press("#searchInput", "Escape")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_timeout(300)
    page.evaluate("['warujie-deck-import', 'warujie-want-list', 'akuchie-deck-view'].forEach(k => localStorage.removeItem(k))")

    # ---- 51. page cleanup (2026-10-17): JP | EN and ¥ | $ in the top bar, every price in the chosen currency ----
    PRICE_SITE["dir"] = PRICES_FULL
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(SITE); page.wait_for_selector("#homeHero", state="visible")
    page.evaluate("['warujie-currency', 'akuchie-market', 'akuchie-lang'].forEach(k => localStorage.removeItem(k))")
    page.goto(SITE + "?card=rag-en-mh2")
    page.wait_for_function("document.querySelector('#cardViewCard .shop-prices') && document.querySelector('#cardViewCard .shop-prices').textContent.includes('Cardsphere')")
    pressed = lambda sel: page.locator(sel + " [aria-pressed=true]").inner_text()
    check("top bar: JP | EN and ¥ | $ switches, JP and ¥ chosen at first", pressed("#langBtn") == "JP" and pressed("#curBtn") == "¥"
          and page.locator("#langBtn button").all_inner_texts() == ["JP", "EN"] and page.locator("#curBtn button").all_inner_texts() == ["¥", "$"]
          and page.get_attribute("html", "data-cur") == "jpy", (pressed("#langBtn"), pressed("#curBtn")))
    check("top bar: the tagline stays (owner's choice), no 'English' button", page.locator("#brandSub").count() == 1 and page.locator(".lang-btn").count() == 0)
    psec = page.locator("#cardViewCard .price-section")
    check("¥: the card page's prices in yen, the dollar price on hover, the rates under them", "¥5,625" in psec.inner_text() and "$37.50" not in psec.inner_text()
          and page.locator("#cardViewCard .sp-val .cur").first.get_attribute("title") == "$37.50" and "1ドル＝150.00円" in psec.inner_text(), psec.inner_text())
    page.click("#curBtn [data-v=usd]")
    page.wait_for_function("document.documentElement.dataset.cur === 'usd'")
    ptxt = psec.inner_text()
    check("$: prices in dollars at once, no yen, no rate note on the US tab", "$37.50" in ptxt and "$44.99" in ptxt and "¥" not in ptxt and "1ドル" not in ptxt
          and page.locator("#cardViewCard .sp-val .cur[title]").count() == 0 and pressed("#curBtn") == "$", ptxt)
    page.wait_for_selector("#priceHistory svg .hist-line")
    check("$: the price chart in dollars", page.locator("#priceHistory .hist-end").text_content() == "$41.00", page.locator("#priceHistory .hist-end").text_content())
    check("$: the printings' prices in dollars", "$55.00" in page.locator("#versionMenuPanel").inner_text() and "¥" not in page.locator("#versionMenuPanel").inner_text())
    check("$: the listings in dollars", "$35.50" in page.locator("#offersBox").inner_text() and "¥" not in page.locator("#offersBox").inner_text())
    if SHOTS:
        page.wait_for_timeout(300); page.screenshot(path="usd_card.png", full_page=True)
        page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(300); page.screenshot(path="usd_card_phone.png", full_page=True)
        page.set_viewport_size({"width": 1280, "height": 900}); page.wait_for_timeout(300)
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="eu"]')
    page.wait_for_function("document.querySelector('#cardViewCard .price-section').dataset.market === 'eu'")
    eu = page.locator("#cardViewCard .shop-prices .cur").first
    check("$: European prices converted to dollars, the euro price on hover, with the rates", eu.inner_text() == "$34.03" and eu.get_attribute("title") == "€31.90"
          and "1ユーロ＝160.00円" in psec.inner_text(), (eu.inner_text(), eu.get_attribute("title")))
    page.click('#cardViewCard .price-tabs .seg-btn[data-pmarket="us"]')
    page.reload(); page.wait_for_function("document.querySelector('#cardViewCard .shop-prices') && document.querySelector('#cardViewCard .shop-prices').textContent.includes('Cardsphere')")
    check("$: remembered after reloading", page.evaluate("localStorage.getItem('warujie-currency')") == "usd" and "$37.50" in psec.inner_text() and pressed("#curBtn") == "$")
    top_search("ラガバン"); page.wait_for_selector("#cardGrid .tile-price")
    check("$: search results in dollars", page.locator("#cardGrid .tile-price").first.inner_text() == "$40.00", page.locator("#cardGrid .tile-price").first.inner_text())
    page.goto(SITE + "?view=prices&market=us&win=7"); page.wait_for_selector("#moverBody .mover-row")
    mv = page.locator("#moverBody").inner_text()
    check("$: price movers in dollars", "$6.44 → $7.28" in mv and "¥" not in mv, mv[:200])
    if SHOTS: page.screenshot(path="usd_movers.png")
    page.click("#curBtn [data-v=jpy]"); page.wait_for_function("document.documentElement.dataset.cur === 'jpy'")
    mv = page.locator("#moverBody").inner_text()
    check("¥ again: the movers follow without reloading", "¥966 → ¥1,092" in mv and "$" not in mv, mv[:200])
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'en'")
    check("English: the switches keep their labels, EN chosen, labels for screen readers", pressed("#langBtn") == "EN" and page.get_attribute("#curBtn", "aria-label") == "Currency"
          and page.get_attribute("#langBtn", "aria-label") == "Language" and page.get_attribute("#curBtn [data-v=usd]", "title") == "Show prices in US dollars")
    page.click("#langBtn [aria-pressed=true]"); page.wait_for_timeout(200)
    check("pressing the chosen half changes nothing", page.evaluate("document.documentElement.lang") == "en")
    page.click("#langBtn [aria-pressed=false]"); page.wait_for_function("document.documentElement.lang === 'ja'")
    page.set_viewport_size({"width": 390, "height": 800}); page.goto(SITE); page.wait_for_selector("#homeHero", state="visible")
    lb, cb, mb = page.locator("#langBtn").bounding_box(), page.locator("#curBtn").bounding_box(), page.locator("#menuBtn").bounding_box()
    check("phone: both switches in the top bar beside the menu, on one line, no sideways scroll", no_hscroll() and abs(lb["y"] - cb["y"]) < 4
          and lb["x"] + lb["width"] <= cb["x"] and cb["x"] + cb["width"] <= mb["x"] + 1 and mb["x"] + mb["width"] <= 390, (lb, cb, mb))
    if SHOTS: page.screenshot(path="topbar_phone.png")
    check("home: no input label, second lead line or hint (the placeholder and the examples say it)", page.locator(".hero-label").bounding_box()["width"] <= 1
          and page.locator(".lead-extra, .hero-hint").count() == 0)
    page.set_viewport_size({"width": 1280, "height": 900})
    page.evaluate("localStorage.removeItem('warujie-currency')")

    # ---- 52. page cleanup round 2 (2026-10-17): tagline back, square JP | EN and ¥ | $ switches, St Pi Mo Lg Vt Pa Cm, Pioneer wildcards ----
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(SITE + "?card=rag-en-mh2"); page.wait_for_selector(".cp-name")
    page.evaluate("['warujie-currency', 'akuchie-lang'].forEach(k => localStorage.removeItem(k))")
    page.goto(SITE + "?card=rag-en-mh2"); page.wait_for_selector("#priceHistory svg .hist-line")
    bar = page.evaluate("""(() => { const r = s => document.querySelector(s).getBoundingClientRect(), bar = document.querySelector('.topbar-inner');
        return [bar.scrollWidth <= bar.clientWidth + 1, Math.round(r('#brandSub').width), Math.round(r('#langBtn').right), Math.round(r('#themeSwitch').right), Math.round(r('#brandSub').right) <= Math.round(r('#searchForm').left), Math.round(r('#searchInput').width), Math.round(r('#brandSub').height)]; })()""")
    check("top bar (1280px): the tagline is back beside the logo and everything fits", page.locator("#brandSub").is_visible() and "効果テキスト" in page.locator("#brandSub").inner_text()
          and bar[0] and bar[1] > 0 and bar[3] <= 1280 - 12 and bar[4] and bar[5] >= 200 and bar[6] <= 32, bar)   # the search box keeps a usable width; the tagline in two lines
    look = page.evaluate("""(() => { const t = document.querySelector('#langBtn .sq-track'), d = document.querySelector('#darkSwitch .sq-track'), c = getComputedStyle(t), e = getComputedStyle(d);
        return [!!document.querySelector('#curBtn .sq-track'), c.borderRadius, e.borderRadius, c.width, e.width, c.height, e.height]; })()""")
    check("top bar: JP | EN and ¥ | $ are the same square switch as ダーク / 軽量", look[0] and look[1] == look[2] and look[3] == look[4] and look[5] == look[6], look)
    knob = lambda sel: page.evaluate(f"Math.round(document.querySelector('{sel} .sq-knob').getBoundingClientRect().left - document.querySelector('{sel} .sq-track').getBoundingClientRect().left)")
    k0 = knob("#langBtn")
    page.click("#langBtn .sq-track"); page.wait_for_function("document.documentElement.lang === 'en'"); page.wait_for_timeout(250)
    check("JP | EN: a click on the switch itself turns to English and moves the knob right", page.locator("#langBtn [aria-pressed=true]").inner_text() == "EN"
          and page.get_attribute("#langBtn", "data-on") == "1" and knob("#langBtn") > k0 + 10 and page.locator("#brandSub").inner_text() == "MTG card search by rules text", [k0, knob("#langBtn")])
    page.click("#langBtn .sq-track"); page.wait_for_function("document.documentElement.lang === 'ja'")
    check("JP | EN: and back to Japanese", page.locator("#langBtn [aria-pressed=true]").inner_text() == "JP" and page.get_attribute("#langBtn", "data-on") == "")
    page.click("#curBtn .sq-track"); page.wait_for_function("document.documentElement.dataset.cur === 'usd'")
    check("¥ | $: a click on the switch itself turns to dollars", page.locator("#curBtn [aria-pressed=true]").inner_text() == "$" and page.get_attribute("#curBtn", "data-on") == "1"
          and page.locator("#priceHistory .hist-end").text_content() == "$41.00", page.locator("#priceHistory .hist-end").text_content())
    page.click("#curBtn [data-v=jpy]"); page.wait_for_function("document.documentElement.dataset.cur === 'jpy'")
    check("¥ | $: the ¥ label picks yen again", page.get_attribute("#curBtn", "data-on") == "" and page.locator("#priceHistory .hist-end").text_content() == "¥6,150")
    page.click("#langBtn [aria-pressed=true]"); page.wait_for_timeout(150)
    check("JP | EN: clicking the chosen side changes nothing", page.evaluate("document.documentElement.lang") == "ja")
    fsw = page.locator("#histFoil")
    check("price chart: foil is a square switch labelled フォイル like the listings' (no 通常 / Foil buttons)", fsw.count() == 1 and fsw.get_attribute("role") == "switch"
          and fsw.inner_text() == "フォイル" and fsw.get_attribute("aria-checked") == "false" and page.locator("#priceHistory .seg-btn[data-foil]").count() == 0)
    fsw.click(); page.wait_for_function("document.getElementById('histFoil') && document.getElementById('histFoil').getAttribute('aria-checked') === 'true'")
    check("price chart: the switch shows foil prices", page.locator("#priceHistory .hist-end").text_content() == "¥9,150", page.locator("#priceHistory .hist-end").text_content())
    page.click("#histFoil"); page.wait_for_function("document.getElementById('histFoil').getAttribute('aria-checked') === 'false'")
    if SHOTS: page.locator(".topbar").screenshot(path="r53_topbar.png")
    codes = page.evaluate("(() => { const d = document.createElement('div'); d.innerHTML = legalityCirclesHtml({ standard: 'legal', commander: 'legal' }); return [...d.querySelectorAll('.legal-circle')].map(c => c.textContent); })()")
    check("search tiles: format circles as St Pi Mo Lg Vt Pa Cm (the owner's list)", codes == ["St", "Pi", "Mo", "Lg", "Vt", "Pa", "Cm"], codes)
    check("Arena wildcards: Standard and Pioneer only", page.evaluate("[wildcardsHtml({ wc: { m: 1, r: 0, u: 0, c: 0 } }, 'pioneer') !== '', wildcardsHtml({ wc: { m: 1, r: 0, u: 0, c: 0 } }, 'legacy') === '']") == [True, True])
    # the set page's 日本語版 / 英語版 is the same square switch
    page.goto(SITE + "?set=m10&lang=en"); page.wait_for_selector("#setHeader .set-lang-toggle .sq-track")
    check("set page: 日本語版 / 英語版 as the square switch, 英語版 chosen", page.get_attribute("#setHeader .set-lang-toggle", "data-on") == "1"
          and page.get_attribute("#setHeader .set-lang-btn[data-lang=en]", "aria-pressed") == "true")
    page.click("#setHeader .set-lang-toggle .sq-track"); page.wait_for_function("document.querySelector('#setHeader .set-lang-btn[data-lang=ja]') && document.querySelector('#setHeader .set-lang-btn[data-lang=ja]').getAttribute('aria-pressed') === 'true'")
    check("set page: a click on the switch turns to the Japanese printings", "lang=ja" in page.url and page.get_attribute("#setHeader .set-lang-toggle", "data-on") == "", page.url)
    if SHOTS: page.locator("#setHeader").screenshot(path="r53_set.png")
    # phone: the metagame's two-letter codes share the row, each centred
    page.set_viewport_size({"width": 390, "height": 844})
    META_MODE["mode"] = "real"
    page.goto(SITE + "?view=meta&format=pioneer"); page.wait_for_selector("#metaBody .meta-row")
    fb = page.evaluate("""[...document.querySelectorAll('#metaFormats .seg-btn')].map(b => { const r = b.getBoundingClientRect(), s = b.querySelector('.sh-short').getBoundingClientRect();
        return [Math.round(r.width), Math.round((s.left + s.width / 2) - (r.left + r.width / 2)), b.innerText]; })""")
    row = page.evaluate("(() => { const s = document.getElementById('metaFormats').getBoundingClientRect(), b = [...document.querySelectorAll('#metaFormats .seg-btn')]; return [Math.round(b[0].getBoundingClientRect().left - s.left), Math.round(s.right - b[b.length - 1].getBoundingClientRect().right)]; })()")
    check("phone, metagame: St Pi Mo Lg Vt Pa fill the row in equal buttons, each code centred", [x[2] for x in fb] == ["St", "Pi", "Mo", "Lg", "Vt", "Pa"]
          and max(x[0] for x in fb) - min(x[0] for x in fb) <= 1 and all(abs(x[1]) <= 1 for x in fb) and abs(row[0]) <= 2 and abs(row[1]) <= 2 and no_hscroll(), (fb, row))
    check("phone: the top bar's switches fit, the tagline stays hidden there as before", page.locator("#curBtn").is_visible() and not page.locator("#brandSub").is_visible() and no_hscroll())
    if SHOTS: page.screenshot(path="r53_meta_phone.png")
    META_MODE["mode"] = "fixture"
    page.set_viewport_size({"width": 1280, "height": 900})

    str_src = INDEX[INDEX.index("const STR = {"):INDEX.index("\n};", INDEX.index("const STR = {"))]
    str_keys = re.findall(r"^\s+'([^']+)':\s*\[", str_src, re.M)
    check("interface strings: no key in STR twice (a later one would win silently)", len(str_keys) > 500 and len(set(str_keys)) == len(str_keys),
          [k for k in set(str_keys) if str_keys.count(k) > 1])

    check("no JavaScript errors", not errors, errors)
    browser.close()

failed = [l for l, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
if failed: print("FAILED:", *failed, sep="\n  ")

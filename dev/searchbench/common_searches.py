"""The 100 searches Japanese players type most, and what each must find (round 22).

There are no search logs (the site keeps none), so the list was built from what players
type: card names in kanji, katakana and hiragana, names typed slightly wrong, nicknames,
rules text typed loosely, slang and role words, land nicknames, and colours, guilds,
formats and rarities beside other words. search_checks.py runs each one against the
real card database; every entry is one check.

Each entry: q (the search) and any of
  first      English name of the card that must come first
  top        English names that must all be in the first `k` results (k defaults to 5)
  has        English names that must be found
  hasnt      English names that must not be found
  nottop     English names that must not be in the first `k` results
  role       the role id the search must be read as
  alias      a "from>to" note that must be shown
  min, max   bounds on the number of results
  only       a test (or a list of tests) every result must pass: 'colors:RW' (within these
             colors), 'type:<word>' (English type line), 'cmc:<n>', 'rarity:<r>',
             'legal:<code>', 'name:<text>' (Japanese name contains), 'cost:X' (X in the cost)
  same       another search that must find exactly as many cards
  atleast    another search that must find no more cards
"""

COMMON_SEARCHES = [
    # card names as printed
    {"q": "稲妻", "first": "Lightning Bolt"},
    {"q": "意志の力", "first": "Force of Will"},
    {"q": "渦まく知識", "first": "Brainstorm"},
    {"q": "思考囲い", "first": "Thoughtseize"},
    {"q": "剣を鍬に", "first": "Swords to Plowshares"},
    {"q": "太陽の指輪", "first": "Sol Ring"},
    {"q": "暗黒の儀式", "first": "Dark Ritual"},
    {"q": "対抗呪文", "first": "Counterspell"},
    {"q": "一つの指輪", "first": "The One Ring"},
    {"q": "オークの弓使い", "first": "Orcish Bowmasters"},
    {"q": "濁浪の執政", "first": "Murktide Regent"},
    {"q": "孤独", "first": "Solitude"},
    {"q": "タルモゴイフ", "first": "Tarmogoyf"},
    {"q": "魂の洞窟", "first": "Cavern of Souls"},
    # part of a name, a name without its punctuation
    {"q": "ラガバン", "first": "Ragavan, Nimble Pilferer"},
    {"q": "ジェイス", "has": ["Jace, the Mind Sculptor"], "min": 30},
    {"q": "テフェリー", "has": ["Teferi, Time Raveler"], "min": 20},
    {"q": "エムラクール", "has": ["Emrakul, the Aeons Torn"]},
    {"q": "ニコルボーラス", "has": ["Nicol Bolas, the Ravager // Nicol Bolas, the Arisen"], "only": "name:ボーラス"},
    {"q": "精神を刻む者ジェイス", "first": "Jace, the Mind Sculptor"},
    {"q": "ウルザ", "has": ["Urza's Saga"]},
    # names typed in hiragana (on phones, before converting): read by the name's reading
    {"q": "いなずま", "first": "Lightning Bolt"},
    {"q": "いしのちから", "first": "Force of Will"},
    {"q": "しこうかこい", "first": "Thoughtseize"},
    {"q": "らがばん", "first": "Ragavan, Nimble Pilferer"},
    {"q": "えむらくーる", "has": ["Emrakul, the Aeons Torn"]},
    {"q": "はかい", "alias": "はかい>破壊", "nottop": ["Tombstone Stairwell"], "min": 2000},
    # names typed slightly wrong: the closest name is searched, with a note
    {"q": "渦巻く知識", "first": "Brainstorm", "alias": "渦巻く知識>渦まく知識"},
    {"q": "意思の力", "first": "Force of Will", "alias": "意思の力>意志の力"},
    {"q": "ジェース", "has": ["Jace, the Mind Sculptor"], "alias": "ジェース>ジェイス"},
    {"q": "エムラクル", "has": ["Emrakul, the Aeons Torn"]},
    {"q": "ラガヴァン", "first": "Ragavan, Nimble Pilferer"},
    {"q": "じぇーす", "has": ["Jace, the Mind Sculptor"]},
    # players' names for cards, and cards never printed in Japanese
    {"q": "ボルト", "first": "Lightning Bolt", "alias": "ボルト>稲妻"},
    {"q": "フォース", "first": "Force of Will"},
    {"q": "FoW", "first": "Force of Will", "max": 1},
    {"q": "JTMS", "first": "Jace, the Mind Sculptor", "max": 1},
    {"q": "ブレスト", "first": "Brainstorm"},
    {"q": "ボブ", "first": "Dark Confidant"},
    {"q": "トロン", "top": ["Urza's Tower", "Urza's Mine", "Urza's Power Plant"], "k": 3},
    {"q": "ブラックロータス", "first": "Black Lotus"},
    {"q": "アンダーグラウンドシー", "first": "Underground Sea"},
    {"q": "ライトニングボルト", "first": "Lightning Bolt"},
    # rules text, typed the way players type it
    {"q": "カードを1枚引く", "has": ["Opt", "Preordain"], "min": 1500},
    {"q": "カード2枚引く", "has": ["Divination"], "min": 250},
    {"q": "クリーチャーを破壊する", "has": ["Murder", "Doom Blade"]},
    {"q": "追放する", "has": ["Swords to Plowshares", "Path to Exile"], "min": 1000},
    {"q": "打ち消す", "has": ["Counterspell", "Mana Leak"]},
    {"q": "トークンを生成", "has": ["Raise the Alarm"], "min": 2000},
    {"q": "トークンを作る", "has": ["Raise the Alarm"], "alias": "トークンを作る>トークンを生成", "atleast": "トークンを生成"},
    {"q": "+1/+1カウンター", "has": ["Hardened Scales"]},
    {"q": "ライフを得る", "has": ["Healing Salve"], "min": 1000},
    {"q": "墓地から戦場", "has": ["Reanimate", "Animate Dead"]},
    {"q": "土地を探す", "has": ["Rampant Growth"]},
    {"q": "手札に戻す", "has": ["Unsummon"]},
    {"q": "ハンドに戻す", "has": ["Unsummon"], "alias": "ハンドに戻す>手札に戻す", "same": "手札に戻す"},
    {"q": "ライブラリーから探して手札に加える", "has": ["Demonic Tutor"]},
    {"q": "破壊不能", "has": ["Darksteel Myr"]},
    {"q": "飛行をもつ", "same": "飛行を持つ", "min": 500},
    {"q": "呪文を唱えるたび", "has": ["Young Pyromancer"]},
    {"q": "キャストしたとき", "has": ["Young Pyromancer"], "alias": "キャストしたとき>唱えたとき・唱えるたび"},
    {"q": "兵士トークン", "has": ["Raise the Alarm"], "alias": "兵士トークン>兵士クリーチャートークン"},
    {"q": "戦場に出たとき", "has": ["Mulldrifter"], "min": 3000},
    {"q": "占術", "has": ["Preordain"]},
    {"q": "宝物", "has": ["Smothering Tithe"]},
    {"q": "接死", "has": ["Baleful Strix"]},
    # role words and slang
    {"q": "除去", "role": "removal", "has": ["Swords to Plowshares", "Murder"]},
    {"q": "ドロー", "role": "draw", "has": ["Rhystic Study"]},
    {"q": "マナ加速", "role": "ramp", "has": ["Rampant Growth"], "same": "ランプ"},
    {"q": "サーチ", "role": "tutor", "has": ["Demonic Tutor"]},
    {"q": "リアニ", "role": "reanimate", "has": ["Reanimate"]},
    {"q": "ハンデス", "role": "hand-disruption", "has": ["Thoughtseize"]},
    {"q": "ランデス", "role": "land-removal", "has": ["Stone Rain"]},
    {"q": "全体除去", "role": "boardwipe", "has": ["Wrath of God"]},
    {"q": "火力", "role": "burn", "has": ["Lightning Bolt"]},
    {"q": "マナクリ", "role": "mana-dork", "has": ["Llanowar Elves"]},
    {"q": "墓地対策", "role": "graveyard-hate", "has": ["Rest in Peace"]},
    {"q": "ライフ 回復", "role": "lifegain", "same": "ライフ回復"},
    # land nicknames
    {"q": "フェッチランド", "role": "fetchland", "has": ["Flooded Strand"]},
    {"q": "ショックランド", "role": "shockland", "has": ["Hallowed Fountain"]},
    {"q": "ペインランド", "role": "painland", "has": ["Adarkar Wastes"], "hasnt": ["Glacial Fortress"], "only": "type:land"},
    {"q": "チェックランド", "role": "checkland", "has": ["Glacial Fortress"], "hasnt": ["Adarkar Wastes"], "only": "type:land"},
    {"q": "ファストランド", "role": "fastland", "has": ["Seachrome Coast"], "hasnt": ["Deserted Beach"]},
    {"q": "スローランド", "role": "slowland", "has": ["Deserted Beach"], "hasnt": ["Seachrome Coast"]},
    {"q": "ミシュラランド", "role": "manland", "has": ["Mutavault", "Celestial Colonnade"], "hasnt": ["Adarkar Wastes"], "only": "type:land"},
    {"q": "トライランド", "role": "triland", "has": ["Arcane Sanctum", "Zagoth Triome"], "hasnt": ["Tundra", "Hallowed Fountain"]},
    {"q": "パスウェイ", "role": "pathway", "has": ["Brightclimb Pathway // Grimclimb Pathway"], "max": 20},
    {"q": "ギルドゲート", "has": ["Azorius Guildgate"], "alias": "ギルドゲート>ギルド門"},
    # colours, guilds, formats and rarities beside other words
    {"q": "ボロス 除去", "role": "removal", "has": ["Lightning Helix"], "only": "colors:RW"},
    {"q": "アゾリウス カウンター", "role": "counterspell", "has": ["Absorb"], "only": "colors:WU"},
    {"q": "モダン 除去", "role": "removal", "has": ["Path to Exile"], "hasnt": ["Swords to Plowshares"], "only": "legal:m"},
    {"q": "パウパー 除去", "role": "removal", "has": ["Lightning Bolt"], "only": "legal:a"},
    {"q": "神話レア ドラゴン", "has": ["Stormbreath Dragon"], "only": "rarity:mythic"},
    {"q": "白 クリーチャー", "has": ["Serra Angel"], "hasnt": ["Swords to Plowshares"], "only": "type:creature", "min": 3000},
    {"q": "1マナ クリーチャー", "has": ["Llanowar Elves"], "only": "cmc:1", "min": 500},
    {"q": "青 インスタント", "has": ["Counterspell", "Brainstorm"], "only": "type:instant"},
    {"q": "レア 土地", "has": ["Glacial Fortress"], "only": ["rarity:rare", "type:land"]},
    {"q": "スタンダード 火力", "role": "burn", "only": "legal:s"},
    {"q": "伝説のドラゴン", "has": ["Niv-Mizzet, Parun"], "hasnt": ["Shivan Dragon"]},
    {"q": "X呪文", "has": ["Fireball"], "only": "cost:X"},
]

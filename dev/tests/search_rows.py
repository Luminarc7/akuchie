# Search test cards: [id, oracle, name_en, name_ja, type_en, type_ja, oracle_en, oracle_ja, mana, colors, cmc, pow, tou, rarity, set, keywords, released, alt]
def R(i, en, ja, ten, tja, oen, oja, kw="", colors="B", cmc=2, rarity="common"):
    return [i, i + "-o", en, ja, ten, tja, oen, oja, "{1}{B}", colors, cmc, None, None, rarity, "tst", kw, "2020-01-01", ""]
SEARCH_ROWS = [
    R("s-altar", "Costly Altar", "高価な祭壇", "Artifact", "アーティファクト", "Sacrifice two permanents: Draw a card.", "パーマネント２つを生け贄に捧げる：カードを１枚引く。", colors=""),
    R("s-beast", "Annihilator Beast", "滅殺の獣", "Creature — Eldrazi", "クリーチャー — エルドラージ",
      "Annihilator 2 (Whenever this creature attacks, defending player sacrifices two permanents.)", "滅殺２（このクリーチャーが攻撃するたび、防御プレイヤーはパーマネント２つを生け贄に捧げる。）", kw="Annihilator", colors=""),
    R("s-scatter", "Scattered Thoughts", "散らばった思考", "Sorcery", "ソーサリー",
      "Sacrifice a creature.\nReturn target permanent card from your graveyard to your hand.\nDraw two cards.",
      "クリーチャー１体を生け贄に捧げる。\nあなたの墓地にあるパーマネント・カード１枚を対象とし、それをあなたの手札に戻す。\nカードを２枚引く。"),
    R("s-paired", "Paired Offering", "対の供物", "Instant", "インスタント",
      "As an additional cost to cast this spell, sacrifice two creatures or two permanents.\nDestroy target creature.",
      "この呪文を唱えるための追加コストとして、クリーチャー２体かパーマネント２つを生け贄に捧げる。\nクリーチャー１体を対象とし、それを破壊する。"),
    R("s-manaelf", "Mana Elf", "マナのエルフ", "Creature — Elf Druid", "クリーチャー — エルフ・ドルイド", "{T}: Add {G}.", "{T}：{G}を加える。", colors="G"),
    R("s-groveelf", "Grove Elf", "木立のエルフ", "Creature — Elf", "クリーチャー — エルフ", "{T}: Add one mana of any color.", "{T}：好きな色１色のマナ１点を加える。", colors="G"),
    R("s-sky", "Sky Healer", "空の癒し手", "Creature — Angel", "クリーチャー — 天使", "Flying\nWard {2}\nLifelink", "飛行\n護法{2}\n絆魂", kw="Flying,Ward,Lifelink", colors="W"),
    R("s-shatter", "Shatter Test", "粉砕テスト", "Instant", "インスタント", "Destroy target artifact.", "アーティファクト１つを対象とし、それを破壊する。", colors="R"),
    R("s-golem", "Wrecking Golem", "破壊のゴーレム", "Artifact Creature — Golem", "アーティファクト・クリーチャー — ゴーレム",
      "When Wrecking Golem enters, destroy target creature an opponent controls.", "破壊のゴーレムが戦場に出たとき、対戦相手がコントロールしているクリーチャー１体を対象とし、それを破壊する。", colors=""),
    R("s-study", "Careful Study Test", "入念な研究テスト", "Sorcery", "ソーサリー", "Draw two cards, then discard two cards.", "カードを２枚引き、その後カードを２枚捨てる。", colors="U"),
    R("s-rummage", "Rummage Test", "物色テスト", "Enchantment", "エンチャント", "Discard a card: Draw a card.", "カードを１枚捨てる：カードを１枚引く。", colors="R"),
    R("s-shield", "Permanent Shield", "永続の盾", "Enchantment", "エンチャント", "Creatures you control have hexproof.", "あなたがコントロールするクリーチャーは呪禁を持つ。", colors="W"),
    R("s-tapper", "Tapper Test", "タッパーテスト", "Creature — Human", "クリーチャー — 人間", "{T}: Tap target creature. It doesn't untap during its controller's next untap step.",
      "{T}：クリーチャー１体を対象とし、それをタップする。それはそれのコントローラーの次のアンタップ・ステップにアンタップしない。", colors="W"),
    R("s-fling", "Fling Test", "投げ飛ばしテスト", "Instant", "インスタント",
      "As an additional cost to cast this spell, sacrifice a creature.\nFling Test deals damage equal to the sacrificed creature's power to any target.",
      "この呪文を唱えるための追加コストとして、クリーチャー１体を生け贄に捧げる。\n１つを対象とする。投げ飛ばしテストはそれに、生け贄に捧げたクリーチャーのパワーに等しい点数のダメージを与える。", colors="R"),
    R("s-strike", "First Striker", "先制の兵", "Creature — Human Knight", "クリーチャー — 人間・騎士", "First strike", "先制攻撃", kw="First strike", colors="W"),
]

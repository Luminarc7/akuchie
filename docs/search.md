# How search works

Search is the heart of the site and the part that changes most. Everything here runs in the
visitor's browser over the card database (`LOCAL_DB`); no server is involved. The owner's goal
for search (project instructions): the best results for players, keeping the current style,
finding cards by their text, without punctuation, and by the words players actually use.

## From the search box to results

```
search box ──► startSearch() / runSearch()
                  │
                  ├─ database not loaded? ─► Scryfall live API (translateQuery(), weaker)
                  ▼
             runLocalSearch() ──► searchRows(query, state)
                                     │
                                     ├─ buildSearchPlan(query)      (memoised in PLAN_MEMO)
                                     │     └─ parseSearch(query)    what each word is
                                     ├─ filter every row            filters, phrases, roles, panel
                                     ├─ evaluateRow(row, plan)      tier 1/2/3 and a score
                                     └─ sort                        tier, relevance, closeness, A→Z
                                  ──► first 30 rows ──► hydrateRows() (pictures, prices from Scryfall)
                                  ──► resultTilesHtml() / textRowHtml(), renderMatchNote()
```

`searchRows()` returns `{ rows, info, plan }`. `info` feeds the line above the results
(`renderMatchNote()`): how a word was read, spelling fixes, role notes, tier headings.

## 1. Reading the query: `parseSearch()`

The query is normalised (`NFKC`, so full-width letters and digits become plain) and split into
tokens (`tokenizeQuery()`, which keeps `"quoted phrases"` together). Each token becomes one of:

| Token | Becomes | Example |
|---|---|---|
| A role word (when the tag file loaded) | `roles` | 除去, ドロー, ramp, `role:tutor`, `役割:除去` |
| `op:value`, `op>=value`… | `filters` (or `roles`/`sim`) | `o:draw`, `t:ゴブリン`, `色:赤`, `mv<=2`, `似:稲妻` |
| `-something` | a negative filter (not before a number: `-2:` is a loyalty ability, `-1/-0` a number) | `-t:creature`, `-飛行` |
| `"two words"` | `phrases` (exact phrase) | `"draw a card"` |
| A word in `WORD_FILTERS` | a type test | PW, 置物, X呪文 |
| A card shape (`CARD_SHAPES`; English names of several words are read first, `SHAPE_PHRASE_RE`) | a layout test, also `is:<id>` | 分割カード, 両面, MDFC, 変身カード, 反転カード, 出来事カード, split card, `is:mdfc` |
| A color or mana value alone, or before a type word (`narrowingWord()`) | a color / mana value filter; not inside a card name (`rolesLookLikeAName()`) or in quotes | 白 天使, 白の天使, 3マナ ゴブリン, 黒のクリーチャー, red goblin |
| A guild, shard or wedge (`COLOR_GROUP_WORDS`), a format (`FORMAT_WORDS`) or a rarity (`RARITY_WORDS`) beside other words | the same kind of filter (a guild = the cards a deck of its colors can play, a format = legal in it). These words are often part of names, so they narrow only beside other words that aren't one card's name (`wordsInOneName()`), or alone when no name starts with them (`nameStartsWith()`) | ボロス 除去, ゴルガリ 墓地, モダン 除去, パウパー 火力, 神話レア ドラゴン, レア 土地, boros removal |
| パワーN, タフネスN (以上/以下) | a power / toughness filter (`derivedFromWord()`; パワー 5以上 is joined first) | パワー3以上 クリーチャー |
| A card type beside a color, mana value, format or rarity, with nothing else but keyword abilities | a type filter, not text (`typeAsFilter` in `parseSearch()`); 土地 stays text beside a color, as lands have none | 白 クリーチャー, 1マナ クリーチャー, 青 インスタント, 白 飛行 クリーチャー, レア 土地 |
| A word in `EN_WORD_ALIAS` | the card's own wording | unblockable → can't be blocked, sac → sacrifice |
| Japanese text (mana symbols beside it too; `{T}:…` with an unknown "operator" is text) | `ja` | 墓地から手札, 飛行, `{T}:土地1つを対象とする` |
| Symbols only | a literal text filter | `%`, `🔥` |
| Anything else | `words` (English) | lightning, bolt |

**Rarity** (`r:m`, `r:rare`, the rarity buttons, 神話レア/レア/コモン as narrowing words) matches
every rarity the card was printed at, as Scryfall does (`hasRarity()` over the database's
`rarities`; `rarityName()` reads c/u/r/m/s/b, the English names and the Japanese ones). A card
found through another printing keeps its own picture; its tile says 神話レア版あり / "Mythic
printing" instead of its printing's rarity, which is the tooltip (`tileRarityHtml()`,
`wantedRarity()`).

**Operators** are `KNOWN_OPS` (including `is:` for card shapes) plus the Japanese names in `JA_OPERATORS` (効果→o, タイプ→t,
色→c, マナ総量→cmc, セット→e…). They are matched against a row in `localOperatorMatch()`;
an unknown operator returns `null` and the token is searched as text. To add an operator: add
its names to `KNOWN_OPS`/`JA_OPERATORS`, a `case` in `localOperatorMatch()`, a line in the search
tips (`GUIDE_ROWS`), and checks in `dev/searchbench/search_checks.py`.

## 2. Making a plan: `buildSearchPlan()`

The plan says how to test each row. English words go through `prepareEnglish()` (stop words
dropped, stems, spelling correction against words that exist on cards: `correctEnglish()`);
Japanese words through `prepareJapanese()` (split at particles, slang and spelling variants).
Punctuation (、。「」, `JA_PUNCT_RE`) is left out of both the search and the cards' text
(`normJaSearch()`), so a sentence typed with or without it matches; a typed 、 still separates
the parts of a word. A run-together English search that is part of a card name (`isNamePart()`)
also matches that name (`plan.en.nameKey`: "wrenchrigger", "snow covered island"), and such words
are not spelling-corrected.
`plan.graded` is true when the query has several words, so results are grouped by how closely
they matched.

The plan is memoised by query, language, tag state and database size (`PLAN_MEMO`), because it
is rebuilt on every keystroke.

## 3. Matching and tiers: `evaluateRow()`

Each row gets a **tier** (1 best) and a **score** (lower is better within a tier):

| Tier | Meaning (heading shown above the group) |
|---|---|
| 1 | The words together: the exact phrase or close together in one ability (`tier.1`) |
| 2 | Together with the card's name or type line standing in for one of them, or (one Japanese search) all the pieces in one ability (`tier.2`, `tier.2.ja`) |
| 3 | The words somewhere on the card, separately (`tier.3`) |

Tier 3 is hidden behind "show loose matches" (`state.showLoose`) whenever tier 1 or 2 found
anything. English is graded by `englishTier()` / `englishWordTier()`, Japanese by
`japaneseWordTier()` / `unitsTier()` with `locateJa()`.

Speed matters: `englishMayHave()` and `jaMayHave()` are quick pre-checks that throw out most
rows before the slower line-by-line tests. Keep any new test behind such a pre-check.

## Ordering

`searchRows()` sorts by tier first, then by the chosen order:

| Order (`state.sort`) | Then by |
|---|---|
| default (`name`) | `relevance()` (0 exact name, 1 name starts with it, 1.5 name contains it, 2 not in the name), then closeness of the match, then A→Z |
| `popular` | EDHREC rank from the tag file (`popularity()`) |
| `cmc_asc`, `cmc_desc` | mana value |
| `released_desc` | newest first |
| a role search | the card the word names, cards that mainly do this (`roleDemoted()`), then A→Z or popularity |
| `似:<card>` | similarity score |

**A→Z** in Japanese mode is あいうえお順 (the label says 一致・五十音順; あいうえお順 doesn't fit a phone): it sorts by the reading
of the Japanese name (`jaSortKey()`, from `name_kana`), so 稲妻 sorts under い. As in a
dictionary, ゛ ゜ and small kana only break ties (`gojuonKey()`): ゴブリン巡視部隊 (じゅんし)
comes before ゴブリン職工団 (しょっこう). Japanese names that start with a letter or a number
(A.I.M.の科学者, 500年日記, mostly Universes Beyond) come after the kana names, and cards with only
an English name after those, so a text search doesn't open on them. Readings are never shown;
they are searched only as described under "Names typed in hiragana".

A **nickname** (`CARD_NICKNAMES`) puts the card it names before everything else in the
default and "most played" orders.

## Names typed in hiragana (readings)

A search word all in hiragana, three letters or more (`yomiQuery()`), also matches the reading
of the card names (`rowYomi()`, from `name_kana`): いなずま finds 稲妻, いしのちから 意志の力,
しこうかこい 思考囲い. The readings write long vowels out (えむらくうる), so a typed ー is read
as the vowel before it, and ゔ as ぶ (`yomiKey()`). A whole reading is an exact name for
`relevance()`, the start of one counts as the name starting with the word. Game words typed in
hiragana (はかい, ひこう: the whole word reads as `JA_READINGS` words) are not matched this
way, or はかい would bring up 墓石 (はかいし).

## Nicknames and cards never printed in Japanese

`CARD_NICKNAMES` maps players' names for cards to the cards: ボルト → 稲妻, ブレスト →
渦まく知識, フォース/FoW → 意志の力, JTMS/神ジェイス, ボブ, トロン (the three Urza lands), and the
katakana names of cards with no Japanese printing (ブラックロータス, モックス, アンダーグラウンドシー
and the other original dual lands, タイムウォーク…). The whole search must be the nickname
(compared with `nameKey()`, so ブラック・ロータス and ぼると count). `nicknameRows()` finds the
cards; `searchRows()` shows them first, then what the word finds as usual (other ボルト names),
with the note 「ボルト」は「稲妻」としても検索しました. Letter nicknames (FoW, JTMS) show only the
card, so they are not spelling-corrected into other words. To add one: a line in
`CARD_NICKNAMES` (English name, as on Scryfall) and an entry in
`dev/searchbench/common_searches.py`.

## Japanese names typed slightly wrong

When a Japanese search finds nothing, or only loose matches, `closestJaName()` looks for the
card name or name part (the part after 、 or //) closest to it: one letter different for up
to five letters, two for longer words, compared with ヴァ as バ, small kana as large and ー left
out (`looseKana()`). The most played card wins a tie. That name is searched instead and the
note says so (「渦巻く知識」は「渦まく知識」として検索しました). Examples: 渦巻く知識, 意思の力,
ジェース, エムラクル, ラガヴァン, じぇーす. The list of name parts (`NAME_PARTS`) is built the
first time it is needed.

## Names without punctuation

`nameKey()` lowercases, folds hiragana to katakana and removes punctuation and spaces
(`NAME_PUNCT_RE`), so "yawgmoth thran" finds "Yawgmoth, Thran Physician" and らがばん finds
ラガバン. It also drops accents, so "lim dul" finds Lim-Dûl. `relevance()` and the name
suggestions (`nameSuggestions()`) use it. Older Japanese names (`alt_names_ja`) match too.

## A card's own name in its text

Older Japanese text names the card itself (石の雨…、灰色熊が死亡したとき) where newer cards say
このクリーチャー, この土地. For the search, `rowJaText()` reads the card's own name (and its older
names) in its text the newer way (`jaSelfWord()` picks the word from the type line), so
このクリーチャーが戦場に出たとき finds both. Instants and sorceries keep their names. The
slang step also tries このオーラ for このエンチャント and この装備品 / この機体 for
このアーティファクト.

## Players' words (slang)

| Table | What it does | Examples |
|---|---|---|
| `JA_SLANG` | Rewrites Japanese slang to the cards' wording (regular expressions, applied in `jaSlangForm()`) | 山札→ライブラリー, 3ダメージ→3点のダメージ, 2ドロー, サクる→生け贄に捧げ, キャストする→唱える (キャストしたとき→唱えたとき・唱えるたび), ハンド→手札, トークンを作る/出す→トークンを生成, 兵士トークン→兵士・クリーチャー・トークン, ギルドゲート→ギルド門 |
| `JA_KW_SLANG` | Katakana English keyword names to the official Japanese | フライヤー→飛行, ヘイスト→速攻 |
| `JA_ORTHO` | Spelling variants | 全て→すべて, 時→とき, 飛行をもつ→飛行を持つ |
| `EN_WORD_ALIAS` | English slang to card wording | unblockable, flyer, sac, lifeloss |
| `WORD_FILTERS` | A word that means a kind of card | PW, 置物, X呪文 (X in the mana cost) |
| `AMBIG_ROLE_WORDS` | Words that are only sometimes slang; searched as text, the note offers the role | カウンター, ロード, ラス, ティム |

When a word is read as something else, the note above the results says so (`plan.aliases`).
To add slang: add the entry, then a check in `dev/searchbench/search_checks.py` with a real card
that should (and one that should not) be found.

## Roles (what a card does)

Players search by role: 除去, ドロー, サーチ, マナ加速, サクり台… Each role is a line in
`ROLE_LIST`: `[id, Japanese label, English label, Tagger tags, options, Japanese words,
English words]`. Most roles come from **Scryfall Tagger** oracle tags, published weekly by
warujie-prices as `t/tags.json.gz` (`loadTags()`, `TAG_MAP`); a few are read from the English
text with regular expressions (`ROLE_TEXT`, `ROLE_TESTS`). A role word counts only as a whole,
unquoted word, so トランプル is still trample text and `"ランプ"` searches the text.

Land nicknames are roles too: フェッチランド, ショックランド, バウンスランド, デュアルランド,
タップイン, and from the rules text ペインランド (`painland`), チェックランド (`checkland`),
ファストランド (`fastland`), スローランド (`slowland`), ミシュラランド/マンランド (`manland`); from the
card's type and layout トライランド (three colors, Triomes too: `ROLE_TESTS.triland`) and
パスウェイ (`ROLE_TESTS.pathway`). A Japanese role word typed with a space in it (ライフ 回復,
全体 除去) is read as the role, as English phrases are (`findRoleWords()`).

To add a role: a `ROLE_LIST` line; if it uses a tag the site doesn't fetch yet, add the tag to
`TAGS` in warujie-prices `build_tags.py` (the next weekly build picks it up, or run it with
`--force`). If the tag file is missing, role words fall back to text and the note says so
(`rolesOff`).

## Similar cards (`似:`)

`似:<card name>` (also `sim:`, `like:`) and the "similar cards" box on card pages use
`buildSimIndex()` / `similarTo()`: a TF-IDF comparison of the English rules text (stemmed
words and word pairs, numbers generalised) and type words, mixed 60/40 with the overlap of the
cards' main roles. The index is built in the background the first time it's needed. The
card page's toggles (same colours, no higher mana value, same type: `simPasses()`) are saved in
`akuchie-similar`.

## Other search features

| Feature | Where |
|---|---|
| Name suggestions while typing | `nameSuggestions()`, `attachNameSuggest()` |
| Highlighting the matched text | `highlightRanges()`, `highlightHtml()` |
| "No results" help (closest names, closest words, recent searches) | `renderZeroHelp()`, `fuzzyNameRows()`, `closestKnownWord()` |
| Recent searches (this browser only) | `rememberSearch()`, `akuchie-recent` |
| The filter panel | `state`, `localFilterRow()`, `syncFilterUI()` |
| Random cards on the home page | `loadRandomCards()` |
| Combo hint above results (preview page only) | `updateComboHint()` |

## Tests for search

- `dev/searchbench/search_checks.py` runs real searches against the real database and role
  tags. `dev/searchbench/common_searches.py` lists the 100 searches Japanese players type most
  (names, readings, typos, nicknames, rules text, slang, land nicknames, colors/guilds/formats/
  rarities) with what each must find; each is one check. A search that should work and doesn't
  belongs on that list. **Add a check for every search change**, including one that proves a wrong card is
  *not* found. One check types a sentence of 300 random cards' own text plainly (no 、,
  half-width numbers) and their English names in lower case without punctuation, and expects
  each card to be found (at most 1% missed).
- `dev/tests/e2e.py` covers the search interface with fixture cards (`dev/tests/search_rows.py`).
- `dev/searchbench/harness.py` opens the site with the real data for screenshots or
  reproducing a bug.

See [workflow.md](workflow.md) for how to run them.

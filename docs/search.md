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
| A word in `WORD_FILTERS` | a type test | PW, 置物 |
| A card shape (`CARD_SHAPES`; English names of several words are read first, `SHAPE_PHRASE_RE`) | a layout test, also `is:<id>` | 分割カード, 両面, MDFC, 変身カード, 反転カード, 出来事カード, split card, `is:mdfc` |
| A color or mana value alone, or before a type word (`narrowingWord()`) | a color / mana value filter; not inside a card name (`rolesLookLikeAName()`) or in quotes | 白 天使, 白の天使, 3マナ ゴブリン, 黒のクリーチャー, red goblin |
| A word in `EN_WORD_ALIAS` | the card's own wording | unblockable → can't be blocked, sac → sacrifice |
| Japanese text (mana symbols beside it too; `{T}:…` with an unknown "operator" is text) | `ja` | 墓地から手札, 飛行, `{T}:土地1つを対象とする` |
| Symbols only | a literal text filter | `%`, `🔥` |
| Anything else | `words` (English) | lightning, bolt |

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

**A→Z** in Japanese mode sorts by the reading of the Japanese name (`jaSortKey()`, from
`name_kana`), so 稲妻 sorts under い. Readings are never shown or searched.

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
| `JA_SLANG` | Rewrites Japanese slang to the cards' wording (regular expressions, applied in `jaSlangForm()`) | 山札→ライブラリー, 3ダメージ→3点のダメージ, 2ドロー, サクる→生け贄に捧げ |
| `JA_KW_SLANG` | Katakana English keyword names to the official Japanese | フライヤー→飛行, ヘイスト→速攻 |
| `JA_ORTHO` | Spelling variants | 全て→すべて, 時→とき |
| `EN_WORD_ALIAS` | English slang to card wording | unblockable, flyer, sac, lifeloss |
| `WORD_FILTERS` | A word that means a kind of card | PW, 置物 |
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
  tags. **Add a check for every search change**, including one that proves a wrong card is
  *not* found. One check types a sentence of 300 random cards' own text plainly (no 、,
  half-width numbers) and their English names in lower case without punctuation, and expects
  each card to be found (at most 1% missed).
- `dev/tests/e2e.py` covers the search interface with fixture cards (`dev/tests/search_rows.py`).
- `dev/searchbench/harness.py` opens the site with the real data for screenshots or
  reproducing a bug.

See [workflow.md](workflow.md) for how to run them.

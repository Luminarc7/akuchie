# A map of `index.html`

`index.html` is the whole site: about 9,000 lines in three blocks.

| Block | What's in it |
|---|---|
| `<head>` | Title and share tags (the Worker rewrites some for bots), the manifest, and a tiny script that applies the saved theme, language and lightweight mode before the page paints and loads the web fonts. |
| `<style>` | All the CSS. Colours are CSS variables, set for dark (`:root, html[data-theme="dark"]`) and light (`html[data-theme="light"]`). Lightweight mode is `html[data-lite="1"]`; the current view is `html[data-view="…"]`; the home page is `html[data-home="true"]`. |
| `<body>` HTML | The fixed skeleton: top bar, home hero, filter panel, results, and one empty `<div>` per view. Most content is drawn later by JavaScript. |
| `<script>` | All the behaviour, in sections marked `// ---- name ----`. |

To see the sections with their current line numbers:

```sh
grep -n -- '// ---- ' index.html
```

**Never edit `preview.html`.** After changing `index.html`, run `python3 tools/make_preview.py`.

## The HTML skeleton

| Element | What it is |
|---|---|
| `header.topbar` | Logo (`#brandLink`), the search box (`#searchForm`, `#searchInput`, suggestions `#searchSuggest`), the tabs (`#tabSearch`, `#tabSets`, `#tabMeta`, `#tabPrices`), the want list button (`#wantBtn`, count `#wantN`), which opens the tray, the JP \| EN and ¥ \| $ switches (`#langBtn`, `#curBtn`), theme and lightweight switches (`#themeSwitch`, phones: `#menuBtn`) |
| `#searchView` | The home page and search results. Inside: `#homeHero` (big search box `#heroInput`, "try this" `#heroTry`, effect examples `#heroExample`), `#homeBoxes` (price risers `#homeMovers`, top decks `#homeMeta`), `#filterPanel`, the result bar (`#resultCount`, `#viewToggle`, `#sortSelect`, `#activeFilters`), search tips `#guidePanel`, notes above results (`#translationNote`, `#comboHint`, `#matchNote`), the results `#cardGrid`, `#loadMoreRow` |
| `#cardView` | The card page; everything is drawn into `#cardViewCard` |
| `#setsView` | Set list (`#setListPanel`) and one set (`#setDetailPanel`, `#setGrid`) |
| `#metaView` | The metagame tab |
| `#pricesView` | Price movers |
| `#deckView` | One deck's page |
| `#importView` | The want list and deck price page: the switch between the two lists (`#impWhich`), the title and words above the box (`#impTitle`, `#impLead`, `#impLabel`), the list's box (`#importForm`, `#importText`, `#importClear`) and the result (`#importBody`) |
| `#wantTray`, `#wantTrayBg` | The want list's tray (from the right, over a dimmed page), drawn by `drawTray()`; with `#wantToast`, the note after adding or removing a card, just above the footer |
| `#artPicker`, `#artPickerBg` | The deck price page's art picker (every printing of a card), drawn by `drawArtPicker()` |
| `footer.attribution` | Data credits, the Fan Content Policy notice, the privacy promise and the contact link (address assembled in JS) |

`showView(name)` shows one of the views and marks the right tab.

## The script, section by section

In file order. "Key names" are what to search for.

### Set-up and shared helpers (top of the script, no marker)

- `EDITIONS`, `SITE`: the retired colour editions; only `main` is left. Keep as is.
- `STR`, `t(key, vars)`, `tn(key, n)`: every interface string, Japanese then English. See
  [interface.md](interface.md).
- `state`: the search state (query, colour/type/keyword/mana/role/rarity sets, format, sort,
  image/text view, `showLoose`). The filter panel, the URL and the search all read it.
- `CREATURE_TYPE_JA`, `JA_KEYWORDS`, `JA_PHRASES`, `JA_OPERATORS`: Japanese words for creature
  types, keyword abilities, rules phrases and search operators.

### Card database and Scryfall

| Section marker | What it does | Key names |
|---|---|---|
| `Japanese card-name index (legacy, name-only)` | An old fallback when only `ja_names.json` exists. Not deployed any more. | `JA_NAME_INDEX` |
| `local card database (full, effect-text-searchable)` | Downloads and unpacks the database, turns each row into an object with pre-computed lowercase fields, starts the idle-time warm-up. | `LOCAL_FIELDS`, `LOCAL_DB`, `dbState`, `dbReady`, `DB_FILES`, `fetchMaybeGzipJson()`, `loadCardDatabase()`, `indexRow()`, `warmSearch()`, `rowToCard()`, `hasRarity()`, `rarityName()`, `RARITY_CODE`, `RARITY_ORDER`; the printings in the database (every set, treatments, 日本語版): `TREATMENTS`, `treatmentTest()`, `hasJaPrinting()`, `setCodesOf()`, `printWordForms()` |
| `Scryfall's /cards/collection…` | Fetches full card objects (pictures, prices) for result rows, 100 ms apart, retries 429/5xx, caches for the visit. Also local matching helpers (types, names, operators, filter panel). | `scryfallTurn()`, `scryfallCollection()`, `CARD_CACHE`, `hydrateRows()`, `nameKey()`, `textMatches()`, `localOperatorMatch()`, `localFilterRow()`, `relevance()`, `yomiQuery()`, `rowYomi()`, `jaSortKey()`, `popularity()`, `ROLE_LIST` |
| `the tag file` | Loads the role tags and EDHREC ranks from warujie-prices `t/tags.json.gz`. | `loadTags()`, `TAG_MAP`, `tagsState`, `rowTags()`, `rowRoles()`, `hasRole()` |
| `reading role words in the search box` | Finds role words (除去, ドロー, ramp…) and the colour/guild/format/rarity/type/mana words that narrow them. | `findRoleWords()`, `splitRoleToken()`, `derivedFromWord()`, `COLOR_GROUP_WORDS`, `FORMAT_WORDS`, `RARITY_WORDS`, `AMBIG_ROLE_WORDS`, `roleSuggestions()` |
| `spelling…` | Corrects English words that appear on no card to the nearest one that does. | `enVocab()`, `editDistance()`, `correctEnglish()` |
| `reading the search box` | Splits the query into operators, quoted phrases, English words and Japanese words; slang aliases. | `parseSearch()`, `KNOWN_OPS`, `WORD_FILTERS`, `narrowingWord()`, `nameStartsWith()`, `wordsInOneName()`, `EN_WORD_ALIAS`, `prepareEnglish()`, `englishTier()` |
| `Japanese` | Japanese text matching: splitting at particles, slang, spelling variants, verb endings. Then nicknames, typo correction, the search plan, scoring and ordering. | `normJaSearch()`, `JA_SLANG`, `JA_KW_SLANG`, `JA_ORTHO`, `prepareJapanese()`, `japaneseWordTier()`, `CARD_NICKNAMES`, `nicknameRows()`, `closestJaName()`, `buildSearchPlan()`, `evaluateRow()`, `searchRows()`, `resultTilesHtml()`, `renderMatchNote()` |
| `format legality` | Format names and legality badges; the Scryfall-fallback translation of Japanese queries. | `FORMAT_JA`, `FORMAT_ORDER`, `MAIN_FORMATS`, `legalityHtml()`, `translateQuery()`, `FORMAT_CODE`, `buildSearchQuery()` |

### Drawing cards and prices

| Section marker | What it does | Key names |
|---|---|---|
| `card pictures` | Picks the best picture (real scan over placeholder), `srcset` sizes. | `imageQuality()`, `pictureTag()`, `getImage()` |
| `exchange rate (USD -> JPY)` | Dollar and euro to yen; redraws every price. | `fetchJpyRate()`, `USD_JPY`, `EUR_JPY`, `updateYenLabels()` |
| `currency: every price in ¥ or $…` | The ¥ \| $ switch: each price in the chosen currency, the shop's own on hover. | `CUR`, `curHtml()`, `curText()`, `fromYen()`, `setCurrency()` |
| `prices` | Prices on result tiles; a Japanese printing borrows its English twin's prices. | `effectivePrices()`, `ensureEnglishPrices()`, `tilePriceHtml()` |
| `Japanese names/text for any printing` | Japanese name, type and text for any printing, from the database when Scryfall lacks them; type-line translation. | `displayNameJa()`, `displayTypeJa()`, `displayTextJa()`, `translateTypeLine()`, `cardNames()` |
| `treatments…` | Labels such as borderless, showcase, extended art; the result tile and its rarity (the rarity asked for, with an arrow, when the search asks for a rarity its printing doesn't have). | `treatmentLabels()`, `cardTileHtml()`, `tileRarityHtml()`, `wantedRarities()` |
| `prices on the card page, by market` | JP / US / EU price tabs. | `PRICE_MARKETS`, `priceMarket`, `marketRows()`, `priceHtml()` |
| `listings and stock…` | Per-shop offers by condition, cheapest first. | `OFFER_SHOPS`, `offerRows()`, `offersHtml()` |
| `the notes under the card page…` | Where each price comes from; loads today's shop prices (`q/`). Also the card page itself. | `priceNotesHtml()`, `loadCardQuotes()`, `renderCardViewContent()` |
| `links to shops and deck sites` | Search links to shops (Japanese, US, EU) and deck sites; all printings. | `JP_SHOP_SEARCH`, `JP_MAIN_SHOPS`, `jpShopDirHtml()`, `hareruyaUrl()`, `tcgplayerUrl()`, `loadPrintings()` |
| `the printing's language: 日本語版 / 英語版` | The language buttons under the picture, from the printings file (`printings.json.gz`) or one Scryfall search. | `PRINT_LANGS`, `SET_TWIN`, `loadPrintingsFile()`, `printingLanguages()`, `fillPrintToggle()`, `openPrinting()`, `showView()`, `navigateToCard()` |

### Pages, navigation and controls

| Section marker | What it does | Key names |
|---|---|---|
| `set browser` | Set list and one set's cards. | `SET_GROUPS`, `SET_NAME_JA`, `loadSets()`, `openSet()` |
| `routing` | URL ↔ view. Also runs a search (`runSearch()`), random cards, the live-API fallback. | `routeFromUrl()`, `applyRoute()`, `goTo()`, `resetToHome()`, `runLocalSearch()`, `runSearch()` |
| `controls` | Sort, view and load-more controls. | `refreshResults()`, `hasActiveFilters()` |
| `filters` | The filter panel: colours, types, creature types, keywords, mana value, roles, rarity, format; similar cards (`似:`). | `syncFilterUI()`, `removeFilter()`, `wireCheckList()`, `similarTo()`, `showSimilar()`, `showCardRoles()` |
| `recent searches…` | Last 10 searches in `localStorage`; the "no results" help. | `RECENT_KEY`, `rememberSearch()`, `renderZeroHelp()`, `fuzzyNameRows()` |
| `themes: light / dark` | Theme and lightweight mode switches; the contact link. | `setTheme()`, `setLite()` |
| `search tips…` | The tips table under the results. | `GUIDE_ROWS`, `GUIDE_EXAMPLES`, `renderGuide()` |
| `links between the main site and the colour editions` | Retired; harmless. | `renderSiteSwitch()` |
| `language switch` | Redraws everything in the other language; the top bar's switches; prices redrawn after the ¥ \| $ switch. | `applyStaticText()`, `setLang()`, `syncTopToggles()`, `redrawPrices()` |
| `metagame tab` | Deck shares, win rates, trends. | `META_FORMATS`, `META_MIN_MATCHES`, `loadMeta()`, `renderMeta()` |
| `deck names in Japanese…` | Turns English archetype names into the words Japanese players use (ディミーア・ミッドレンジ, 赤単バーン); a name with an unknown word stays English. | `DECK_NAME_WHOLE`, `DECK_GUILD_JA`, `DECK_MONO_JA`, `DECK_WORD_JA`, `deckNameJa()`, `deckLabel()`, `toggleMetaRow()` |
| `price history & price movers` | The price chart on card pages and the movers tab. | `PRICE_DATA_URL`, `loadPriceShard()`, `priceHistoryId()`, `drawPriceHistory()`, `loadMovers()`, `renderMovers()` |
| `combo suggestions` | Commander combos (only where `data-combos="1"`, i.e. the preview page). | `COMBOS_ON`, `loadCardCombos()`, `comboText()` |
| `highlighting…` | Marks the matching part of a card's text. | `highlightRanges()`, `highlightHtml()` |
| `the text view of the results` | Text-only results. | `textRowHtml()`, `renderViewToggle()` |
| `more results load by themselves…` | Auto "load more" near the bottom. | `watchAutoLoad()` |
| `card name suggestions under the search boxes…` | The dropdown of card names while typing, each with a green ＋ that adds one copy to the want list (or the list on the deck price page). | `nameSuggestions()`, `attachNameSuggest()`, `suggestAdd()`, `suggestAddList()` |
| `install as an app` | Registers `sw.js` (HTTPS only, not on github.io) and shows the install button in the footer. | `installButton`, `#appInstall` |
| `home: …` (three sections) | Example searches, three effects to try, price risers and top decks on the home page. | `HERO_TRY`, `HERO_EFFECTS`, `HERO_SLANG`, `pickHeroEffects()`, `renderHomeMovers()`, `renderHomeMeta()` |
| `phones: the theme buttons sit in a small menu` | The phone menu. | `setMenu()` |
| `deck pages` | One deck: sample lists, card groups, trend. | `loadMetaDecks()`, `loadMetaLists()`, `renderDeck()`, `drawDeck()` |
| `export…` | Copy or download a list for MTG Arena or Magic Online. | `exportName()`, `deckExportText()`, `saveTextFile()` |
| `deck price page…` | The page of the two lists (the pasted deck, the want list) and the switch between them: see what a list costs; the list's name box; − n ＋ and the art button on each card and row; the pictures and prices of the printings the lines name. | `setList()`, `drawImportHead()`, `parseDeckText()`, `importRow()`, `readImport()`, `priceImport()`, `drawImport()`, `textWithName()`, `impCardHtml()`, `impRowHtml()`, `PRINT_CARDS`, `loadPrintCards()`, `PRINT_PRICES`, `entryYen()`, `loadPrintPrices()`, `lineWithPrint()` |
| `art picker…` | Every printing of a card, to pick the one the list names. | `openArtPicker()`, `drawArtPicker()`, `pickArt()` |
| `want list…` | ☆ on results and card pages, the want list's cards and counts, the tray. | `wantTogHtml()`, `wantCardHtml()`, `listSetCount()`, `wantData()`, `refreshWant()`, `drawTray()` |
| `the search box follows the page` | Sticky search bar when the hero scrolls away. | `updateHeroOut()`, `updateBarTop()` |
| `start…` | Applies the saved language, then the route. | |

## Conventions in the code

- **Plain JavaScript**, no modules, no build. Everything is global inside one `<script>`.
- **Comments say why**, in plain English. Keep them that way.
- **Two languages always.** Any new visible text goes in `STR` with Japanese and English.
- **HTML is built with template strings.** Always pass outside text through `esc()`.
- **Race guards.** Searches carry a token (`searchToken`); a slow answer for an old search is
  dropped. Card-page loaders check `shownCard === card` before drawing.
- **Memo caches** (`PLAN_MEMO`, `TERM_MEMO`, `STEM_MEMO`…) keep typing fast. When a memo key
  depends on something new (for example the language), add it to the key.
- **Row fields starting with `_`** (`_nameEn`, `_typeEn`, `_colors`, `_cmc`…) are computed in
  `indexRow()` when the database loads; they are not in the file.
- **Browser storage keys start with `akuchie-`** for historical reasons. Don't rename them
  (visitors would lose their settings). New keys start with `warujie-` (`IMPORT_SAVE_KEY`, `WANT_SAVE_KEY`, `WANT_VIEW_KEY`).

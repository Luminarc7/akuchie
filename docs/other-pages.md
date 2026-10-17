# Home, sets, metagame, decks, deck price page, want list, price movers, export, app

All pages are views of the same `index.html`. The URL decides which one shows
(`routeFromUrl()` → `applyRoute()`); tabs and links change the URL with `goTo()` so the back
button works.

| URL | View | Drawn by |
|---|---|---|
| `/` | Home and search results | `startHome()`, `runSearch()` |
| `?card=<id>[&print=<lang>]` | Card page | `renderCardViewContent()` (see [card-page.md](card-page.md)) |
| `?view=sets` | Set list | `renderSetList()` |
| `?set=<code>[&lang=ja\|en]` | One set | `openSet()` |
| `?view=meta[&format=modern][&days=30]` | Metagame tab | `renderMeta()` |
| `?view=deck&format=…&days=…&deck=<name>[&u=1][&list=N]` | One deck | `renderDeck()`, `drawDeck()` |
| `?view=prices[&market=us\|eu][&win=1\|7\|30][&dir=up\|down]` | Price movers | `renderMovers()` |
| `?view=import[&list=<a deck list>]` | Want list and deck price page (one list) | `renderImport()`, `priceImport()`, `drawImport()` |
| `?view=want` | The old want list address: opens `?view=import` | `routeFromUrl()` |

Adding a view: a branch in `routeFromUrl()` and `applyRoute()`, a `<div id="…View">` in the
HTML, a line in `showView()`, a tab or link, share tags in `worker.js` `shareTags()`, and checks
in `dev/tests/e2e.py`.

## Home

`html[data-home="true"]` while the home page shows (`setHomeMode()`).

| Part | Where |
|---|---|
| Big search box | `#homeHero`, `#heroInput`; it hands off to the top bar's box as you scroll (`updateHeroOut()`) |
| "Try this" example searches | `HERO_TRY`, `renderHeroTry()` |
| Three effects, each with a card that has it, and slang examples | `HERO_EFFECTS`, `HERO_SLANG`, `pickHeroEffects()`, `renderHeroExample()` |
| Price risers box | `renderHomeMovers()` (from `movers.json`) |
| Top decks box | `renderHomeMeta()`, `HOME_META_FORMATS` (from `meta.json`) |
| Secret Lair and booster box boxes (Rakuten Books, sliding strips) | `renderHomeShop()`, `renderShopBox()`, `#homeShop`, `#homeBoxShop` (from `worker.js` `/shop/rakuten`; see [Shops](#shops-rakuten-books-and-amazon)) |
| Random cards below | `loadRandomCards()` (`RANDOM_COUNT`), from the local database, or Scryfall's `/cards/random` without it |

## Sets

The set list comes from Scryfall's `/sets` (paper sets with cards, newest first), grouped by
type (`SET_GROUPS`) and filterable. Japanese set names are in `SET_NAME_JA`, a hand-made list:
add new sets there when they come out (the Rakuten box search on set pages uses it too). One set's cards come from a Scryfall search
(`setSearchUrl()`), Japanese printings when `lang=ja`.

### Shops: Rakuten Books and Amazon

Things to buy, with affiliate links once the owner has the IDs ("shops" section of
`index.html`).

- **Where:** two home-page boxes the size of the price movers box, Secret Lair (`#homeShop`) and
  booster boxes (`#homeBoxShop`), each drawn by `renderShopBox()`. Each is a sideways strip of
  products (`shopCardHtml()`: big picture, 予約受付中 / NEW / 在庫あり on it, title, release
  date, price), newest first, with ‹ › buttons. Like Rakuten's motion widget it moves on by itself
  every `SHOP_MOTION_MS` (`startStripMotion()`), back to the start at the end; it stops under the
  pointer or a finger, with focus, off screen, in a background tab, and never moves when the
  visitor's system asks for reduced motion. Also a "このセットのBOXを買う" strip on set pages (`renderSetShop()`, `#setShop`)
  for sets in `SHOP_SET_TYPES` released in the last three years or upcoming. Not in
  lightweight mode.
- **Products come from Rakuten's API**, asked by `worker.js` (`/shop/rakuten`, see
  [hosting.md](hosting.md#workerjs)) and read by `loadShopItems()`. A set's boxes are searched by
  its `SET_NAME_JA` name (Rakuten's titles are Japanese), so a set missing from that list finds
  nothing and falls back to a search link. Without the worker (GitHub Pages, local tests) or
  before Rakuten's keys are set, each place shows a Rakuten Books search link instead
  (`rakutenSearchUrl()`).
- **Amazon** has no product list (its API needs sales first): set pages get an Amazon search link
  for the set's boxes (`amazonSearchUrl()`).
- **Rakuten's rules:** the parts made from Rakuten's API link only to Rakuten and carry the
  credit `RAKUTEN_CREDIT` unchanged; Amazon sits in a separate part (`.set-shop-part.amazon`).
- **Affiliate IDs:** `AFFILIATE` (`rakuten`, `amazon`). Both are public by nature, so they are
  in the page, not secrets. Empty = plain links. Set, links get `rel="sponsored"` and a "PR" mark
  (Japan's stealth-marketing rules), Rakuten links become Rakuten Affiliate links
  (`rakutenLink()`, or the API's own `affiliateUrl`), Amazon links get `&tag=`, and the footer
  switches to `footer.privacy.aff` (says the PR links are affiliate ads) and shows Amazon's
  required line `footer.amazon`.

## Metagame tab

Reads `meta.json` from the site itself (`loadMeta()`), which `build_meta.py` rebuilds every day
(see [data.md](data.md#metagame-files)). Shows, per format (`META_FORMATS`) and period (30 or
90 days), each archetype's share of the field, match win rate with its confidence range, the
weekly trend (sparklines from `trends`) and key cards. A win rate from fewer than
`META_MIN_MATCHES` matches is hidden as noise; when most decks are below it, a note offers the
period with more matches. The ⓘ button (`#metaHelpBtn`, text in `STR` `meta.help`) explains how to
read the numbers. The deck icon is a card's art crop (`deckArtHtml()`, credited with
`creditDeckArt()`). A sample list's finish comes from the source as written; `placeText()` puts a
wrong ordinal right (the sources write 2st, 3st, 22th), here and on deck pages.

- **Deck names in Japanese.** Archetype names arrive in English from MTGOFormatData.
  `deckNameJa()` translates them: whole names first (`DECK_NAME_WHOLE`), then guild and mono-colour
  words (`DECK_GUILD_JA`, `DECK_MONO_JA`) and deck words (`DECK_WORD_JA`). A name with any word
  not in the lists stays English. `deckLabel()` shows the Japanese name with the English one
  small beside it, here, on deck pages and in the home page's top decks. New archetypes need
  their words added to these lists.
- **Phones** (`META_PHONE`, 760px): each deck is one short row; tapping it opens the details
  (`toggleMetaRow()`). Closed rows show a short name the way players say it
  (`deckNameShort()`: guilds as colour pairs from `DECK_GUILD_SHORT`, words from `DECK_WORD_SHORT`,
  e.g. 青黒ミッド, 白青コン, UB Mid); the open row shows the full name, and the English name only
  when open. A closed row keeps its name on one line: `fitMetaNames()` shrinks the font of a long
  name (down to `META_NAME_MIN` px) after each render, resize and toggle, and the mana symbols are
  small (11px) so the name and its colours sit as one centred block. The name, price, share and
  win rate share the row's first line (see "Sizes that should match" in [interface.md](interface.md)). The format buttons show
  two-letter codes (`FORMAT_SHORT`: ST, Pi, Mo, LC, VT, Pa, the owner's choice), the
  periods 30日/30d, the ⓘ button no words, and the win-rate column says 勝率/Win%; each button
  keeps its full name as a tooltip (`.sh-full` / `.sh-short` spans).
- **Rank arrows.** In the default share order, each rank has ▲ or ▼ beside it when the deck's
  average weekly share over the last 4 weeks rose or fell by `META_RANK_SHARE` (2) points or more
  against the 4 weeks before (`rankMoveHtml()`, `metaRankMoves()`, from `trends`: the same weeks
  as the ▲▼pt numbers). Under 2 points is shown as a grey — (no real change), whatever the rank
  did; the tooltip also says how the rank moved. A deck absent from the earlier 4 weeks gets ▲.
- **Deck price.** A 価格 column left of the share shows about how much the sample list costs in
  yen (`metaCostsFor()`, cached in `metaCosts`; a + when some cards have no price), and the sort menu has 安い順 (cheapest first;
  decks without a price go last). In Standard, the Arena wildcards the list needs appear too
  (`wildcardsHtml()`).

### How a deck's price is worked out

`deckCost()` adds up, for every card in the main deck and sideboard, the cheapest paper
printing's price (`cheap.json.gz` from warujie-prices, `loadCheapest()`, matched by
`cheapRow()`): the lower of USD × the dollar rate and EUR × the euro rate (`cardYen()`).
Basic lands count as free (`isBasicLand()`). Totals are rounded (`yenRound()`) and shown as
「約¥…」; when some cards have no price, `costText()` says 「〜」 and the deck page says how many
are missing. Wildcards count each card at its lowest Arena rarity (`RARITY_LETTER`, falling back
to the database's rarity when the price file has none).

## Deck pages

`renderDeck()` reads `meta_decks.json` (one real list per deck: its best finish in the period,
with how often each card is played across all lists) and `meta_lists/<days>-<format>.json`
(more sample lists, loaded only when asked for). Cards are grouped by type (`DECK_GROUPS`);
image or list view is saved in `akuchie-deck-view`. The trend chart is `deckTrendHtml()`.
Under the title, `deckCostHtml()` draws two one-line boxes of the same height, side by side
(on phones the wildcard box is labelled just "Arena"): 価格 and the deck's price in yen
(how it is worked out is a tooltip and the note at the foot of the page) and the Arena wildcards (Standard only; the rarity names are tooltips). The sample-list picker sits in a
bar that stays under the top bar while the page scrolls (`.deck-pick-bar`). After the main deck
and sideboard, `deckCurveHtml()` draws the mana curve of the main deck's non-land cards (0 to
6+). Each card also shows its own cheapest price (`.dc-yen` in image view, `.dl-yen` in list
view).

## Want list and deck price page (one list)

`?view=import` (`#importView`, titled ウォントリスト・デッキの価格): one list, which the ☆
buttons fill and where a deck list can be pasted, priced in yen and taken elsewhere. The owner
asked for the want list's own page and the deck price page to become one, in the deck price
page's style, and for the top bar's ☆ to open a tray of the list (MTGGoldfish's card tray was the
example), 2026-10-17. `?view=want`, the want list's old address (never live), opens this page.
It belongs to the price tab (the tab bar marks 価格 while it is open; the owner moved it there
from the metagame tab, 2026-10-16). Ways in: the tray's 価格を見る・書き出す, the デッキの価格を調べる
button, its own button right of the price tab's bar (shortened for it, and the same height: the
  dates and count, `#moverSummary`, sit under both) on wide screens
  (`.mv-top` holds both and keeps them under the top bar; under 761px it steps aside with
  `display: contents`, so the bar sticks alone and the button sits between it and the lists),
  bigger than the bar's toggles at the owner's request (`.imp-open`,
`a[data-import]`), and 編集して計算 on a deck page (`.deck-edit`), which opens the shown list there
(with the deck's name) so cards can be swapped and the price follows.

### The list

- **It is text**: the box's text, `listText`, kept in the browser only (`IMPORT_SAVE_KEY`,
  `warujie-deck-import`; no accounts). Every change goes through `setListText()`, which saves it,
  updates the box, every ☆ and the tray (`refreshWant()`), and prices it again on this page.
  Another tab's change arrives by the `storage` event. `wantData()` reads the text as cards (the
  same card's lines added up, by oracle id or English name; memoized per text) for the ☆
  buttons, the top bar's count and the tray.
- **☆ buttons.** Every search result has one over its picture (`wantTogHtml()`, called from
  `cardTileHtml()`; at the end of the row in the text view, `textRowHtml()`), and the card page
  has the same ☆ in a row of its own under the picture and language buttons (`#cpWant` inside
  `.cp-art`, `wantCardHtml()`; as wide as the picture and as tall as the language buttons, 28px
  or 26px on phones, `--want-h`; the owner's choices, 2026-10-16/17). A tap adds the line
  `1 Card Name (SET) 123` (English name, and the printing when the card knows its number,
  `wantLineFor()`) after the last main-deck line (`withLineAdded()`, so it never lands in a
  sideboard); pressed again it takes all the card's lines out, with undo. Each button carries the
  card it acts on (`wantEntryOf()`, `data-wc`), so it works on any page, and one click listener on
  `document` in the capture phase handles every want button first (`.want-tog`,
  `[data-want-act]`), so a ☆ inside a result's link doesn't open the card. Another printing's
  page shows the ☆ pressed too (the list is per card).
- **Counts.** ＋ adds to the card's first line, − takes from its last (`wantSetCount()`,
  rewriting the count the way the line wrote it, `lineWithCount()`: `4 稲妻`, `4x`, `x4`,
  `SB: 2 …`). Undo (`wantUndoToast()`) puts the text back unless the list changed again since.
- **The note** at the bottom of the screen (`wantToast()`, `#wantToast`) confirms, with
  リストを見る (opens the tray) after adding and 元に戻す after taking a card out, clearing the
  list, or when a deck page or a shared link replaced the list (`imp.replaced`).
- A list kept the old way (`warujie-want`, staging only, 2026-10-16) moves into the text once
  (`WANT_OLD_KEY`).

### The tray

The top bar's ☆ button (`#wantBtn`, count of copies `#wantN`; the word ウォント only on screens
1400px and wider) opens `#wantTray` from the right over a dimmed page (`#wantTrayBg`; phones: the
whole width), `openTray()` / `closeTray()`; the ☆ again, ×, Esc or a click beside it closes it.
`drawTray()`: the title and how many cards; a リスト / 画像 switch (remembered as
`WANT_VIEW_KEY`, `warujie-want-view`; no pictures in lightweight mode); each card with − n ＋ and
a trash can (`wantStepHtml()`, `wantTrashHtml()`), as rows with a small picture, the name in the
site's language, the English name and the cheapest price (`trayRowHtml()`), or as pictures two a
row with the buttons under each (`trayTileHtml()`). Pictures come straight from Scryfall's image
server by the database's printing (`trayPic()`), or show the printing the line names (an art
picked on the price page, below) once that card is known (`trayCard()`; the tray asks for the
ones not known yet with `loadPrintCards()` when it opens). Lines not found link to the price page. At the
bottom: 全部消す (a second tap within 4 seconds, then undo), 価格を見る・書き出す (this page), and
晴れる屋で買う as below. A card's name opens its page (on phones the tray closes first).

### Reading and pricing

- **Reading the list** (`parseDeckText()`): one card per line. Section headings as MTG Arena
  (English and Japanese client), Magic Online and deck sites write them (`IMPORT_PARTS`:
  Deck/デッキ, Sideboard/サイドボード, Commander/統率者, Companion/相棒, About + `Name …` for the
  deck's name; maybeboard and tokens are skipped). Without headings, a blank line after cards
  starts the sideboard (Magic Online), unless the list has card-type headings
  (`IMPORT_TYPE_HEAD`, "Creatures (16)"), and `SB:` lines are sideboard too. Counts as `4`,
  `4x`, `x4` after the name, `4枚`, full-width digits, or none (one copy). The set and number
  (`(M10) 146`, also before a foil mark `*F*` or Archidekt's `[Removal]` / `^Tag^`; a number is
  anything without spaces, brackets or `*`, such as `1★`) are kept for the export with printings
  and the picture; `cleanImportName()` drops them from the name with foil marks and `[tags]`, and
  reads `Fire/Ice` as `Fire // Ice`. At most `IMPORT_MAX_LINES` lines.
- **Finding the cards** (`importRow()`): English name (`rowByEnglishName()`), Japanese name
  (also older names and front faces), or either without punctuation or in the other kana
  (`nameKey()`). Basic lands always count (`IMPORT_BASICS`), and a card too new for the database
  is found by its English name in the price file (`importCheapName()`). `readImport()` adds up
  the same card on several lines of one part (keeping which lines, for the buttons below) and
  doesn't count Arena's companion twice. Lines not found are
  listed with up to three guesses (`importGuesses()`: the name suggestions, else names a few
  letters away with `editDistance()`); picking one rewrites that line, keeping its count.
- **The price** is the deck pages' (`deckCost()`, `deckCostHtml()`, see "How a deck's price is
  worked out" above), with lines not found counted as missing (so the total reads 「〜」).
  Arena wildcards show when every card is on Arena. Each card shows the price of one copy, as
  on the deck pages; then the mana curve (`deckCurveHtml()`). The untitled list is called
  ウォントリスト (`imp.untitled`).
- **The bar** (`.want-bar`, owner's request 2026-10-16): the price and リスト / 画像 on the left,
  晴れる屋で買う and 書き出す on the right, staying under the top bar while the list scrolls
  (`position: sticky` at `--stick-top`). On phones the price box's note goes under the price.
- **晴れる屋で買う** (`.imp-buy`, also in the tray): a plain link to Hareruya's "buy from a card
  list" page (`HARERUYA_BULK`; Hareruya allows links only, CLAUDE.md rule 3). The same tap copies
  the whole list as "4 Card Name" lines in English names, sideboard included, the same card
  added up (`hareruyaText()`, copied at once inside the tap by `copyTextNow()` so the link still
  opens), and a line (`importNote()`) says to paste it there.
- **Export** (`importListText()`): Arena or MTGO text, text with printings (`print`:
  `4 Card Name (MH3) 123` where the line has them, which Moxfield and Archidekt read as that
  printing), the .txt file, and a link that carries the list (`importShareUrl()`,
  `?view=import&list=`; opening such a link puts its list in place of the list, with undo, and
  makes the address plain again). Links to Moxfield and Archidekt (`WANT_SITES`: neither can be
  filled in from a link, so the tap copies the list with printings and opens their page, and a
  line says to paste it into Import).
- The list is priced as people type (`priceImport()`, 350 ms after the last key), first from the
  database, then with prices, then with pictures (`importState`, cached per language and name),
  then with the pictures of the printings the lines name (below). There is no "price it" button
  (the owner found it pointless, 2026-10-16). 消す clears the list, with undo.

### Counts and art under each card

In the picture view (画像) each card has − n ＋ and an art button under it (`impCardHtml()`,
passed to `deckGroupsHtml()`; owner's request 2026-10-17). The list view stays as it was.

- **− n ＋** change that card's lines in that part only (main, sideboard or commander), the way
  they were written (`impEntry()` reads the box again, then `wantSetCount()`); − on the last copy
  takes the card out, with undo. The page is drawn again and the button keeps the focus
  (`impActSel()`).
- **The art button** opens `#artPicker` over a dimmed page (`#artPickerBg`; on phones a sheet from
  the bottom, three across): every paper printing of the card, newest first, as the card page
  lists them (`printEntries()`: the default search and the Japanese one, shared and kept for the
  visit, here in the request queue, `scryfallTurn()`; digital-only printings left out). Each shows its picture (the Japanese printing in
  Japanese, the English picture when the Japanese one has no real scan), set, number, rarity,
  treatments, 日本語版 and the English printing's price; the one shown now is marked 選択中.
  `openArtPicker()`, `drawArtPicker()`, `closeArtPicker()` (×, Esc, a click beside it, Back).
- **Picking** (`pickArt()`) writes the printing on the card's lines in that part
  (`lineWithPrint()`: `4 稲妻` → `4 稲妻 (M10) 146`; a foil mark, Archidekt's categories and a
  count written last stay put), with undo. So the export with printings and the Moxfield and
  Archidekt copies carry it. The prices don't change: each card and the total stay the cheapest
  printing's, and the picker says so (`pick.note`).
- **Pictures of the printings the lines name** (also lines pasted from Moxfield or Arena with
  `(SET) 123`, and ☆ lines): `PRINT_CARDS` (language, set and number → the Scryfall card) holds
  the ones picked and the pictures already fetched (`rememberPrint()`); `loadPrintCards()` asks
  for the rest, in Japanese one search for their Japanese printings 25 at a time, then
  `/cards/collection` by set and number for the English ones (75 at a time) where there is no
  Japanese printing or it has no real scan. A printing Scryfall doesn't know (an Arena-only set
  code) keeps the card's usual picture. Not in lightweight mode (no pictures there).

## Export (MTG Arena / Magic Online)

`deckExportText(list, kind)` writes the shown list in Arena format (`Deck` / `Sideboard`
headings) or MTGO format (main deck, blank line, sideboard). The menu opens right-aligned under
its button; `fitExportMenu()` moves it over where that would run off the screen (phones). `exportName()` shortens two-part
names to the front face, except split cards and Rooms, which keep `A // B`. It can be copied
(`copyText()`) or saved as a file (`saveTextFile()`).

## Price movers

Reads `movers.json` from warujie-prices (`loadMovers()`): the biggest risers and fallers over
1, 7 and 30 days, US dollars or euros, with yen. Which cards qualify (at least $2, moved at
least $0.50) is decided in warujie-prices `build_prices.py` (`MIN_PRICE_CENTS`,
`MIN_CHANGE_CENTS`).

## The installable app

- `manifest.webmanifest`: name, colours, icons (`icons/*-v2.png`). When icons change, give
  them a new file name (`-v3`) so phones pick them up, and update the manifest and `<head>`.
- `sw.js`: the offline copy; see [hosting.md](hosting.md#swjs-the-offline-copy).
- The install button in the footer (`#appInstall`) shows when the browser offers installing,
  and on iPhone/iPad with instructions for "Add to Home Screen".

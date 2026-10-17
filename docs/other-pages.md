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
| `?view=import[&list=<a deck list>]` | Deck price page: the pasted deck | `renderImport()`, `priceImport()`, `drawImport()` |
| `?view=want` | The same page showing the want list (the ☆ cards) | `renderImport()`, `drawImportHead()` |

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
| Random cards below | `loadRandomCards()` (`RANDOM_COUNT`), from the local database, or Scryfall's `/cards/random` without it |

## Sets

The set list comes from Scryfall's `/sets` (paper sets with cards, newest first), grouped by
type (`SET_GROUPS`) and filterable. Japanese set names are in `SET_NAME_JA`, a hand-made list:
add new sets there when they come out. One set's cards come from a Scryfall search
(`setSearchUrl()`), Japanese printings when `lang=ja`; the 日本語版 / 英語版 choice in the set's header is
the same square switch as the top bar's JP | EN (`.tog`).

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
  two-letter codes (`FORMAT_SHORT`: St, Pi, Mo, Lg, Vt, Pa, the owner's choice of 2026-10-17; Cm for Commander on the search tiles' circles, `FORMAT_BADGES`), the
  periods 30日/30d, the ⓘ button no words, and the win-rate column says 勝率/Win%; each button
  keeps its full name as a tooltip (`.sh-full` / `.sh-short` spans).
- **Rank arrows.** In the default share order, each rank has ▲ or ▼ beside it when the deck's
  average weekly share over the last 4 weeks rose or fell by `META_RANK_SHARE` (2) points or more
  against the 4 weeks before (`rankMoveHtml()`, `metaRankMoves()`, from `trends`: the same weeks
  as the ▲▼pt numbers). Under 2 points is shown as a grey — (no real change), whatever the rank
  did; the tooltip also says how the rank moved. A deck absent from the earlier 4 weeks gets ▲.
- **Deck price.** A 価格 column left of the share shows about how much the sample list costs in
  yen (`metaCostsFor()`, cached in `metaCosts`; a + when some cards have no price), and the sort menu has 安い順 (cheapest first;
  decks without a price go last). In Standard and Pioneer (`WC_FORMATS`), the Arena wildcards the
  list needs appear too (`wildcardsHtml()`), unless a card in it isn't on Arena.

### How a deck's price is worked out

`deckCost()` adds up, for every card in the main deck and sideboard, the cheapest paper
printing's price (`cheap.json.gz` from warujie-prices, `loadCheapest()`, matched by
`cheapRow()`): the lower of USD × the dollar rate and EUR × the euro rate (`cardYen()`).
Basic lands count as free (`isBasicLand()`). Totals are rounded (`yenRound()`) and shown as
「約¥…」 (or 「約$…」 with $ chosen in the top bar); when some cards have no price, `costText()` says 「〜」 and the deck page says how many
are missing. Wildcards count each card at its lowest Arena rarity (`RARITY_LETTER`, falling back
to the database's rarity when the price file has none).

## Deck pages

`renderDeck()` reads `meta_decks.json` (one real list per deck: its best finish in the period,
with how often each card is played across all lists) and `meta_lists/<days>-<format>.json`
(more sample lists, loaded only when asked for). Cards are grouped by type (`DECK_GROUPS`);
image or list view is saved in `akuchie-deck-view`. The trend chart is `deckTrendHtml()`.
Under the title, `deckCostHtml()` draws two one-line boxes of the same height, side by side
(on phones the wildcard box is labelled just "Arena"): 価格 and the deck's price in yen
(how it is worked out is a tooltip and the note at the foot of the page) and the Arena wildcards (Standard and Pioneer only; the rarity names are tooltips). The sample-list picker sits in a
bar that stays under the top bar while the page scrolls (`.deck-pick-bar`). After the main deck
and sideboard, `deckCurveHtml()` draws the mana curve of the main deck's non-land cards (0 to
6+). Each card also shows its own cheapest price (`.dc-yen` in image view, `.dl-yen` in list
view).

## Want list and deck price page (two lists, one page)

`#importView` shows one of two lists, priced in yen and taken elsewhere the same way: the want
list that the ☆ buttons fill (`?view=want`, titled ウォントリスト) and a pasted deck list
(`?view=import`, titled デッキの価格を調べる, as it was before the want list). A switch at the top
(`#impWhich`, ☆ ウォントリスト / デッキの価格, drawn by `drawImportHead()` with the title, lead and
label for the list shown) goes between them. The owner asked for the want list's page and the
deck price page to become one, in the deck price page's style, with the top bar's ☆ opening a
tray of the list (MTGGoldfish's card tray was the example), and then chose to keep the two lists
apart (2026-10-17): a ☆ never touches a pasted deck, and a deck page's list never replaces the
want list. The page belongs to the price tab (the tab bar marks 価格 while it is open). Ways in:
the tray's 価格を見る・書き出す (`?view=want`), the デッキの価格を調べる button right of the price tab's bar
(`.imp-open`, `a[data-import]`; bigger than the bar's toggles at the owner's request, the same height
as the bar, the dates and count `#moverSummary` under both; `.mv-top` holds both on wide screens and
under 761px steps aside with `display: contents`, so the button sits between the bar and the lists), and 編集して計算 on a deck page (`.deck-edit`), which opens the
shown list as the pasted deck (with the deck's name) so cards can be swapped and the price
follows.

### The lists

- **They are text**, kept in the browser only (no accounts): `lists.want` (`WANT_SAVE_KEY`,
  `warujie-want-list`) and `lists.deck` (`IMPORT_SAVE_KEY`, `warujie-deck-import`, the deck price
  page's key since before the want list, so a deck pasted on the live site stays where it was).
  `importState.which` says which one the page shows, and the box holds that one (`pageList()`).
  Every change goes through `setList(which, text)`, which saves it, updates the box when it shows
  that list, every ☆ and the tray for the want list (`refreshWant()`), and prices it again when it
  is on screen. Another tab's change arrives by the `storage` event. `wantData()` reads the want
  list as cards (the same card's lines added up, by oracle id or English name; memoized per text)
  for the ☆ buttons, the top bar's count and the tray.
- **☆ buttons.** Every search result has one over its picture (`wantTogHtml()`, called from
  `cardTileHtml()`; at the end of the row in the text view, `textRowHtml()`), and the card page
  has the same ☆ in a row of its own between the picture and the language buttons (`#cpWant`
  inside `.cp-art`, before `#printSlot`, `wantCardHtml()`; as wide as the picture and as tall as
  a language button, 28px or 26px on phones, `--want-h`; the owner's choices, 2026-10-16/17). A tap adds the line
  `1 Card Name (SET) 123` (English name, and the printing when the card knows its number,
  `wantLineFor()`) after the last main-deck line (`withLineAdded()`, so it never lands in a
  sideboard); pressed again it takes all the card's lines out, with undo. Each button carries the
  card it acts on (`wantEntryOf()`, `data-wc`), so it works on any page, and one click listener on
  `document` in the capture phase handles every want button first (`.want-tog`,
  `[data-want-act]`), so a ☆ inside a result's link doesn't open the card. Another printing's
  page shows the ☆ pressed too (the list is per card).
- **The green ＋ in the name suggestions** (owner's request 2026-10-17, `.sug-add` beside each
  card name under the search boxes, `attachNameSuggest()`): adds one copy without opening the card
  (`suggestAdd()`). On the deck price page it goes into the list on screen (`suggestAddList()`: the
  want list, or the pasted deck's main deck, `1 Card Name`), anywhere else into the want list (a
  card already there gets one more copy, `listSetCount()`). The line names no printing (the
  database has no collector numbers), so it is priced at the cheapest. The menu stays open
  (`mousedown` is cancelled, so the box keeps the focus) for the next card; each ＋ shows the copies
  its list has as a badge (`data-n`, its label and title too, `suggestAddLabel()`), and the note
  says so (リストを見る elsewhere, 元に戻す on the price page). Role and recent-search lines have none.
  The top bar's menu is at least 340px wide (`#searchSuggest`), so under its narrow box the name, the
  English name and the ＋ still fit; the ＋ keeps room on its right for its badge.
- **Counts.** ＋ adds to the card's first line, − takes from its last (`listSetCount()`,
  rewriting the count the way the line wrote it, `lineWithCount()`: `4 稲妻`, `4x`, `x4`,
  `SB: 2 …`). Undo (`wantUndoToast()`) puts the list's text back unless it changed again since.
- **The note** at the bottom of the screen (`wantToast()`, `#wantToast`) confirms, with
  リストを見る (opens the tray) after adding (a ☆, or a ＋ in the name suggestions) and 元に戻す after taking a card out, clearing the
  list, or when a deck page or a shared link replaced the pasted deck (`imp.replaced`).
- A list kept the old way (`warujie-want`, staging only, 2026-10-16) moves into the want list
  once (`WANT_OLD_KEY`). The ☆ cards saved on the test site between 2026-10-17's merge of the
  two pages and their separation went into the deck's key, so they show under デッキの価格 there.

### The tray

The top bar's ☆ button (`#wantBtn`, count of copies `#wantN`; the ☆ alone, its name in the tooltip,
so the search box keeps its width beside the JP | EN and ¥ | $ switches) opens `#wantTray` from the right over a dimmed page (`#wantTrayBg`; phones: the
whole width), `openTray()` / `closeTray()`; the ☆ again, ×, Esc or a click beside it closes it.
`drawTray()`: the title (the want list's name when it has one, `wantData().title`) and how many cards; a リスト / 画像 switch (remembered as
`WANT_VIEW_KEY`, `warujie-want-view`; no pictures in lightweight mode); each card with − n ＋ and
a trash can (`wantStepHtml()`, `wantTrashHtml()`), as rows with a small picture, the name in the
site's language, the English name and the price (`trayRowHtml()`: the printing the line names, as
on the price page below, else 最安 and the cheapest), or as pictures two a
row with the buttons under each (`trayTileHtml()`). Pictures come straight from Scryfall's image
server by the database's printing (`trayPic()`), or show the printing the line names (an art
picked on the price page, below) once that card is known (`trayCard()`; the tray asks for the
ones not known yet with `loadPrintCards()` when it opens, then their prices with
`loadPrintPrices()`, also after a ☆ while it is open, `refreshWant()`). Lines not found link to the price page. At the
bottom: 全部消す (a second tap within 4 seconds, then undo), 価格を見る・書き出す (`?view=want`), and
晴れる屋で買う as below. A card's name opens its page (on phones the tray closes first).

### Reading and pricing

- **Reading the list** (`parseDeckText()`): one card per line. Section headings as MTG Arena
  (English and Japanese client), Magic Online and deck sites write them (`IMPORT_PARTS`:
  Deck/デッキ, Sideboard/サイドボード, Commander/統率者, Companion/相棒, About + `Name …` for the
  deck's name, which ends at a blank line; maybeboard and tokens are skipped). Without headings
  (About doesn't count as one), a blank line after cards starts the sideboard (Magic Online),
  unless the list has card-type headings
  (`IMPORT_TYPE_HEAD`, "Creatures (16)"), and `SB:` lines are sideboard too. Counts as `4`,
  `4x`, `x4` after the name, `4枚`, full-width digits, or none (one copy). The set and number
  (`(M10) 146`, also before a foil mark `*F*` or Archidekt's `[Removal]` / `^Tag^`; a number is
  anything without spaces, brackets or `*`, such as `1★`) are kept for the export with printings,
  the picture and the price, and so is Moxfield's finish mark (`f`: `*F*` foil, `*E*` etched);
  `cleanImportName()` drops them from the name with foil marks and `[tags]`, and
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
  worked out" above), with lines not found counted as missing (so the total reads 「〜」), except
  that **a line naming a printing counts at that printing's price** (owner's request 2026-10-17,
  "the price doesn't update when you change the printing"): an art picked below, a ☆ line (it
  names the printing the ☆ was on) or a pasted Moxfield or Arena line with `(SET) 123`.
  `entryYen()` prices each of a card's lines: `printYen()` from `PRINT_PRICES` (set and number →
  that printing's Scryfall prices; a Japanese printing has none, so its English printing's, as on
  the card page), the lower of USD and EUR in yen as `cardYen()` does (`pricesYen()`; a `*F*` line
  at the foil price, `*E*` etched, a printing made only in foil at that), else the card's cheapest
  printing. `drawImport()` passes those to `deckCost()` as its second list, one per card (deck pages
  pass none, so they keep the cheapest; not as a third item of each card, where the metagame's
  lists keep the play rate), and the card's price title says この版の価格 (`imp.yen.print`); the
  total's title and the note at the foot say which lines count how (`imp.cost.sub`,
  `imp.cost.note`). The prices come with the English printings `loadPrintCards()` fetches (now
  for every printing, not only those without a Japanese scan), from the cards fetched for the
  pictures (`rememberPrint()` → `notePrintPrices()`), from the art picker, and for the rest
  (also in lightweight mode) from `loadPrintPrices()`: `/cards/collection` by set and number, 75
  at a time, each asked once (`PRINT_PRICES_ASKED` while in flight; a printing Scryfall has no
  English price for keeps the cheapest). Arena wildcards show when every card is on Arena. Each
  card shows the price of one copy, as on the deck pages; then the mana curve
  (`deckCurveHtml()`). An empty want list (or one with
  only its name left) says how to fill it with ☆ (`tray.empty`); an empty deck shows the formats
  it reads and an example.
- **The name** (owner's request 2026-10-17) is a text box with a pen in place of the title
  (`#impName`, `.imp-name`), showing ウォントリスト or 貼り付けたデッキ (`want.title`,
  `imp.untitled`) until it has one. Typing writes it at the top of the list as MTG Arena does,
  `About` / `Name …` and a blank line (`textWithName()`, at most `IMPORT_NAME_MAX` letters);
  emptying it takes those lines out. So the name is kept with the list, read back by
  `parseDeckText()`, used for the .txt file and carried by the share link. The text changes at
  once (`importNameTyped()`), but not while Japanese is being converted (an `input` event with
  `isComposing`; the word goes in at `compositionend`); the page is priced again a moment later
  so line numbers follow, and `drawImport()` leaves the box itself alone while it has the focus
  (only what is around it is drawn again), so the keyboard and the conversion are never cut off.
  Enter finishes. A ☆ on a list that has only a name puts the card under it (`withLineAdded()`).
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
  `?view=import&list=`, from either list; opening such a link puts its list in place of the
  pasted deck, with undo, and makes the address plain again). Links to Moxfield and Archidekt (`WANT_SITES`: neither can be
  filled in from a link, so the tap copies the list with printings and opens their page, and a
  line says to paste it into Import).
- The list is priced as people type (`priceImport()`, 350 ms after the last key), first from the
  database, then with prices, then with pictures (`importState`, cached per language and name),
  then with the pictures of the printings the lines name (below), then with those printings'
  prices (`loadPrintPrices()`). There is no "price it" button
  (the owner found it pointless, 2026-10-16). 消す clears the list shown, with undo.

### Counts and art under each card

In the picture view (画像) each card has − n ＋ and an art button under it (`impCardHtml()`,
passed to `deckGroupsHtml()`; owner's request 2026-10-17), and in the list view (リスト) each row
has the same − n ＋ in place of the count and the art button at its end (`impRowHtml()`:
`deckRowHtml()` with `impStepHtml()` and `impArtHtml()` as its lead and tail; owner's request,
the same day, "make the UI consistent with the image view").

- **Order:** by card type, then mana value, then name (`deckSort()` with `byCount` false), so a
  count changed with − / ＋ never moves a card past another; deck pages put most copies first.
- **− n ＋** change that card's lines in that part only (main, sideboard or commander), the way
  they were written (`impEntry()` reads the list again, then `listSetCount()`); − on the last copy
  takes the card out, with undo. The page is drawn again and the button keeps the focus
  (`impActSel()`).
- **The art button** opens `#artPicker` over a dimmed page (`#artPickerBg`; on phones a sheet from
  the bottom, three across): every paper printing of the card, newest first, as the card page
  lists them (`printEntries()`: the default search and the Japanese one, shared and kept for the
  visit, here in the request queue, `scryfallTurn()`; digital-only printings left out). Each shows its picture (the Japanese printing in
  Japanese, the English picture when the Japanese one has no real scan), set, number, rarity,
  treatments, 日本語版 and the price it would count at in the list (`pricesYen()` of the English
  printing's prices, foil when the card's first line is; dollars until the exchange rate is in);
  the one shown now is marked 選択中.
  `openArtPicker()`, `drawArtPicker()`, `closeArtPicker()` (×, Esc, a click beside it, Back).
- **Picking** (`pickArt()`) writes the printing on the card's lines in that part
  (`lineWithPrint()`: `4 稲妻` → `4 稲妻 (M10) 146`; a foil mark, Archidekt's categories and a
  count written last stay put), with undo. So the export with printings and the Moxfield and
  Archidekt copies carry it, and the card and the total are priced at it at once: the picked
  printing's prices go into `PRINT_PRICES` (`pick.note` says so).
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
`MIN_CHANGE_CENTS`). The market tabs here and in the home page's box follow the card page's
order (`PRICE_MARKETS`: 日本, 米国, 欧州), with 米国 chosen at first.

## The installable app

- `manifest.webmanifest`: name, colours, icons (`icons/*-v4.png`). The icon is the owner's
  own artwork, `tools/icon_source.png` (2026-10-17: a brush-drawn 悪 in a rough glowing ring;
  `favicon.ico` is its small version). `tools/make_icons.py` cuts it to a square and scales it
  to each size, unchanged (a first version redrew it with a font, which the owner didn't want).
  The script makes a green set for warujie.jp and a pink copy (`icons/*-v4-test.png`, named by
  `manifest-test.webmanifest`) that `worker.js` shows on the test sites (see
  [hosting.md](hosting.md#workerjs), job 4).
  When icons change, raise `VERSION` in the script so phones pick up the new files, and update
  both manifests, the `<head>`, `sw.js` and the checks in `dev/tests/worker_icons.mjs`.
- `sw.js`: the offline copy; see [hosting.md](hosting.md#swjs-the-offline-copy).
- The install button in the footer (`#appInstall`) shows when the browser offers installing,
  and on iPhone/iPad with instructions for "Add to Home Screen".

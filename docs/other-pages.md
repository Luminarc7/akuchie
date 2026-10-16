# Home, sets, metagame, decks, deck price page, price movers, export, app

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
| `?view=import[&list=<a deck list>]` | Deck price page (paste a list) | `renderImport()`, `priceImport()`, `drawImport()` |

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
| Rakuten Books box (Secret Lair / ブースターBOX tabs) | `renderHomeShop()`, `#homeShop` (from `worker.js` `/shop/rakuten`; see [Shops](#shops-rakuten-books-and-amazon)) |
| Random cards below | `loadRandomCards()` (`RANDOM_COUNT`), from the local database, or Scryfall's `/cards/random` without it |

## Sets

The set list comes from Scryfall's `/sets` (paper sets with cards, newest first), grouped by
type (`SET_GROUPS`) and filterable. Japanese set names are in `SET_NAME_JA`, a hand-made list:
add new sets there when they come out (the Rakuten box search on set pages uses it too). One set's cards come from a Scryfall search
(`setSearchUrl()`), Japanese printings when `lang=ja`.

### Shops: Rakuten Books and Amazon

Things to buy, with affiliate links once the owner has the IDs ("shops" section of
`index.html`).

- **Where:** the home page's Rakuten Books box (`renderHomeShop()`: four Secret Lair products or
  booster boxes, newest first, with price, 予約受付中 / 在庫あり, release date, NEW for the last
  two weeks), and a "このセットのBOXを買う" strip on set pages (`renderSetShop()`, `#setShop`)
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
`creditDeckArt()`).

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

## Deck price page (paste a list)

`?view=import` (`#importView`): people paste a deck list and see what it costs. It belongs to the
price tab (the tab bar marks 価格 while it is open; the owner moved it there from the metagame tab,
2026-10-16). Ways in: the デッキの価格を調べる button, its own button right of the price tab's bar (which is shortened for it) on wide screens
  (`.mv-top` holds both and keeps them under the top bar; under 761px it steps aside with
  `display: contents`, so the bar sticks alone and the button sits between it and the lists),
  bigger than the bar's toggles at the owner's request (`.imp-open`,
`a[data-import]`), and 編集して計算 on a deck page (`.deck-edit`), which opens the shown list there
(with the deck's name) so cards can be swapped and the price follows.

- **Reading the list** (`parseDeckText()`): one card per line. Section headings as MTG Arena
  (English and Japanese client), Magic Online and deck sites write them (`IMPORT_PARTS`:
  Deck/デッキ, Sideboard/サイドボード, Commander/統率者, Companion/相棒, About + `Name …` for the
  deck's name; maybeboard and tokens are skipped). Without headings, a blank line after cards
  starts the sideboard (Magic Online), unless the list has card-type headings
  (`IMPORT_TYPE_HEAD`, "Creatures (16)"), and `SB:` lines are sideboard too. Counts as `4`,
  `4x`, `x4` after the name, `4枚`, full-width digits, or none (one copy). `cleanImportName()`
  drops the set and number (`(M10) 146`), foil marks, `[tags]`, and reads `Fire/Ice` as
  `Fire // Ice`. At most `IMPORT_MAX_LINES` lines.
- **Finding the cards** (`importRow()`): English name (`rowByEnglishName()`), Japanese name
  (also older names and front faces), or either without punctuation or in the other kana
  (`nameKey()`). Basic lands always count (`IMPORT_BASICS`), and a card too new for the database
  is found by its English name in the price file (`importCheapName()`). `readImport()` adds up
  the same card on several lines and doesn't count Arena's companion twice. Lines not found are
  listed with up to three guesses (`importGuesses()`: the name suggestions, else names a few
  letters away with `editDistance()`); picking one rewrites that line, keeping its count.
- **The price** is the deck pages' (`deckCost()`, `deckCostHtml()`, see "How a deck's price is
  worked out" above), with lines not found counted as missing (so the total reads 「〜」).
  Arena wildcards show when every card is on Arena. Each card shows the price of one copy, as
  on the deck pages; then the mana curve (`deckCurveHtml()`). (A breakdown naming each card's
  cheapest printing was tried and left out at the owner's request, 2026-10-16.)
- **晴れる屋で買う** (`.imp-buy`): a plain link to Hareruya's "buy from a card list" page
  (`HARERUYA_BULK`; Hareruya allows links only, CLAUDE.md rule 3). The same tap copies the whole
  deck as "4 Card Name" lines in English names, sideboard included, the same card added up
  (`hareruyaText()`, copied at once inside the tap by `copyTextNow()` so the link still opens),
  and a line says to paste it there.
- **Export** (`importListText()`): Arena or MTGO text and the .txt file in English names, and a
  link that carries the list (`importShareUrl()`, `?view=import&list=`); opening such a link
  puts the list in the box and makes the address plain again.
- The box is priced as people type (`priceImport()`, 350 ms after the last key), first from the
  database, then with prices, then with pictures (`importState`, cached per language and name).
  There is no "price it" button (the owner found it pointless, 2026-10-16). The text is kept in
  the browser only (`IMPORT_SAVE_KEY`); 消す clears it.

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

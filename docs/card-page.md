# The card page

URL: `?card=<Scryfall printing id>`, optionally `&print=<lang>`. Drawn by
`renderCardViewContent(card)` into `#cardViewCard`; `shownCard` holds the card on screen.
Everything that loads later (printings, prices, history, combos, similar cards) checks
`shownCard === card` before drawing, so a slow answer never lands on the wrong card.

## How the card is found

- From search results or a set page the card object is already there (`currentCards`,
  `setView.cards`) and the page draws at once.
- Opened directly, `applyRoute()` fetches it from Scryfall (`fetchSingleCard()`) and waits for
  the card database too, because Japanese names for English printings come from the database
  (`dbRowFor()`, `displayNameJa()`).

## Layout, top to bottom

| Part | Function(s) | Data from |
|---|---|---|
| Picture | `cardArtHtml()`, `pictureTag()` | Scryfall images. Placeholder Japanese scans are swapped for the same printing's English picture with a note |
| Language buttons (JP EN CS…) under the picture | `fillPrintToggle()`, `printingLanguages()`, `printButtonsHtml()`, `openPrinting()` | The printings file (`printings.json.gz`, `loadPrintingsFile()`); for a printing it doesn't have yet, one Scryfall search: `e:<set> cn:"<number>" include_multilingual=true` (plus `SET_TWIN`) |
| Name, cost, type line, text | `cardPageNames()`, `cardPageType()`, `cardPageText()` | Scryfall card, Japanese from the database where Scryfall lacks it |
| Roles row | `showCardRoles()` | Tag file |
| Set, number, Scryfall link | inline in `renderCardViewContent()` | |
| Prices (JP / US / EU tabs) | `priceHtml()`, `marketRows()`, `rerenderPriceSection()` | Scryfall prices, warujie-prices `q/` shards |
| Shop links | `shopGroups` in `renderCardViewContent()`; `…Url()` helpers; `jpShopDirHtml()` | Links only |
| Listings and stock | `offersHtml()`, `offerRows()` | warujie-prices `q/` shards (`l`, `lk`) |
| Legality | `legalityHtml()` | Scryfall `legalities` |
| Deck sites | `mtgDecksUrl()`, `goldfishUrl()` | Links only |
| Price history chart | `showPriceHistory()`, `drawPriceHistory()` | warujie-prices `h/` shards |
| All printings | `loadPrintings()`, `printEntries()` (shared with the deck price page's art picker, kept for the visit) | Scryfall search `oracleid:<id> unique:prints`, and the same with `lang:ja` (`fetchAllPages()`) |
| Combos (preview page only) | `loadCardCombos()` | warujie-prices `c/` shards, `combo_ja.js` for Japanese |
| Similar cards | `showSimilar()`, `renderSimilar()` | The local similarity index (see [search.md](search.md#similar-cards-似)) |
| Price notes | `priceNotesHtml()` | Which source each number came from and its date |

## Printings and languages (decided; don't change without asking)

- One language button per language the **exact printing** (same set and collector number)
  exists in. There is never a jump to another set's printing. A printing that exists only in
  English shows EN alone.
- Some old sets file non-English printings under another set code with the same numbers:
  `4bb`↔`4ed`, `bchr`↔`chr`, `fbb`↔`3ed`. `SET_TWIN` pairs them. Add a pair there if you find
  another.
- `?print=<lang>` shows that printing in its own language (`printChoice()`); without it the
  site language decides which name is big.
- The languages come from the printings file (`printings.json.gz`, made with the card database;
  [data.md](data.md#the-printings-file-printingsjsongz)), loaded once per visit by
  `loadPrintingsFile()`, so opening a card page no longer asks Scryfall which languages exist.
  A language other than the one shown is then only its set and number (`_stub`); pressing its
  button fetches that one printing (`/cards/<set>/<number>/<lang>`, after `scryfallTurn()`) and
  opens it (`openPrinting()`; the button dims while it loads).
- A printing the file doesn't have yet (a set newer than the last rebuild), or a page without the
  file, asks Scryfall as before; those results are cached per printing in `PRINTINGS`.
- Two-part cards read in their own language on both halves (呪文嘲りの集会 // お返し).

## Prices

**Prices for a non-English printing come from the English printing with the same set and
number.** `priceHistoryId()` finds that English twin (`/cards/<set>/<number>/en`) and remembers
it as `card._enId`. Japanese copies rarely have a price of their own on US/EU markets.

The three tabs (`PRICE_MARKETS`, choice saved in `akuchie-market`):

| Tab | Shows |
|---|---|
| JP | "準備中" (in preparation) and the Japanese shop links (`jpShopDirHtml()`). Japanese shop prices appear only for shops that granted permission. The "B+D" layout is a decided design. |
| US | TCGplayer lowest listing, Mana Pool, Card Kingdom (sell), Cardsphere, other USD shops from MTGJSON; TCGplayer market price only when nothing else is known; Card Kingdom's buy price last |
| EU | Cardmarket lowest offer, other EUR shops; Cardmarket trend only when nothing else is known |

The cheapest selling price in each column (non-foil, foil) is marked "best". Every amount shows
yen too (`yenFor()`, `yenForEur()`), using Frankfurter's rate.

`loadCardQuotes()` reads `q/<first two characters of the id>.json.gz` and fills `card._quotes`
(today's shop prices), `card._offers` (listings), `card._links` (shop product links). The file
formats are in [data.md](data.md#warujie-prices-files-the-site-reads).

**Listings** (`offersHtml()`): per-shop offers by condition with stock, cheapest first, from
Card Kingdom, Mana Pool, TCGplayer, Cardmarket and CardTrader (`OFFER_SHOPS`). The foil switch is
saved in `akuchie-offer-foil`; foil-only printings switch to foil automatically unless the
visitor changed it by hand (`offerFoilTouched`).

**Japanese shop stock** (`jpOffersHtml()`): on the JP tab the price column shows the offers whose
market is `jp` in `OFFER_MARKET` (so far ENNDAL GAMES, `ed`, read once a night by
warujie-prices). Their price field is in **yen**, not cents, and English copies get an 英語 label.
The table shares `offerTableParts()` and the foil switch with the US/EU listings. A printing with
none shows the notice instead (`price.jp.none` once ENNDAL's stock is published, otherwise
`price.jp.notice`); the notes give the night it was read in Japan time (`jpNightLabel()`).

**Price history** keeps US dollars and euros, non-foil and foil, daily for 120 days and weekly
after that. The chart offers 1 month, 3 months (default), 1 year and all, plus a foil switch (`histState`).

## Shop links

Links are search URLs built from the card's English or Japanese name; nothing is read from the
shops. Japanese shops: `hareruyaUrl()`, `bigMagicUrl()`, `cardRushUrl()`, `tokyoMtgUrl()` and the
`JP_SHOP_SEARCH` list (each entry: Japanese label, English label, URL with `{q}`, optionally
`"name": "en"` to search by English name). On phones only `JP_DIR_PHONE` shops show before
"load more". Star City Games is a link only (no price feed exists).

Adding a shop's **prices** is a different matter: it needs the shop's permission first
(CLAUDE.md rule 3), then a builder in warujie-prices (as ENNDAL GAMES has), a code in
`OFFER_SHOPS` and `OFFER_MARKET`, and a link rule in `offerLink()`.

## Combos

Commander combos from Commander Spellbook show only where `<html data-combos="1">`, which is
`preview.html` (made by `tools/make_preview.py`). `COMBOS_ON` reads it. Turning combos on for
the main site means adding that attribute to `index.html` (a visible change: ask the owner).
Japanese wording for combo results is in `combo_ja.js`.

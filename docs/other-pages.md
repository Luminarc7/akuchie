# Home, sets, metagame, decks, price movers, export, app

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
(`setSearchUrl()`), Japanese printings when `lang=ja`.

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
  (`toggleMetaRow()`).
- **Deck price.** Each row shows about how much the sample list costs in yen
  (`metaCostsFor()`, cached in `metaCosts`), and the sort menu has 安い順 (cheapest first;
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
Under the title, `deckCostHtml()` draws three boxes: the deck's price in yen, the Arena
wildcards (Standard only) and the mana curve of the main deck's non-land cards (0 to 6+). Each
card also shows its own cheapest price (`.dc-yen` in image view, `.dl-yen` in list view).

## Export (MTG Arena / Magic Online)

`deckExportText(list, kind)` writes the shown list in Arena format (`Deck` / `Sideboard`
headings) or MTGO format (main deck, blank line, sideboard). `exportName()` shortens two-part
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

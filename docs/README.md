# warujie.jp developer guide

This folder explains how the site works, so that a developer who has never seen it can find
the code behind any part of the page and change or fix it safely. Start here.

- **The owner's rules and decisions** (staging first, publishing, which outside data may be
  used, privacy promises) are in [`../CLAUDE.md`](../CLAUDE.md). Read its "Rules" and
  "Decisions already made" sections before changing anything visible.
- **The price, combo and role-tag data** is built in a second repository,
  [warujie-prices](https://github.com/warujie/warujie-prices). Its own `docs/` folder explains
  it. [data.md](data.md) here describes the files the site reads from it.

## What the site is, in one paragraph

warujie.jp (悪知恵) is a free Japanese Magic: The Gathering card search. It is one static page,
[`index.html`](../index.html) (HTML, CSS and JavaScript in one file), served by Cloudflare
Workers. On load the page downloads the whole card database (`ja_cards.json.gz`, about 33,800
cards with Japanese and English names and text) and searches it **in the browser**. Pictures,
printings and today's prices come live from Scryfall's API; price history, shop listings,
combos and role tags come from files that warujie-prices publishes every day on GitHub Pages;
metagame data is rebuilt every day by a workflow in this repository. There is no server-side
code apart from a small Worker ([`worker.js`](../worker.js)) and no database server.

## Read in this order

| Doc | What it explains |
|---|---|
| [architecture.md](architecture.md) | The parts, where data comes from, branches and deploys, the outside services |
| [index-html.md](index-html.md) | A map of `index.html`: its sections, the main functions and the page state |
| [search.md](search.md) | How a search is read, matched and ordered; slang, roles, operators, spelling |
| [card-page.md](card-page.md) | The card page: printings and language buttons, prices, listings, history, combos, links |
| [other-pages.md](other-pages.md) | Home, sets, metagame and deck pages, the deck price page, price movers, export, the installable app |
| [interface.md](interface.md) | Interface text in two languages, themes, lightweight mode, saved settings, phones |
| [data.md](data.md) | Every data file: its fields, who builds it, when, and how to rebuild or fix it |
| [hosting.md](hosting.md) | `worker.js`, `sw.js`, Cloudflare, what is published, link previews, rolling back |
| [workflow.md](workflow.md) | Running it locally, tests, committing to staging, publishing, keeping these docs true |
| [troubleshooting.md](troubleshooting.md) | Symptoms, where to look, and the usual fix |

## I want to change… where is it?

Names in `code` are functions, constants or section markers in `index.html` unless another file
is given. Search for them; line numbers move too often to be worth writing down.

| I want to… | Look at |
|---|---|
| Change a piece of interface text | `STR` (Japanese and English side by side), and `data-i18n` attributes in the HTML. See [interface.md](interface.md) |
| Change colours or spacing | CSS variables at the top of `<style>` (`html[data-theme="dark"]`, `html[data-theme="light"]`) |
| Make a word players use find the right cards | `JA_SLANG`, `JA_KW_SLANG`, `EN_WORD_ALIAS`, `WORD_FILTERS`. See [search.md](search.md#players-words-slang) |
| Add or change a role word (除去, ドロー, ramp…) | `ROLE_LIST`; if it needs a new Scryfall Tagger tag, also `TAGS` in warujie-prices' `build_tags.py` |
| Change the order of search results | `searchRows()`, `relevance()`, `evaluateRow()`. See [search.md](search.md#ordering) |
| Add a search operator (`o:`, `t:`, `色:`…) | `JA_OPERATORS`, `KNOWN_OPS`, `localOperatorMatch()` |
| Fix a wrong Japanese card name | `tools/name_fixes_ja.json` (English name → Japanese). See [data.md](data.md#fixing-a-japanese-name) |
| Add a Japanese shop link to card pages | `JP_SHOP_SEARCH` (search links), `JP_MAIN_SHOPS`, and the `…Url()` helpers in "links to shops and deck sites" |
| Show a Japanese shop's prices | Only for shops that gave permission (CLAUDE.md rule 3). The JP tab is `jpShopDirHtml()`; the price builder is in warujie-prices |
| Change the example searches on the home page | `HERO_TRY`, `HERO_EFFECTS`, `HERO_SLANG` |
| Change the search tips | `GUIDE_ROWS`, `GUIDE_EXAMPLES` |
| Change which formats are shown | `FORMAT_ORDER`, `MAIN_FORMATS`, `FORMAT_JA`, `FORMAT_EN`; metagame: `META_FORMATS` and `build_meta.py` |
| Add Japanese set names | `SET_NAME_JA`; set groups: `SET_GROUPS` |
| Add a new page (`?view=…`) | `routeFromUrl()`, `applyRoute()`, `showView()`, a `<div id="…View">` in the HTML; link previews in `worker.js` `shareTags()` |
| Change what link previews (LINE, X…) show | `worker.js`, `shareTags()` |
| Change the footer | `<footer class="attribution">` in the HTML (keep the no-tracking promise true) |
| Change the app icon or name | `icons/`, `manifest.webmanifest`, `tools/make_icons.py` |
| Change price-mover thresholds | warujie-prices `build_prices.py`: `MIN_PRICE_CENTS`, `MIN_CHANGE_CENTS`, `WINDOWS` |
| Change the metagame numbers | `build_meta.py` (this repo); the tab itself is "metagame tab" in `index.html` |
| Change how a pasted deck list is read | `parseDeckText()`, `IMPORT_PARTS`, `cleanImportName()`, `importRow()`. See [other-pages.md](other-pages.md#reading-and-pricing) |
| Change the want list (☆, the tray), the switch to the pasted deck, or where they can be exported | `wantTogHtml()`, `setList()`, `drawImportHead()`, `drawTray()`, `importListText()`, `WANT_SITES`. See [other-pages.md](other-pages.md#want-list-and-deck-price-page-two-lists-one-page) |
| Change the − n ＋ and art buttons on the price page's cards and rows, or the art picker | `impCardHtml()`, `impRowHtml()`, `openArtPicker()`, `drawArtPicker()`, `lineWithPrint()`, `loadPrintCards()`. See [other-pages.md](other-pages.md#counts-and-art-under-each-card) |
| Change the price page's name box | `textWithName()`, `importNameTyped()`, `drawImport()`. See [other-pages.md](other-pages.md#reading-and-pricing) |
| Change the green ＋ in the name suggestions (what it adds, to which list) | `suggestAdd()`, `suggestAddList()`, `attachNameSuggest()`. See [other-pages.md](other-pages.md#want-list-and-deck-price-page-two-lists-one-page) |
| Change how a line naming a printing is priced (the art picked, ☆ lines, foil) | `entryYen()`, `pricesYen()`, `printYen()`, `PRINT_PRICES`, `loadPrintPrices()`, `deckCost()`. See [other-pages.md](other-pages.md#reading-and-pricing) |
| Translate a deck name into Japanese | `DECK_NAME_WHOLE` (whole names), `DECK_WORD_JA` (words), `DECK_GUILD_JA`, `DECK_MONO_JA` |

## Which doc covers which code

When you change code, update the doc that covers it in the same commit (see
[workflow.md](workflow.md#keeping-these-docs-true)).

| Code | Doc |
|---|---|
| `index.html` search sections (database, tag file, role words, spelling, reading the search box, Japanese, highlighting, suggestions, recent searches, filters) | search.md, index-html.md |
| `index.html` card page sections (pictures, prices, treatments, listings, notes, shop links, printing language, price history, combos, similar cards) | card-page.md |
| `index.html` home, sets, metagame, price movers, deck pages, deck price page, want list, export, install | other-pages.md |
| `STR`, themes, language switch, lightweight mode, phone menu, `localStorage` keys | interface.md |
| any new or renamed `// ---- section ----` or top-level function that others call | index-html.md |
| `worker.js`, `sw.js`, `wrangler.jsonc`, `.assetsignore`, `manifest.webmanifest` | hosting.md |
| `ja_cards.json.gz` fields, `printings.json.gz`, `tools/*.py`, `build_meta.py`, workflows, the warujie-prices file formats | data.md |
| `dev/` tests, branches, publishing steps | workflow.md |
| a bug you fixed that could come back | troubleshooting.md |

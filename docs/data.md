# Data files and the jobs that make them

| File | What | Made by | When |
|---|---|---|---|
| `ja_cards.json.gz` | The card database | `tools/update_database.py` (the builder, the name fixes, the readings, the check) via `update-cards.yml` | Mondays 02:30 UTC, committed to `staging` when cards changed; by hand any time |
| `printings.json.gz` | Every printing's languages, rarity and treatments (card page language buttons) | the same builder, with the database | With the database |
| `ja_cards.json.br` | The same, brotli-compressed (not in git) | `tools/brotli_db.mjs` | At every Cloudflare deploy |
| `meta.json`, `meta_decks.json`, `meta_lists/*.json` | Metagame tab, deck pages, sample lists | `build_meta.py` via `update-meta.yml` | Daily 18:40 UTC, committed to `main` |
| `combo_ja.js` | Japanese wording for combo results | by hand | When combo wording needs fixing |
| `tools/name_fixes_ja.json` | Japanese names Scryfall has wrong or missing | by hand (read off real cards) | When a wrong name is found |
| warujie-prices files (`h/`, `q/`, `c/`, `t/`, `movers.json`, `cheap.json.gz`, `index.json`) | Prices, listings, combos, role tags | warujie-prices builders | Daily 12:17 UTC |
| `dev/tests/fixtures/*`, `dev/searchbench/*.json*` | Test data | by hand / scripts in `dev/` | When tests need it |

## The card database (`ja_cards.json.gz`)

Gzipped JSON: `{ "version": 2, "generated": "YYYY-MM-DD", "fields": [...], "cards": [[...], ...] }`.
Each card is an array in the order of `fields` (smaller than objects). One row per card (about
33,800), not per printing.

| Field | Meaning |
|---|---|
| `id` | The Scryfall printing shown in results: a Japanese printing with a real scan where possible, else an English one (another language only for cards never printed in English); when the builder's preferences are level, the ordinary frame over a showcase or borderless one (`picture_rank()`). When the chosen Japanese printing has no sharp scan, a Japanese one that has, at the same rarity in a regular set (`CardEntry.picture()`) |
| `oracle_id` | Scryfall's id for the card across printings |
| `name_en`, `name_ja` | Names; two-part cards as `A // B` |
| `type_en`, `type_ja` | Type lines; `type_ja` from another Japanese printing when the one with the text has an English type line (`ja_type` in `CardEntry`), empty when no Japanese printing has a Japanese one |
| `oracle_en`, `oracle_ja` | Rules text (Japanese from the newest Japanese printing whose text has Japanese in it: since 2.5 an English text on a Japanese printing, as Scryfall has for most of Edge of Eternities, doesn't count) |
| `mana_cost`, `cmc` | `{2}{W}{B}`, mana value |
| `colors` | Letters, e.g. `GR`; empty for colourless |
| `power`, `toughness` | Strings or `null` |
| `rarity`, `set` | Of the printing in `id` (the rarity the tile shows) |
| `rarities` | Every rarity the card was printed at, one letter each in the order `c u r m s b` (common, uncommon, rare, mythic, special, bonus), counted as Scryfall's `r:` counts: each English printing, plus a printing in another language where that set and number has no English one (Renaissance, Japanese-only promos, Phyrexian); promos and Secret Lair included, memorabilia and digital-only printings not (`CardEntry.all_rarities()`). The rarity filters use it (`hasRarity()`); a file without it falls back to `rarity` |
| `keywords` | Comma-separated |
| `released_at` | First release of the card |
| `alt_names_ja` | Older Japanese names, `|`-separated (they still match in search) |
| `legal` | One letter per format where legal: `s` standard, `p` pioneer, `m` modern, `l` legacy, `v` vintage, `a` pauper, `c` commander (`FORMAT_CODE` in `index.html`) |
| `layout` | The card's shape from Scryfall when it isn't an ordinary one-faced card: `split`, `transform`, `modal_dfc`, `meld`, `flip`, `adventure` (Omens too), `prepare`, `saga`, `class`, `case`, `leveler`, `mutate`, `prototype`, `host`, `augment` (`SHAPE_LAYOUTS` in the builder); empty otherwise. Searched by 分割カード, 両面カード… (`CARD_SHAPES`) |
| `sets` | Every set the card was printed in (any language, promos included, digital-only and memorabilia not), space-separated, oldest first: `lea 4bb m10 …`. `e:` / `セット:` search it, so `e:mh3` finds reprints too, as Scryfall does; a file without it falls back to `set` |
| `treatments` | One letter per treatment any printing has, in the order `b s x f o u t e n` (borderless, showcase, extended art, full art, old frame 1993/1997, future frame, textless, etched, serialized: `treatment_letters()`), then the same letters in upper case for those a Japanese printing has (bsoS: borderless, showcase and old-frame printings, the showcase one also in Japanese). ボーダーレス, 旧枠, `is:showcase`… search it (`TREATMENTS` in `index.html`); beside 日本語版 or `lang:ja`, the upper-case letter |
| `name_kana` | Reading of the Japanese name in hiragana: the あいうえお order, and names typed in hiragana (いなずま finds 稲妻); never shown. Made by `tools/name_readings.py`: printed furigana, else SudachiDict, else pykakasi for kanji Sudachi doesn't know, so no reading keeps a kanji |

When the page loads it, `indexRow()` adds computed fields starting with `_` (lowercased names,
type and text, colour string, keyword set…). It also empties a `type_ja` or `oracle_ja` with no
Japanese in it (files built before 2.5 have about 410), so the type line is translated and the
card is found through its English text. To add a database field: add it in
`build_ja_database.py`, in `LOCAL_FIELDS` (the fallback field list) and, if needed, in
`indexRow()`; old files without it must still work.

### Rebuilding it (every week, by itself)

The builder reads Scryfall's `all_cards` bulk file (every language of every printing; served as
gzipped JSON Lines since September 2026). `.github/workflows/update-cards.yml` runs
`tools/update_database.py` every Monday at 02:30 UTC (11:30 in Japan) on a GitHub runner; the
Actions tab's "Run workflow" starts it by hand. The schedule is read from `main`, the job works
on `staging`. It:

1. builds `ja_cards.json.gz` and `printings.json.gz` (`tools/build_ja_database.py --out …
   --printings …`, about a minute);
2. applies `tools/name_fixes_ja.json` (`tools/fix_names.py`) and writes the readings
   (`tools/name_readings.py`): the push it makes doesn't start the Name readings workflow, so it
   does both itself;
3. compares the new files with the ones in the repository (`tools/check_database.py`) and
   **refuses** the build when something looks lost: more than 30 cards gone, more than 30
   Japanese names or 60 Japanese texts gone (a text counts only with Japanese in it), any rarity down by more than 3%, more than 2% of
   Japanese names changed, more than 1% of printings gone, readings for fewer than 95% of
   Japanese names, or a well-known card (`SPOT_CHECKS`) without its Japanese name. A refused
   build changes nothing and the run goes red;
4. replaces the files only when their cards changed (the date alone is not a change), and
   commits them to `staging` with a what's-new note (new cards, cards that got a Japanese name or
   text, renamed, gone, fields changed). The note is also on the run's summary page.

The update reaches warujie.jp only when the owner says "publish", like any other change. The
fixes once made by hand after a rebuild (Japanese type lines from other printings, a Japanese
printing with a real scan) are made by the builder since 2.4, so `tools/audits/db_updates.py` is
no longer needed after a rebuild.

Claude's sandbox can't download the bulk file; a developer with normal internet can run
`python3 tools/update_database.py --work some/folder` in the repo folder (it needs
`pip install sudachipy sudachidict_full pykakasi`). Run both test suites after a rebuild by
hand; the searchbench uses the real database.

### The printings file (`printings.json.gz`)

Gzipped JSON, about 0.3 MB, one entry per printing (set and collector number, about 100,000):

```
{ "version": 1, "generated": "YYYY-MM-DD", "fields": ["langs", "rarity", "treatments"],
  "sets": { "mh3": { "1": ["en ja zhs fr de it es pt", "u", ""], … }, "4bb": { "4": ["ja de en@4ed", "r", ""] }, … } }
```

- `langs`: the languages that set and number exists in, in the card page's order. A language
  Scryfall files under the twin set code (`SET_TWIN`: `4bb`↔`4ed`, `bchr`↔`chr`, `fbb`↔`3ed`) is
  written `lang@set`, only when it is the same card.
- `rarity`: the English printing's (else the first seen), one letter as in `rarities`.
- `treatments`: the letters of `treatments` above, for that printing.

Made by the builder's `Printings` class. The card page reads it the first time it needs language
buttons (`loadPrintingsFile()`; see card-page.md); `sw.js` keeps it for offline use.

### How the counts compare with Scryfall

Checked against Scryfall's search on 2026-10-16 with `tools/audits/rarity_audit.py` (run on a
runner). Per rarity the site finds the same paper cards as Scryfall's `r:<rarity> game:paper`
to within a handful. Scryfall's plain `r:` shows more because it also counts:

- Arena- and MTGO-only cards (Alchemy and the like, about 690). The builder leaves
  digital-only cards out on purpose.
- Rarities a card has only in a digital set (Vintage Masters' Power Nine as "bonus", Tempest
  Remastered mythics). With the above, 140 of Scryfall's 2,853 mythics.

The site has about 825 cards Scryfall hides from its searches: playtest cards (Mystery Booster 2,
Unknown Event), holiday and convention joke promos, Heroes of the Realm, and the seven cards
Wizards withdrew in 2020 (Invoke Prejudice, Cleanse, Jihad…). They are in the database and in
the counts. AFR/CLB dungeons count as commons on Scryfall; the builder drops them with tokens.

### Fixing a Japanese name

Add `"English name": "日本語名"` to `tools/name_fixes_ja.json` (two-part cards: the full
`A // B` form on both sides) and push to `staging`. The workflow applies it to the database.
Read the name off a real Japanese card; `tools/audits/face_sheets.py` makes contact sheets of
Japanese name bars for that.

### Known gaps in Scryfall's Japanese data

- About 4,800 English printings in sets that were printed in Japanese have no Japanese entry
  (for example Dominaria Remastered's split cards #207–216).
- About 4,000 cards have a Japanese name but no Japanese text anywhere.
- Many old Japanese printings have only a placeholder image; the page shows the same
  printing's English picture with a note.

Nothing can fill these until another source is permitted (a request to Wizards is pending; see
CLAUDE.md rule 3). Don't scrape Gatherer or wikis.

## Metagame files

`build_meta.py` reads two public GitHub repositories only: tournament results from
[MTGODecklistCache](https://github.com/Jiliac/MTGODecklistCache) and archetype rules from
[MTGOFormatData](https://github.com/Badaro/MTGOFormatData). Its docstring explains the maths.

- `meta.json`: `{version, generated, data_through, sources, windows, trends}`.
  `windows["30"|"90"].formats.<format>` has `events`, `decks`, `matches`, `archetypes` (each
  with `name`, `colors`, `decks`, `share`, `wins`, `losses`, `draws`, `winrate`, `ci`, `cards`,
  `icon`, `sample`) and `rest`. `trends.<format>` holds the weekly shares (`TREND_WEEKS`, 12 weeks).
- `meta_decks.json`: `{version, generated, data_through, windows}`: one real list per archetype
  with how often each card is played.
- `meta_lists/<days>-<format>.json`: `{version, generated, decks}`: more sample lists, loaded only
  on a deck page.

Share counts decks in events of the period (Magic Online leagues left out); win rate counts
only events that publish every match; mirrors, byes and draws are left out.

If the metagame stops updating, look at the **Update metagame data** runs in GitHub Actions.

## warujie-prices files the site reads

All from `https://warujie.github.io/warujie-prices/` (`PRICE_DATA_URL`). The exact formats are
documented in the warujie-prices repository
([docs/data-formats.md](https://github.com/warujie/warujie-prices/blob/main/docs/data-formats.md)); in short:

| Path | Read by | What |
|---|---|---|
| `index.json` | `loadPriceIndex()` | Dates in the history, today's date, providers and their currencies, when listings were read |
| `h/<xx>.json.gz` | `loadPriceShard()` | Price history of printings whose Scryfall id starts with `xx` |
| `q/<xx>.json.gz` | `loadQuoteShard()` | Today's shop prices (`p`), listings (`l`), shop product links (`lk`) |
| `movers.json` | `loadMovers()` | Biggest risers and fallers, 1/7/30 days, US and EU |
| `c/index.json`, `c/<xx>.json.gz` | `loadComboIndex()`, `loadComboShard()` | Commander combos by oracle id |
| `t/tags.json.gz` | `loadTags()` | Role tags and EDHREC rank by oracle id (first 12 characters) |
| `cheap.json.gz` | `loadCheapest()` | Per card name, the cheapest paper printing's USD and EUR price in cents and its lowest Arena rarity (`m r u c`), for deck prices and wildcards |

The `h/` and `q/` requests carry `?d=<date>` so a new day's file is never served from the
browser's cache.

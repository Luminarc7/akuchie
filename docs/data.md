# Data files and the jobs that make them

| File | What | Made by | When |
|---|---|---|---|
| `ja_cards.json.gz` | The card database | `tools/build_ja_database.py`, then the Name readings workflow | By hand after new sets; the workflow runs on every change |
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
| `id` | The Scryfall printing shown in results: a Japanese printing with a real scan where possible, else an English one (another language only for cards never printed in English); when the builder's preferences are level, the ordinary frame over a showcase or borderless one (`picture_rank()`) |
| `oracle_id` | Scryfall's id for the card across printings |
| `name_en`, `name_ja` | Names; two-part cards as `A // B` |
| `type_en`, `type_ja` | Type lines |
| `oracle_en`, `oracle_ja` | Rules text (Japanese from the newest Japanese printing that has it) |
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
| `name_kana` | Reading of the Japanese name in hiragana: the あいうえお order, and names typed in hiragana (いなずま finds 稲妻); never shown. Made by `tools/name_readings.py`: printed furigana, else SudachiDict, else pykakasi for kanji Sudachi doesn't know, so no reading keeps a kanji |

When the page loads it, `indexRow()` adds computed fields starting with `_` (lowercased names,
type and text, colour string, keyword set…). To add a database field: add it in
`build_ja_database.py`, in `LOCAL_FIELDS` (the fallback field list) and, if needed, in
`indexRow()`; old files without it must still work.

### Rebuilding it

The builder reads Scryfall's `all_cards` bulk file (every language of every printing; served as
gzipped JSON Lines since September 2026). Claude's sandbox can't download it, so it runs on a
GitHub runner (CLAUDE.md, "Reaching other websites"; the `warujie-outside-data` skill). A
developer with normal internet can run `python3 tools/build_ja_database.py` in the repo folder.

After a rebuild:

1. Commit `ja_cards.json.gz` to `staging`. The **Name readings** workflow then runs
   `tools/fix_names.py` and `tools/name_readings.py` and commits back. Pull before your next
   commit.
2. Redo the one-off improvements a rebuild undoes, with `tools/audits/db_updates.py`
   (888 Japanese type lines taken from other Japanese printings; 51 rows switched to a Japanese
   printing with a real scan).
3. Run both test suites; the searchbench uses the real database.

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

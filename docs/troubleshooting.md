# Troubleshooting

Symptom → where to look → the usual fix. When you fix a bug whose cause wasn't obvious, add it
here.

## Search

| Symptom | Likely cause | Where / fix |
|---|---|---|
| Searches are slow or the results come from Scryfall (a "translated" note above results) | The card database didn't load | Browser console and network tab for `/ja_cards.json` / `ja_cards.json.gz`. On Cloudflare, check the deploy built `ja_cards.json.br` (build log of `tools/brotli_db.mjs`). Locally, make sure you run a web server (not `file://`) |
| Role words (除去, ドロー…) are searched as text; a note says roles are unavailable | `t/tags.json.gz` from warujie-prices didn't load (`tagsState === 'absent'`) | Is `https://warujie.github.io/warujie-prices/t/tags.json.gz` there? Check the warujie-prices workflow run |
| A slang word finds nothing or the wrong cards | Missing or too-broad entry in `JA_SLANG`, `JA_KW_SLANG`, `EN_WORD_ALIAS` | Add or narrow the entry; add a check in `dev/searchbench/search_checks.py` (also one that a wrong card is *not* found) |
| A card's name doesn't match without punctuation | `NAME_PUNCT_RE` lacks that character | Add it; check `nameKey()` |
| Japanese results are in an odd order | Missing or wrong `name_kana` for those cards | `tools/name_readings.py`; the Name readings workflow run; printed furigana in Scryfall wins over Sudachi |
| A search worked yesterday and doesn't now | A recent change in the search sections | `git log -p staging -- index.html`; run the searchbench on the previous commit to compare |

## Card page

| Symptom | Likely cause | Where / fix |
|---|---|---|
| Wrong or English Japanese name on a card | Scryfall's Japanese data is wrong or missing (common on two-part cards) | Add it to `tools/name_fixes_ja.json` ([data.md](data.md#fixing-a-japanese-name)) |
| No Japanese text | Scryfall has none for that card (about 4,000 cards) | Nothing to do until another source is permitted |
| Missing language button, or a button for the wrong printing | The printing's languages are under another set code | Add the pair to `SET_TWIN`; check with `tools/audits/audit_printings.py` |
| Japanese printing shows no price | Its English twin wasn't found (`priceHistoryId()`), or the shop data has no entry | Check `/cards/<set>/<number>/en` exists on Scryfall; check the `q/` shard |
| Listings, history or shop prices missing for every card | warujie-prices didn't publish | GitHub → warujie-prices → Actions → Update price history; the site keeps working with Scryfall's prices only |
| Prices show without yen | Frankfurter didn't answer (`fetchJpyRate()`) | Usually temporary; the code tries two Frankfurter addresses |
| A placeholder picture instead of a Japanese scan | Scryfall has only a placeholder for that printing | Expected: the page swaps in the English picture with a note |

## Metagame and decks

| Symptom | Likely cause | Where / fix |
|---|---|---|
| Metagame data is old | The daily **Update metagame data** run failed | GitHub → Warujie → Actions. Run it by hand ("Run workflow"). If MTGODecklistCache changed its format, `build_meta.py` needs a fix |
| A deck has an odd name or is "unclassified" | MTGOFormatData's archetype rules don't know it yet | Usually fixed upstream within days; nothing to change here |
| Arena/MTGO import complains about a card name | The two clients spell some two-part names differently | `exportName()` |

## Deploys and hosting

| Symptom | Likely cause | Where / fix |
|---|---|---|
| A push didn't change the site | No Workers build ran, or it failed | Check "Workers Builds: warujie" on the commit; empty commit to retrigger; read the Cloudflare build log |
| Build fails at `brotli_db.mjs` | `ja_cards.json.gz` is broken | Restore the last good file from git history and rebuild the database |
| `git push` to `staging` or `main` is rejected | A bot committed in the meantime | `git pull --no-rebase` and push again; never force-push `main` |
| Cloudflare scripts appear in the page source | HTML is bypassing `worker.js` (path not in `run_worker_first`) or the Worker changed | `wrangler.jsonc` `run_worker_first`; `worker.js` must keep `no-transform` |
| Link previews show the site's default card | The bot isn't matched by `PREVIEW_BOTS`, or `shareTags()` failed | Test with that bot's User-Agent against the `workers.dev` address |
| Visitors see an old version | Unlikely (the service worker is network-first); usually a slow deploy | Check the deployment in Cloudflare; a hard reload confirms |
| A file that should be private is downloadable from warujie.jp | Not listed in `.assetsignore` | Add it and push |

## Getting at outside data

Claude's sandbox can't reach Scryfall's API, warujie.jp or shop sites, and warujie.jp
challenges GitHub runners. Use the `workers.dev` address for the live site, and a GitHub
Actions workflow on a scratch branch for outside downloads (CLAUDE.md, "Reaching other
websites"; template `tools/audits/probe-workflow.example.yml`). Only fetch what the owner has
allowed.

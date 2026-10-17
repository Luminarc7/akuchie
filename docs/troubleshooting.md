# Troubleshooting

Symptom → where to look → the usual fix. When you fix a bug whose cause wasn't obvious, add it
here.

## Search

| Symptom | Likely cause | Where / fix |
|---|---|---|
| Searches are slow or the results come from Scryfall (a "translated" note above results) | The card database didn't load | Browser console and network tab for `/ja_cards.json` / `ja_cards.json.gz`. On Cloudflare, check the deploy built `ja_cards.json.br` (build log of `tools/brotli_db.mjs`). Locally, make sure you run a web server (not `file://`) |
| Role words (除去, ドロー…) are searched as text; a note says roles are unavailable | `t/tags.json.gz` from warujie-prices didn't load (`tagsState === 'absent'`) | Is `https://warujie.github.io/warujie-prices/t/tags.json.gz` there? Check the warujie-prices workflow run |
| A sentence copied from a card finds it, the same sentence typed without 、 finds nothing | Punctuation was compared literally | Fixed: `normJaSearch()` drops it from cards and searches (`JA_PUNCT_RE`). When mapping a list through it, write `.map(l => normJaSearch(l))`: `.map(normJaSearch)` passes the index as `keep` |
| `{T}:…` or `2:…` typed from a card finds nothing | `parseSearch()` read the part before the colon as an operator | Fixed: an unknown "operator" in Japanese text or starting with `{` is text. A new real operator must be in `KNOWN_OPS` |
| A slang word finds nothing or the wrong cards | Missing or too-broad entry in `JA_SLANG`, `JA_KW_SLANG`, `EN_WORD_ALIAS` | Add or narrow the entry; add a check in `dev/searchbench/search_checks.py` (also one that a wrong card is *not* found) |
| A card's name doesn't match without punctuation | `NAME_PUNCT_RE` lacks that character | Add it; check `nameKey()` |
| Rules text typed without its particles (カード2枚引く) finds nothing, though カードを2枚引く works | `jaMayHave()`, the quick pre-check, compared the text without particles only when the search itself had some | Fixed: it compares without particles for any search that isn't all hiragana |
| A typed name finds nothing | Not the printed name: a nickname, the katakana of an English-only card, or a typo | Add the nickname to `CARD_NICKNAMES`; typos go through `closestJaName()` (check its distance limits) |
| Japanese results are in an odd order | Missing or wrong `name_kana` for those cards (a kanji left in a reading sorts after ん) | `tools/name_readings.py`; the Name readings workflow run; printed furigana in Scryfall wins over Sudachi; kanji Sudachi doesn't know (滅殺) and numbers (三) are read with pykakasi / the number's reading |
| A name typed in hiragana doesn't find the card | Its `name_kana` is wrong, or the word reads as game words (`yomiQuery()` skips those) | Check the reading in the database; `yomiKey()` for ー and ゔ |
| Fewer cards per rarity than Scryfall shows (神話レア 2,203 against Scryfall's 2,853) | The filter looked only at the rarity of the printing shown; Scryfall counts every printing (Sengir Vampire: uncommon, rare, mythic) and Arena-only cards | Fixed: the `rarities` field and `hasRarity()`. The rest of the difference is expected; see data.md, "How the counts compare with Scryfall" |
| A Legends or The Dark card shows an Italian picture and the wrong rarity | The builder kept another language's printing as the card's "English" one when the English printings ranked level with it | Fixed in the builder (2.3): an English printing always replaces such a fallback; the 116 rows were switched in the database |
| 到達 (or 追放, 破壊) lists cards that don't do it, mixed in with the ones that do | The word is in their reminder text （…）: 飛行's reminder mentions 到達, 接死's 破壊, an adventure's 追放 | Fixed: a word only in reminder text scores half a step lower (`JA_REMINDER_RE`, `locateJa()`'s `plain`), so those cards come last |
| ボーダーレス版, ボーダーレスのドラゴン, 日本語版のカード find nothing though ボーダーレス works | Only the bare printing word was read as the filter | Fixed: `printWordForms()` reads 版, の, あり and のカード forms |
| A search worked yesterday and doesn't now | A recent change in the search sections | `git log -p staging -- index.html`; run the searchbench on the previous commit to compare |

## Card page

| Symptom | Likely cause | Where / fix |
|---|---|---|
| Wrong or English Japanese name on a card | Scryfall's Japanese data is wrong or missing (common on two-part cards) | Add it to `tools/name_fixes_ja.json` ([data.md](data.md#fixing-a-japanese-name)) |
| No Japanese text | Scryfall has none for that card (about 4,000 cards) | Nothing to do until another source is permitted |
| English text or an English type line shown as the Japanese one (most of Edge of Eternities) | Scryfall gives those Japanese printings the English text | Since builder 2.5 such a text doesn't count as Japanese; `indexRow()` empties it in older files and `displayTypeJaRaw()` translates the type |
| In English, the card page shows a Japanese picture and Japanese flavor text | The link named the Japanese printing (the database's id); before 2026-10-17 the page kept it | `siteLanguagePrinting()` opens the English card of the same printing; check the printings file lists `en` for that set and number |
| Missing language button, or a button for the wrong printing | The printing's languages are under another set code | Add the pair to `SET_TWIN`; check with `tools/audits/audit_printings.py` |
| Japanese printing shows no price | Its English twin wasn't found (`priceHistoryId()`), or the shop data has no entry | Check `/cards/<set>/<number>/en` exists on Scryfall; check the `q/` shard |
| Listings, history or shop prices missing for every card | warujie-prices didn't publish | GitHub → warujie-prices → Actions → Update price history; the site keeps working with Scryfall's prices only |
| Prices show without yen | Frankfurter didn't answer (`fetchJpyRate()`) | Usually temporary; the code tries two Frankfurter addresses |
| A placeholder picture instead of a Japanese scan | Scryfall has only a placeholder for that printing | Expected: the page swaps in the English picture with a note |

## Metagame and decks

| Symptom | Likely cause | Where / fix |
|---|---|---|
| Metagame data is old | The daily **Update metagame data** run failed | GitHub → Warujie → Actions. Run it by hand ("Run workflow"). If MTGODecklistCache changed its format, `build_meta.py` needs a fix |
| A sample list says "3st Place" | The source data writes some ordinals wrong (2st, 3st, 22th) | `placeText()` puts them right when shown |
| A deck has an odd name or is "unclassified" | MTGOFormatData's archetype rules don't know it yet | Usually fixed upstream within days; nothing to change here |
| A phone page scrolls sideways in English only | Short pieces with `white-space: nowrap` joined with no space between them: English has no place to break the line (Japanese breaks after （）) | Join them with a space, as the deck page's facts line (`.deck-meta`) does before each ·; check with `dev/tests/e2e.py`'s `no_hscroll()` at 360px in English |
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

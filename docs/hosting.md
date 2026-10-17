# Hosting: Cloudflare, the Worker, the offline copy

## Cloudflare Workers

The site is a Cloudflare Worker named **warujie** with static assets: every file in this
repository is served as it is, except what `.assetsignore` lists. Configuration:
[`wrangler.jsonc`](../wrangler.jsonc).

- **Deploys:** Workers Builds (connected to the GitHub repo) builds every push. `main` →
  warujie.jp; any other branch → `https://<branch>-warujie.warujie-mtg.workers.dev`.
- **Build step:** `node tools/brotli_db.mjs` makes `ja_cards.json.br` and checks the database
  unpacks to valid JSON; a broken database stops the deploy instead of reaching visitors.
- **`run_worker_first`** lists the only paths that go through `worker.js`: `/`, `/index.html`,
  `/preview`, `/preview.html`, `/preview/`, `/ja_cards.json`, `/shop/rakuten`. Everything else
  is served straight from the static files.
- **Secrets:** `RAKUTEN_APP_ID` and `RAKUTEN_ACCESS_KEY` (Rakuten Web Service), set by the owner
  in Cloudflare → Workers & Pages → warujie → Settings → Variables and Secrets, as type
  "Secret". They are never in the repository. The test sites use the same ones.
- **Domain:** warujie.jp is registered at XServer Domain; DNS is on Cloudflare. Cloudflare's
  Bot Fight Mode is on, so warujie.jp challenges bots, including GitHub runners and Claude's
  sandbox. To check the live site from a script, use `https://warujie.warujie-mtg.workers.dev/`
  (same Worker, same files).
- **A legacy GitHub Pages build** of this repo still runs on `main` from before Cloudflare. It is
  harmless; the page notices `github.io` in a few places (`PRICE_DATA_URL`, no service worker).

### What is published

`.assetsignore` keeps these out of the public site: `.git`, `.github`, `.assetsignore`,
`wrangler.jsonc`, `build_meta.py`, `README.md`, `worker.js`, `_headers`, `tools`, `.gitignore`,
`dev`, `docs`, `CLAUDE.md`. **Anything new that shouldn't be downloadable from warujie.jp goes
there.** (The repository itself is public on GitHub, so never put secrets in any file.)

## `worker.js`

Five jobs:

1. **HTML without Cloudflare's injected scripts.** Cloudflare would add its Web Analytics beacon
   and bot-detection script to HTML. The Worker fetches the page from the assets, sets
   `Cache-Control: … no-transform` and gzips it itself (`CompressionStream`), because
   `no-transform` alone would also turn off Cloudflare's compression. ETags become weak ones
   because the compressed bytes differ from the file. This keeps the footer's "no analytics"
   promise true.
2. **The card database.** `/ja_cards.json` answers with `ja_cards.json.br` (`Content-Encoding:
   br`) or, for a browser without brotli, `ja_cards.json.gz` (`Content-Encoding: gzip`). The
   browser unpacks either one itself. Outside Cloudflare (local tests, GitHub Pages) the page
   falls back to fetching `ja_cards.json.gz` and unpacking it in JavaScript.
3. **Link previews.** When a bot (`PREVIEW_BOTS`: LINE, X, Discord, Slack, search engines…)
   asks for a page with a query string, `shareTags()` works out a title, description and
   picture, and `rewriteTags()` writes them into `<title>` and the `og:`/`twitter:` tags with
   `HTMLRewriter`. Covered: `?card=` (from Scryfall, cached a day), `?view=deck` (numbers from
   `meta.json`), `?view=meta`, `?view=prices`, `?view=import` (also `?view=want`), `?set=`. People always get the page unchanged.
   Any error keeps the page's own tags.

When you add a page type, add its share tags in `shareTags()` and a check in
`dev/tests/e2e.py`.

4. **Rakuten Books products** (`rakutenItems()`). `/shop/rakuten?kind=sl` (Secret Lair) or
   `?kind=box[&set=<Japanese set name>]` (booster boxes), with `&aff=<affiliate ID>` when the page
   has one. It asks Rakuten's Books Total Search API (`RAKUTEN_API`, games genre `006`, newest
   first) with the two secrets, sending `RAKUTEN_SITE` (warujie.jp, the site registered with the
   Rakuten app) as Referer and Origin. Only these fixed searches are possible, so nobody can spend
   the API quota on other searches. It keeps Magic products with Rakuten links only (for boxes:
   no single packs, bundles or decks, at least 8,000 yen), at most 12, as
   `{ ok, items: [{ title, price, url, image, date, avail }] }`. Cloudflare keeps Rakuten's
   answer an hour (`cacheTtlByStatus`), so Rakuten is asked rarely. Until the secrets exist it
   answers `{ ok: false, reason: "not-configured" }`; a Rakuten error gives
   `reason: "rakuten-<status>"`, kept two minutes. Tests: `dev/tests/worker_shop.mjs`.
   **Setting it up (owner):** make a Rakuten Web Service app of type "Webアプリケーション" with
   `https://warujie.jp` as its allowed site, then add the two secrets above.

5. **The pink icon on the test sites** (`isTestSite()`, `testIcons()`). On a branch preview
   (`<branch>-warujie.warujie-mtg.workers.dev`, staging included) the page's icon,
   apple-touch-icon and manifest links are pointed at the pink files (`TEST_ICONS`:
   `icons/*-v4-test.png`, `manifest-test.webmanifest`), so a test site saved to a phone's home
   screen is easy to tell from warujie.jp. warujie.jp and `warujie.warujie-mtg.workers.dev` keep
   the green icon. Tests: `dev/tests/worker_icons.mjs`.

## `sw.js`: the offline copy

A service worker so the installed app opens without a connection, with search working on the
stored database.

- **Network first, always.** It only answers from its cache when the network fails, so nobody
  is kept on an old version, and a rollback reaches visitors on their next visit.
- **Stored:** the page (any URL of it, stored under its path), `/ja_cards.json`, `/printings.json.gz`, `/meta.json`,
  `/meta_decks.json`, `/combo_ja.js`, `/manifest.webmanifest`, `/manifest-test.webmanifest`, `/meta_lists/*`, `/icons/*`
  (`KEEP`). Other origins (Scryfall, fonts, price data) are left to the browser.
- The database (about 22 MB unpacked) is stored again only when its ETag changed.
- The cache is named `warujie-v2` (`CACHE`). Changing the name makes every visitor drop the old
  cache on the next activation; do that only when the stored format changes.
- Registered only over HTTPS and not on `github.io` (the "install as an app" section of
  `index.html`).

## Rolling back

1. **Fastest:** Cloudflare dashboard → Workers & Pages → warujie → Deployments → choose the
   earlier deployment → Rollback. The next push to `main` deploys `main` again, so also fix the
   code (step 2) if the problem is in it.
2. **In the code:** every publish leaves a branch `backup-<date>-before-<what>` with the site as
   it was. Merge or reset `main` back to it and push; Cloudflare redeploys. Each backup branch is
   also viewable at `https://backup-<date>-before-<what>-warujie.warujie-mtg.workers.dev`.

[`../README.md`](../README.md) explains the same for the owner.

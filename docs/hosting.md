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
  `/preview`, `/preview.html`, `/preview/`, `/ja_cards.json`. Everything else is served straight
  from the static files.
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

Three jobs:

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

## `sw.js`: the offline copy

A service worker so the installed app opens without a connection, with search working on the
stored database.

- **Network first, always.** It only answers from its cache when the network fails, so nobody
  is kept on an old version, and a rollback reaches visitors on their next visit.
- **Stored:** the page (any URL of it, stored under its path), `/ja_cards.json`, `/meta.json`,
  `/meta_decks.json`, `/combo_ja.js`, `/manifest.webmanifest`, `/meta_lists/*`, `/icons/*`
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

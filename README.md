Japanese websites to search for magic cards
eventually will add prices for local stores

## Test site (staging)

- `main` → **warujie.jp** (live). Every push to `main` goes live.
- `staging` → test site at `https://staging-warujie.<subdomain>.workers.dev` (not indexed by search engines).
  Work is pushed to `staging` first; when it's ready, merge `staging` into `main` to publish.

## Data files and the jobs that keep them up to date

- `ja_cards.json.gz` – the card database. When it changes, the **Name readings** workflow adds the
  reading of every Japanese card name (`name_kana`, for the あいうえお order; never shown) using
  `tools/name_readings.py`. At each deploy `tools/brotli_db.mjs` makes `ja_cards.json.br`, which
  `worker.js` sends as `/ja_cards.json` (half the download of the .gz).
- `meta.json`, `meta_decks.json`, `meta_lists/` – the metagame tab, deck pages, weekly trends and the
  sample lists per deck. Rebuilt every day by **Update metagame data** (`build_meta.py`).
- `manifest.webmanifest`, `sw.js`, `icons/`, `og.png` – the installable app, its offline copy and the
  picture shown when a link to the site is shared. `worker.js` fills in card and deck share tags for
  link-preview bots.

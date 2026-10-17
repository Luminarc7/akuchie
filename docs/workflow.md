# Working on the site

## Set up

```sh
git clone https://github.com/warujie/Warujie.git
git clone https://github.com/warujie/warujie-prices.git    # next to it; the tests use its builders
cd Warujie
git checkout staging
python3 -m pip install playwright pillow                    # for the tests; Chromium via `playwright install chromium`
```

If git says `staging` has no upstream (some sandboxes fetch only `main`):
`git config --add remote.origin.fetch '+refs/heads/staging:refs/remotes/origin/staging' && git fetch origin && git branch -u origin/staging`.

## Run it on your computer

```sh
python3 -m http.server 8000
# open http://localhost:8000/
```

That is the whole site with real data: it loads `ja_cards.json.gz` from the folder and talks to
Scryfall, Frankfurter and warujie-prices directly. What you don't get locally: the Worker
(brotli database, link-preview tags) and the offline copy (needs HTTPS). To try `worker.js`
too: `node tools/brotli_db.mjs && npx wrangler dev`.

## Make a change

1. Edit `index.html` (and other files). Follow the conventions in
   [index-html.md](index-html.md#conventions-in-the-code): both languages for any text, CSS
   variables for colours, `esc()` for outside text.
2. Run `python3 tools/make_preview.py` (rewrites `preview.html`; never edit that by hand).
3. Update the docs that describe what you changed (below).
4. Test (below), and look at it at 1280px and 390px wide, light and dark, and in lightweight mode.

## Tests

Both must pass before every push. Details in [`../dev/README.md`](../dev/README.md).

| Command | What it checks | Time |
|---|---|---|
| `python3 dev/tests/e2e.py` | About 600 checks of the whole site in headless Chromium; every network request answered from fixtures, so it runs offline and repeatably. Last line: `N/N checks passed` | a few minutes |
| `cd dev/searchbench && python3 search_checks.py ../../index.html` | About 90 real searches against the real database and role tags | a minute or two |
| `node dev/tests/worker_icons.mjs` | `worker.js` gives the test sites the pink app icon and warujie.jp the green one; every icon file exists | seconds |
| `node dev/tests/worker_shop.mjs` | `worker.js`'s Rakuten Books list (`/shop/rakuten`) against a fixture of Rakuten's API | seconds |
| `python3 dev/check_docs.py` | Every function, constant, file and section the docs name still exists | seconds |

Add checks for every new feature or fix: in `e2e.py` as a new numbered section near the end
(`check("what it proves", condition, detail)`), in `search_checks.py` for search behaviour.
`dev/searchbench/harness.py` opens the site with real data, for screenshots or reproducing a
bug.

## Commit and push to `staging`

```sh
git pull --no-rebase origin staging      # bots commit too (name readings, weekly card update)
git add -A && git commit -m "What changed for users, in plain words"
git push origin staging
```

Then check the Cloudflare build on the commit: GitHub → the commit → checks → **Workers
Builds: warujie** should be green (or `gh api repos/warujie/Warujie/commits/<sha>/check-runs`).
If no build started, an empty commit (`git commit --allow-empty -m "Rebuild"`) retriggers it.
Look at the test site: `https://staging-warujie.warujie-mtg.workers.dev`.

## Publish (owner's word only)

Publishing happens **only when the owner says "publish"** (CLAUDE.md rule 2).

```sh
git fetch origin
git push origin origin/main:refs/heads/backup-$(date +%F)-before-<what>   # backup of the live site
git checkout -B main origin/main
git merge --no-ff origin/staging -m "Publish: <what goes live>"
git push origin main
```

Never force-push `main`: the daily metagame job commits there. Confirm the production Workers
build, then that the live page matches (fetch `https://warujie.warujie-mtg.workers.dev/` and
compare with `index.html`). Rolling back is in [hosting.md](hosting.md#rolling-back).

## Keeping these docs true

The docs are only useful if they match the code, so they change with it:

- **Every commit that changes behaviour, a file, a data format, a URL, a workflow, a schedule
  or a setting updates the doc that covers it, in the same commit.** The table "Which doc covers
  which code" in [README.md](README.md#which-doc-covers-which-code) says where.
- A new feature gets a line in the right doc (and in the "I want to change…" table if people
  will look for it). A removed feature is removed from the docs.
- A bug whose cause wasn't obvious gets a line in [troubleshooting.md](troubleshooting.md).
- The owner's rules and decisions stay in `CLAUDE.md`; when one changes, change it there.
- Name things by function, constant or section marker, never by line number.
- GitHub runs the same checker on every push to `staging` and `main` and on pull requests
  (`.github/workflows/check-docs.yml`, check "Docs match the code"). A red check means a doc
  names something that no longer exists: fix the doc.
- Run `python3 dev/check_docs.py` before pushing. It lists every name in backticks in `docs/`
  that no longer exists in the code (a renamed function, a deleted file), so stale docs show up
  at once. It can't tell whether a description is still right; reread the paragraphs around
  what you changed.

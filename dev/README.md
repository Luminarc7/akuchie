# Development tools (not published on the site)

Everything in `dev/` (and `tools/`) stays out of the website: `.assetsignore` lists both.

## Requirements

- Python 3 with `playwright` (Chromium) and `Pillow`.
- A clone of the **warujie-prices** repository next to this one
  (`../warujie-prices`), or `WARUJIE_PRICES=/path/to/warujie-prices`. The tests run its
  `build_prices.py` and `build_combos.py` to make realistic price and combo data.

## `dev/tests/e2e.py` — the whole site in a headless browser

    python3 dev/tests/e2e.py            # tests ./index.html and ./preview.html
    WARUJIE_PAGES=/some/build python3 dev/tests/e2e.py   # tests pages in another folder

About 660 checks. Every network request is answered from fixtures (Scryfall, the exchange
rate, the card database, price and combo data, metagame files), so it runs offline and
gives the same result every time. It covers search, filters, suggestions, card pages
(language buttons, prices, listings, history), sets, metagame and deck pages, export,
the app install, link previews, English mode, lightweight mode (軽量), phones. The last line is
`N/N checks passed`; failures are listed by name. Run it before every push.

- `fixtures/real_meta.json` — a frozen copy of a real `meta.json`, for the metagame checks.
- `fixtures/fixture_cards.json`, `price_fixtures.py`, `combo_fixture.py`, `search_rows.py` —
  the fixture builders.
- When you add a feature, add its checks near the end of `e2e.py` (numbered sections,
  `check("what it proves", condition, detail)`).

## `dev/searchbench/` — search against the real card database

    cd dev/searchbench && python3 search_checks.py ../../index.html

About 240 checks of real searches (Japanese and English names, rules text, readings, typos,
punctuation-free names, role words, players' slang, everyday wording, hiragana, card shapes,
colors and mana values, and 600 searches typed from random cards' own text and names) against the real `ja_cards.json.gz` and role tags.
`common_searches.py` holds the 100 searches Japanese players type most, each with what it must
find (one check each), and `EVERYDAY_SEARCHES`, everyday words that once found nothing (シャッフル,
ETBでカードを引く, エルフ ロード…); add a search there when one should work and doesn't.
`harness.py` opens the site with the real database and stubs Scryfall; use it for
screenshots or to reproduce a bug with real data.

## `check_docs.py` — the docs still match the code

    python3 dev/check_docs.py

Every function, constant, element id, file, saved setting and `index.html` section named in
`docs/` must still exist; it lists the ones that don't. Run it before every push, together with
the two suites above.

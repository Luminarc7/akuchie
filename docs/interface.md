# Interface: text, languages, themes, lightweight mode, phones

## Text in two languages

Every visible string exists in Japanese and English. Japanese is the default; the 「EN」 button
(`#langBtn`) switches, and the choice is saved.

- **`STR`** holds every string: `'key': ['日本語', 'English']`. Placeholders look like `{n}`.
- **`t(key, vars)`** returns the string in the current language (`LANG`), filling in `vars`.
  A missing key shows the key itself, which makes typos easy to spot.
- **`tn(key, n)`** is `t()` with a count; in English it uses `key + '.one'` when `n` is 1.
- **Fixed HTML** uses attributes that `applyStaticText()` fills:
  `data-i18n` (text), `data-i18n-html` (HTML), `data-i18n-ph` (placeholder),
  `data-i18n-aria` (aria-label), `data-i18n-title` (tooltip). The Japanese text is also written
  in the HTML itself so the page reads right before the script runs.
- **`setLang(lang)`** redraws the current view, the filters, the yen labels and the results in
  the new language. If you add a view that keeps text on screen, redraw it there too.

Adding a string: add a `STR` entry with both languages, use `t('your.key')` (or a
`data-i18n` attribute), and add a check in `dev/tests/e2e.py` if it matters.

Game words have their own tables: `FORMAT_JA`/`FORMAT_EN`, `CREATURE_TYPE_JA`, `JA_KEYWORDS`,
`SUPERTYPE_JA`, `CARDTYPE_WORD_JA`, `SUBTYPE_JA`, `SET_NAME_JA`, rarity labels (`rarity.*` in
`STR`). Use the official Japanese card wording.

## Themes

Dark and light. The `<head>` script picks the saved theme, otherwise the device's preference,
and sets `<html data-theme>` before the page paints. `setTheme()` switches and saves it.

Colours are CSS variables at the top of `<style>`: `--page`, `--surface`, `--text`, `--muted`,
`--accent`, `--line`, the `--ok`/`--bad`/`--warn` families, mana colours `--mana-*` and so on,
once for dark and once for light. **Use the variables in new CSS**, never fixed colours, so both
themes work.

## Lightweight mode (軽量)

For slow phones and connections: `<html data-lite="1">`, saved as `akuchie-lite`. In this mode:

- web fonts are not loaded (the `<head>` script stops early);
- the card database downloads only when first needed (`dbGate`, `dbReady`), not at load;
- results default to the text view and decks to the list view;
- some heavy panels show a button instead of loading by themselves (`liteButton()`).

Switching it reloads the page (`setLite()`), because fonts and data are decided at load.
Check new features in lightweight mode too: anything that loads big data should wait for a
click there.

## Phones

Breakpoints are plain `@media (max-width: …)` rules next to the styles they change; the main
ones are 820px (phone layout: filter panel becomes a drawer, `setFilterDrawer()`) and 480px.
On phones the theme and lightweight switches sit in a small menu (`#menuBtn`, `setMenu()`),
and the Japanese shop list shows `JP_DIR_PHONE` shops before "load more". Always look at a
change at 390px wide as well as 1280px, and in English too: English words are longer and only
break at spaces, so a line that wraps fine in Japanese can push the page sideways.

## Settings saved in the browser

All in `localStorage`, all optional (private browsing just forgets them). **Keep the
`akuchie-` names**: renaming would reset every visitor's settings.

| Key | What |
|---|---|
| `akuchie-theme` | `light` / `dark` |
| `akuchie-lang` | `en` when English was chosen |
| `akuchie-lite` | `1` in lightweight mode |
| `akuchie-view` | `text` for the text view of results |
| `akuchie-market` | price tab: `jp`, `us`, `eu` |
| `akuchie-offer-foil` | `1` when listings show foil |
| `akuchie-similar` | similar-cards toggles (colour, mana value, type) |
| `akuchie-recent` | the last 10 searches |
| `akuchie-deck-view` | `list` for the deck list view |

Nothing is sent anywhere. The footer promises no sign-up, cookies, analytics or ads; any change
that would break that promise needs the owner's decision first (CLAUDE.md, rule 6).

## Accessibility habits already in the code

Buttons are real `<button>`s; tabs use `role="tab"` with `aria-selected`; switches use
`aria-checked`; motion is reduced under `prefers-reduced-motion`. Keep new controls the same way.

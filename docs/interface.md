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

## Sizes that should match

- **Mana symbols** (Scryfall's images, from `symbolImg()` and `renderPips()`) come in a few sizes
  only: `--sym-s` (16px) beside list text and deck names (search text rows, similar cards,
  combos, deck lists, the metagame table, the home page's top decks), `--sym-l` (20px) beside a
  page title (the card page's mana cost, a deck page's title), and 1em inside card text
  (`.sym`). The one exception is the metagame on phones, where closed rows use 11px (the owner's
  choice). The colour and mana value buttons of the filters use one image size per place
  (sidebar 21px, panel and phones 24px in a 34px button). Use the variables instead of new pixel sizes.
- **Buttons side by side share one height:** the results toolbar (詳しい条件, 画像/テキスト, sort
  menu: 34px, 36px on phones), a deck page's 書き出す and 画像/リスト (34px), and the metagame
  header's buttons and sort menu (30px, 28px on phones). These rules are the "round 10" block at
  the end of `<style>`.
- **Metagame rows read along one line:** rank, deck name, price, share and win rate sit on the
  row's first line (the rows are top-aligned), with the colours, deltas and details below.

## The advanced search panel (詳しい条件)

One panel, `#filterPanel`, opened and closed by `setFilterDrawer()`. `placeFilterPanel()` moves
it between three places: under the home search box (`#heroAdvSlot`), the results sidebar on
screens 1000px and wider (`#sideAdvSlot`), and above the results on narrower screens
(`#resultsAdvSlot`). Its sections run colour, mana
value, rarity, card type, then the four text fields (role, creature type, keyword, format) in
one `.filter-fields` group; that is also the tab order. The layout is the "round 11" block at the
end of `<style>`:

- **Wide panels** wrap the sections in lines. How they wrap follows the panel's own width
  (`@container`), because the home page puts the panel beside the effect examples (about 830px
  inside on desktops) once they load, and full width before. On desktops that gives colour +
  mana value + rarity / card types / the four fields two by two. From 920px the text fields
  leave their group (`display: contents`): フォーマット joins the first line (CSS `order`, so it
  is still last in tab order) and the other three share the last line. Placeholders must never
  be cut off.
- **The sidebar** puts colours, mana values and rarities on one nine-column grid, so all nine mana values
  fit on one line and the colours line up above them; with smaller chips everything fits a
  900px-tall screen without scrolling inside the panel.
- **Phones** use the same nine-column grid at 36px tall, one column of fields, and 16px text in
  the fields so iPhones don't zoom in when one is tapped. Up to 900px the panel fills the page
  column (it used to keep the old slide-in drawer's 360px width).
- Suggestion lists under the text fields may be wider than their field (up to 340px).
- **Rarity buttons** (`.rar-chip`) are C U R M discs the size of the mana value buttons, with
  the full name as tooltip and in the filter pill (`chipLabel()`). While off they are all one
  plain colour; the chosen one fills with the cards' rarity colour (`--rar-common`,
  `--rar-uncommon`, `--rar-rare`, `--rar-mythic` in `:root`, also used by `.dot`). The owner
  asked for this look. Several can be on at once (any of them). A rarity finds a card by any
  printing at it; a tile whose own printing is another rarity still says the rarity asked for,
  with an arrow beside it (`.shift-icon`: ↓ the picture is a lower rarity, ↑ a higher one, on a
  disc of the picture's rarity colour; the owner asked for this instead of 神話レア版あり), and
  the tooltip `rarity.alsoTip` names the picture's rarity.

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
ones are 820px (phone layout: the advanced search opens in the page above the results,
`setFilterDrawer()`) and 480px.
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
| `akuchie-deck-view` | `list` for the deck list view (also the deck price page's view) |
| `warujie-deck-import` | the list pasted on the deck price page (`IMPORT_SAVE_KEY`). New keys use `warujie-`; the old `akuchie-` ones stay as they are |
| `warujie-want` | the want list: JSON, one entry per card with its printing (`WANT_KEY`; see [other-pages.md](other-pages.md#want-list-)) |
| `warujie-want-view` | `image` when the want list page shows pictures (`WANT_VIEW_KEY`) |

Nothing is sent anywhere. The footer promises no sign-up, cookies, analytics or ads; any change
that would break that promise needs the owner's decision first (CLAUDE.md, rule 6).

## Accessibility habits already in the code

Buttons are real `<button>`s; tabs use `role="tab"` with `aria-selected`; switches use
`aria-checked`; motion is reduced under `prefers-reduced-motion`. Keep new controls the same way.

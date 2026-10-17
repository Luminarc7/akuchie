"""Price data for the end-to-end test, made by running the real builder
(build_prices.py v4) over 45 simulated days, with euro prices and, on the
last day, MTGJSON's shop prices for a few printings and the shops' offers
(Card Kingdom, Mana Pool) by condition with stock, and ENNDAL GAMES' stock in yen."""
import gzip, json, lzma, os, subprocess, sys, tempfile
from datetime import date as _date, timedelta as _td

# the price and combo builders come from the warujie-prices repository (a clone next to this one,
# or WARUJIE_PRICES=/path/to/warujie-prices)
_REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PRICES_REPO = os.environ.get("WARUJIE_PRICES", os.path.join(os.path.dirname(_REPO), "warujie-prices"))
BUILDER = os.path.join(PRICES_REPO, "build_prices.py")
START = _date(2026, 8, 26)

def price_day(cards, n):
    # (usd, usd_foil, eur, eur_foil)
    move = {"rag-en-mh2": (30 + n * 0.25, 50 + n * 0.25, 28 + n * 0.2, 45 + n * 0.2),
            "saga-en": (40 - n * 0.25, None, 30 + n * 0.3, None),
            "drs-en": (4 + n * 0.2, None, 12 - n * 0.15, None),
            "qp-en": (2 + n * 0.12, None, None, None),
            "bolt-en-m10": (1.2, None, 1.0, None),
            "rag-en-mh2-bl": (55, None, None, None),
            "rag-en-mul": (41, None, 38, None)}
    out = []
    for c in cards:
        if c["lang"] != "en" or c["id"] not in move:
            continue
        vals = list(move[c["id"]])
        if c["id"] == "rag-en-mh2" and n == 20:
            vals = [None] * 4   # a day with no price: the line has a gap
        f = lambda v: None if v is None else f"{v:.2f}"
        out.append(dict(c, prices={"usd": f(vals[0]), "usd_foil": f(vals[1]), "eur": f(vals[2]), "eur_foil": f(vals[3])}))
    return out

def mtgjson_files(folder, day):
    d = day.isoformat()
    ids = {"meta": {"date": d}, "data": {
        "u-rag": {"name": "Ragavan, Nimble Pilferer", "identifiers": {"scryfallId": "rag-en-mh2"}},
        "u-saga": {"name": "Urza's Saga", "identifiers": {"scryfallId": "saga-en"}},
        "u-bolt": {"name": "Lightning Bolt", "identifiers": {"scryfallId": "bolt-en-m10"}},
        "u-mul": {"name": "Ragavan, Nimble Pilferer", "identifiers": {"scryfallId": "rag-en-mul"}}}}
    today = {"meta": {"date": d}, "data": {
        "u-rag": {"paper": {
            "tcgplayer": {"currency": "USD", "retail": {"normal": {d: 41.0}, "foil": {d: 61.0}}},
            "cardkingdom": {"currency": "USD", "retail": {"normal": {d: 44.99}, "foil": {d: 69.99}}, "buylist": {"normal": {d: 30.0}, "foil": {d: 45.0}}},
            "cardsphere": {"currency": "USD", "retail": {"normal": {d: 39.5}}},
            "cardmarket": {"currency": "EUR", "retail": {"normal": {d: 36.8}, "foil": {d: 52.0}}}},
            "mtgo": {"cardhoarder": {"currency": "USD", "retail": {"normal": {d: 3.0}}}}},
        "u-saga": {"paper": {"cardkingdom": {"currency": "USD", "retail": {"normal": {d: 32.99}}}}},
        "u-mul": {"paper": {"cardmarket": {"currency": "EUR", "retail": {"normal": {d: 38.0}}}}}}}
    with lzma.open(os.path.join(folder, "AllIdentifiers.json.xz"), "wt") as f: json.dump(ids, f)
    with lzma.open(os.path.join(folder, "AllPricesToday.json.xz"), "wt") as f: json.dump(today, f)

def lows_files(folder):
    """TCGCSV-style folder and a Cardmarket price guide for the last day."""
    t = os.path.join(folder, "tcgcsv", "tcgplayer", "1", "77")
    os.makedirs(t, exist_ok=True)
    json.dump({"success": True, "results": [{"groupId": 77, "name": "Fixture sets"}]}, open(os.path.join(folder, "tcgcsv", "tcgplayer", "1", "groups"), "w"))
    json.dump({"success": True, "results": [
        {"productId": 1001, "lowPrice": 37.5, "marketPrice": 41.0, "subTypeName": "Normal"},
        {"productId": 1001, "lowPrice": 55.0, "marketPrice": 61.0, "subTypeName": "Foil"},
        {"productId": 1002, "lowPrice": 28.0, "marketPrice": 30.0, "subTypeName": "Normal"}]}, open(os.path.join(t, "prices"), "w"))
    json.dump({"version": 1, "createdAt": "2026-10-09T02:00:00+0200", "priceGuides": [
        {"idProduct": 2001, "idCategory": 1, "low": 31.9, "trend": 35.0, "low-foil": 48.0}]}, open(os.path.join(folder, "guide.json"), "w"))

def offers_files(folder):
    """Card Kingdom's and Mana Pool's price lists for the last day."""
    cv = lambda nm, nq, ex, eq, vg=None, vq=0, g=None, gq=0: {"nm_price": nm, "nm_qty": nq, "ex_price": ex, "ex_qty": eq, "vg_price": vg, "vg_qty": vq, "g_price": g, "g_qty": gq}
    ck = {"meta": {"created_at": "2026-10-08 20:07:57", "base_url": "https://www.cardkingdom.com/"}, "data": [
        {"id": 1, "scryfall_id": "rag-en-mh2", "url": "mtg/modern-horizons-2/ragavan-nimble-pilferer", "name": "Ragavan, Nimble Pilferer", "is_foil": "false",
         "price_retail": "44.99", "qty_retail": 4, "condition_values": cv("44.99", 3, "38.24", 1, "33.74", 0)},
        {"id": 2, "scryfall_id": "rag-en-mh2", "url": "mtg/modern-horizons-2/ragavan-nimble-pilferer-foil", "name": "Ragavan, Nimble Pilferer", "is_foil": "true",
         "price_retail": "69.99", "qty_retail": 1, "condition_values": cv("69.99", 1, "55.99", 0)},
        {"id": 3, "scryfall_id": "saga-en", "url": "mtg/modern-horizons-2/urzas-saga", "name": "Urza's Saga", "is_foil": "false",
         "price_retail": "32.99", "qty_retail": 12, "condition_values": cv("32.99", 9, "28.04", 2, "24.74", 1)}]}
    open(os.path.join(folder, "ck.json"), "w").write("<html><head></head><body>" + json.dumps(ck) + "</body></html>")
    v = lambda sid, lang, cond, fin, cents, qty, url: {"product_type": "mtg_single", "scryfall_id": sid, "language_id": lang, "condition_id": cond,
                                                     "finish_id": fin, "low_price": cents, "available_quantity": qty, "url": url}
    RU, SU, DU = "https://manapool.com/card/mh2/138/ragavan-nimble-pilferer", "https://manapool.com/card/mh2/259/urzas-saga", "https://manapool.com/card/gol/1/deathrite-shaman"
    mp = [v("rag-en-mh2", "EN", "LP", "NF", 3550, 2, RU), v("rag-en-mh2", "EN", "NM", "NF", 3900, 4, RU), v("rag-en-mh2", "JA", "NM", "NF", 4200, 1, RU),
          v("rag-en-mh2", "EN", "NM", "FO", 5800, 2, RU), v("rag-en-mh2", "EN", "NM", "NF", 9900, 0, RU),
          v("saga-en", "EN", "NM", "NF", 3000, 6, SU), v("saga-en", "EN", "LP", "NF", 2850, 3, SU), v("saga-en", "EN", "MP", "NF", 2600, 1, SU),
          v("saga-en", "EN", "HP", "NF", 2100, 1, SU), v("saga-en", "EN", "DMG", "NF", 1500, 1, SU), v("saga-en", "FR", "NM", "NF", 2950, 2, SU),
          v("saga-en", "DE", "LP", "NF", 2700, 1, SU), v("saga-en", "JA", "NM", "NF", 3600, 2, SU),
          v("drs-en", "EN", "NM", "FO", 1250, 3, DU), v("drs-en", "EN", "LP", "FO", 1100, 1, DU)]
    json.dump({"meta": {"as_of": "2026-10-09T03:04:37.862Z"}, "data": mp}, open(os.path.join(folder, "mp.json"), "w"))

def cardtrader_files(folder):
    """Saved CardTrader answers: sellers in Europe (and one in the US, left out)."""
    d = os.path.join(folder, "ct"); os.makedirs(d, exist_ok=True)
    A = lambda name, obj: json.dump(obj, open(os.path.join(d, name + ".json"), "w"))
    A("expansions", [{"id": 70, "game_id": 1, "code": "mh2", "name": "Modern Horizons 2"}])
    A("blueprints_export_expansion_id-70", [{"id": 701, "name": "Ragavan", "scryfall_id": "rag-en-mh2"}])
    p = lambda i, cents, qty, cond, lang, foil, country: {"id": i, "blueprint_id": 701, "quantity": qty, "price": {"cents": cents, "currency": "EUR"},
        "properties_hash": {"condition": cond, "mtg_language": lang, "mtg_foil": foil}, "user": {"country_code": country}}
    A("marketplace_products_expansion_id-70_foil-false", {"701": [p(1, 2900, 2, "Slightly Played", "en", False, "IT"), p(2, 3300, 1, "Near Mint", "jp", False, "DE"),
                                                                   p(3, 1000, 5, "Near Mint", "en", False, "US")]})
    A("marketplace_products_expansion_id-70_foil-true", {"701": [p(4, 5000, 1, "Mint", "en", True, "ES")]})

def enndal_files(folder):
    """A night's ENNDAL GAMES data (as shop_enndal.py saves it): Ragavan in
    Japanese and English, non-foil and foil; Urza's Saga in English only; a
    product in a set we don't have (matches nothing)."""
    R = "%28MH2-MR%29Ragavan%2C+Nimble+Pilferer%2F%E6%95%8F%E6%8D%B7%E3%81%AA%E3%81%8B%E3%81%99%E3%82%81%E5%8F%96%E3%82%8A%E3%80%81%E3%83%A9%E3%82%AC%E3%83%B4%E3%82%A1%E3%83%B3/product/MH2-MR-0138-JP-NM-{}/"
    S = "%28MH2-RL%29Urza%27s+Saga%2F%E3%82%A6%E3%83%AB%E3%82%B6%E3%81%AE%E3%82%B5%E3%83%BC%E3%82%AC/product/MH2-RL-0259-JP-NM-normal/"
    data = {"version": 1, "updated": "2026-10-08T17:40:00Z", "read_tonight": 1, "sets": 1, "cats": {"1537": {"name": "モダンホライゾン2", "read": "2026-10-08T17:40:00Z", "p": [
        ["mh2", "138", "normal", R.format("normal"), [["JA", "NM", 6980, 2], ["JA", "EX", 5980, 1], ["EN", "NM", 7480, 3]]],
        ["mh2", "138", "foil", R.format("foil"), [["JA", "NM", 12800, 1]]],
        ["mh2", "259", "normal", S, [["EN", "NM", 4280, 5]]],
        ["zzz", "1", "normal", "%28ZZZ-CR%29Nothing%2F%E7%84%A1/product/ZZZ-CR-0001-JP-NM-normal/", [["JA", "NM", 50, 9]]]]}}}
    with gzip.open(os.path.join(folder, "enndal.json.gz"), "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def build_prices(cards, days, name, tmp, quotes=True):
    prev = ""
    for n in range(days):
        k = n + (45 - days)
        day = START + _td(days=k)
        bulk = os.path.join(tmp, f"bulk_{name}_{n}.json")
        open(bulk, "w").write(json.dumps(price_day(cards, k)))
        out = os.path.join(tmp, f"{name}_{n}")
        extra = ["--quotes", "never", "--lows", "never", "--offers", "never"]
        if quotes and n == days - 1:
            mtgjson_files(tmp, day)
            lows_files(tmp)
            offers_files(tmp)
            cardtrader_files(tmp)
            enndal_files(tmp)
            extra = ["--mtgjson-today", os.path.join(tmp, "AllPricesToday.json.xz"), "--mtgjson-ids", os.path.join(tmp, "AllIdentifiers.json.xz"),
                     "--tcgcsv", os.path.join(tmp, "tcgcsv"), "--cardmarket-guide", os.path.join(tmp, "guide.json"),
                     "--ck-pricelist", os.path.join(tmp, "ck.json"), "--manapool-variants", os.path.join(tmp, "mp.json"), "--cardtrader", os.path.join(tmp, "ct"),
                     "--enndal", os.path.join(tmp, "enndal.json.gz")]
        r = subprocess.run([sys.executable, BUILDER, "--out", out, "--previous", prev, "--bulk", bulk, "--date", day.isoformat(),
                            "--min-cards", "1", "--backfill", "never", *extra] + (["--allow-fresh"] if n == 0 else []), capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(r.stdout + r.stderr)
        prev = out
    return prev

if __name__ == "__main__":
    sys.argv = [sys.argv[0]]
    tmp = tempfile.mkdtemp(prefix="pf_")
    cards = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "fixture_cards.json")))
    out = build_prices(cards, 45, "full", tmp)
    print(out)

"""Checks the test site: the printings file is served, search by printing works, and a card page's
language buttons come from the file and open another language through Scryfall."""
import gzip, json, urllib.request
from playwright.sync_api import sync_playwright
BASE = "https://staging-warujie.warujie-mtg.workers.dev/"
UA = {"User-Agent": "warujie.jp site check (GitHub Actions)"}
raw = urllib.request.urlopen(urllib.request.Request(BASE + "printings.json.gz", headers=UA)).read()
try: data = json.loads(gzip.decompress(raw))
except OSError: data = json.loads(raw)
print("printings.json.gz:", len(raw), "bytes,", sum(len(v) for v in data["sets"].values()), "printings; mh2/138:", data["sets"]["mh2"]["138"])
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1280, "height": 900})
    errs, calls = [], []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("request", lambda r: calls.append(r.url))
    page.goto(BASE); page.wait_for_function("typeof dbState !== 'undefined' && dbState === 'ready'", timeout=60000)
    print("fields:", page.evaluate("Object.keys(LOCAL_DB[0]).filter(k => !k.startsWith('_')).join(' ')"))
    for q in ("日本語版 ボーダーレス ドラゴン", "e:mh3", "旧枠 稲妻", "lang:ja is:showcase"):
        page.fill("#heroInput" if page.locator("#heroInput").is_visible() else "#searchInput", q)
        page.press("#heroInput" if page.locator("#heroInput").is_visible() else "#searchInput", "Enter")
        page.wait_for_function("document.querySelector('#resultCount') && document.querySelector('#resultCount').textContent.includes('件')", timeout=30000)
        page.wait_for_timeout(1500)
        print("search", q, "->", page.locator("#resultCount").inner_text(), "|", page.locator("#matchNote").inner_text()[:160].replace("\n", " "),
              "| first:", page.locator("#cardGrid .card-name-main").all_inner_texts()[:4])
    page.screenshot(path="probe_out/site/search.png")
    n0 = len(calls)
    # Ragavan, MH2 #138 in Japanese
    page.goto(BASE + "?card=" + "a1a8c3b4-0f3c-45b5-9d8f-2a4a2d6d31b0")
    page.wait_for_timeout(500)
    rag = page.evaluate("fetch('https://api.scryfall.com/cards/mh2/138/ja').then(r => r.json()).then(c => c.id)")
    page.goto(BASE + "?card=" + rag); page.wait_for_selector("#printSlot .print-lang", timeout=30000); page.wait_for_timeout(1000)
    print("card page buttons:", page.locator("#printSlot .print-lang").all_inner_texts(),
          "| multilingual searches:", sum("include_multilingual" in c for c in calls[n0:]), "| printings file loads:", sum(c.endswith("printings.json.gz") for c in calls[n0:]))
    page.click("#printSlot [data-print=fr]")
    page.wait_for_function("location.search.includes('print=fr')", timeout=30000); page.wait_for_selector("#printSlot [data-print=fr][aria-pressed=true]", timeout=30000)
    page.wait_for_timeout(1000)
    print("after FR:", page.locator(".cp-name").inner_text(), "| buttons:", page.locator("#printSlot .print-lang").all_inner_texts(), "| url:", page.url)
    page.screenshot(path="probe_out/site/card-fr.png")
    arma = page.evaluate("fetch('https://api.scryfall.com/cards/4bb/4/ja').then(r => r.json()).then(c => c.id).catch(() => '')")
    if arma:
        page.goto(BASE + "?card=" + arma); page.wait_for_selector("#printSlot .print-lang", timeout=30000); page.wait_for_timeout(1000)
        print("4bb buttons:", page.locator("#printSlot .print-lang").all_inner_texts())
        page.click("#printSlot [data-print=en]")
        page.wait_for_function("location.search.includes('print=en')", timeout=30000); page.wait_for_timeout(1500)
        print("4bb -> EN:", page.locator(".cp-name").inner_text(), page.locator(".cp-meta").inner_text()[:120].replace("\n", " "))
    print("errors:", errs)
    b.close()

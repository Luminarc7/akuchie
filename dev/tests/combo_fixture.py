"""Commander Spellbook-style combo file for the end-to-end test, built into
the price fixture's c/ folder with build_combos.py itself."""
import gzip, json, os, subprocess, sys

def variant(i, cards, pop, results=("Infinite colorless mana",), templates=(), legal=("commander", "legacy", "vintage"),
            pre="Ashnod's Altar and Pack Rat on the battlefield.", desc="Sacrifice a Rat to Ashnod's Altar.\nRepeat."):
    return {"id": f"{i}-combo", "status": "OK", "identity": "B", "popularity": pop,
            "uses": [{"card": {"name": n, "oracleId": o}, "quantity": 1, "zoneLocations": ["B"]} for n, o in cards],
            "requires": [{"template": {"name": t}, "quantity": 1} for t in templates],
            "produces": [{"feature": {"name": r, "status": "U"}, "quantity": 1} for r in results],
            "manaNeeded": "{B}", "legalities": {f: True for f in legal},
            "notablePrerequisites": pre, "easyPrerequisites": "",
            "description": desc}

ALTAR, RAT, ELF, RAG = ("Ashnod's Altar", "altar-oracle"), ("Pack Rat", "rat-oracle"), ("Llanowar Elves", "elf-oracle"), ("Ragavan, Nimble Pilferer", "rag-oracle")

def build(dest):
    vs = [variant(1, [ALTAR, RAT], 5000, results=("Infinite colorless mana", "Infinite death triggers"),
                  desc="Activate Ashnod's Altar by sacrificing Pack Rat, adding {C}{C}.\nPack Rat dies, triggering Ashnod's Altar.\nRepeat."),
          variant(2, [ELF, ALTAR], 120, templates=("Persist Creature",), results=("Infinite colorless mana", "Some brand new result"),
                  pre="", desc="Frobnicate the Llanowar Elves with a weird new trick.\nRepeat."),
          variant(3, [RAG, ("Unknown Combo Piece", "zz-unknown")], 30)]
    vs += [variant(10 + i, [ALTAR, (f"Filler Card {i}", f"altar-filler-{i}")], 6 - i, results=("Infinite mana",)) for i in range(6)]
    src = os.path.join(os.path.dirname(dest.rstrip("/")), "variants.json.gz")
    with gzip.open(src, "wt") as f:
        json.dump({"timestamp": "2026-10-08T00:00:00Z", "variants": vs}, f)
    r = subprocess.run([sys.executable, os.path.join(os.environ.get("WARUJIE_PRICES", os.path.join(os.path.dirname(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))), "warujie-prices")), "build_combos.py"), "--out", dest, "--source", src, "--today", "2026-10-09"],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)

#!/usr/bin/env python3
"""Checks that the docs still match the code: every name the docs write in `backticks`
(a function, a constant, an element id, a file, a section of index.html, a saved setting)
must still exist. A renamed function or a deleted file then shows up at once.

usage: python3 dev/check_docs.py            (in the repository folder)

It reads docs/*.md. Names are looked up in this repository and, when it is cloned next to
this one, the other repository (Warujie <-> warujie-prices), because the docs mention both.
It can't tell whether a description is still right: reread the paragraphs around what you
changed. The same script is in both repositories; keep them alike.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT = os.path.dirname(REPO)
SIBLINGS = [os.path.join(PARENT, n) for n in ("Warujie", "warujie-prices")
            if os.path.isdir(os.path.join(PARENT, n)) and os.path.realpath(os.path.join(PARENT, n)) != os.path.realpath(REPO)]
ROOTS = [REPO] + SIBLINGS
CODE_EXT = (".html", ".js", ".mjs", ".py", ".yml", ".yaml", ".jsonc", ".webmanifest")
SKIP_DIRS = {".git", "node_modules", "docs", "fixtures", "__pycache__"}
FILE_EXT = (".py", ".js", ".mjs", ".json", ".gz", ".br", ".html", ".md", ".yml", ".jsonc", ".webmanifest", ".png", ".txt")


def walk(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            yield os.path.join(d, f)


ALL_FILES = [p for r in ROOTS for p in walk(r)]
BASENAMES = {os.path.basename(p) for p in ALL_FILES}
CODE = "\n".join(open(p, encoding="utf-8", errors="replace").read()
                 for p in ALL_FILES if p.endswith(CODE_EXT) and os.path.basename(p) != "preview.html")
INDEX = os.path.join(REPO, "index.html")
INDEX_TEXT = open(INDEX, encoding="utf-8").read() if os.path.exists(INDEX) else ""
MARKERS = [m.strip() for m in re.findall(r"// ---- ([^\n]*?)(?:-{3,}|$)", INDEX_TEXT, re.M)]

IDENT = re.compile(r"^[A-Za-z_$][\w$]*$")


def defined(name):
    n = re.escape(name)
    return re.search(rf"(?:function\s+{n}\b|def\s+{n}\b|(?:const|let|var)\s+{n}\b|\b{n}\s*[:=]|\b{n}\b\s*\()", CODE) is not None


def path_ok(span):
    s = span[3:] if span.startswith("../") else span
    s = s.rstrip("/")
    if any(os.path.exists(os.path.join(r, s)) for r in [os.path.join(REPO, "docs")] + ROOTS):
        return True
    base = os.path.basename(s)
    return base in BASENAMES or s in CODE or base in CODE


def check_span(span, doc, in_section_table):
    """None when fine or not something to check, else why it failed."""
    if in_section_table:
        text = span.replace("…", "").strip()
        text = re.sub(r"\s*\(.*\)$", "", text)
        if any(m.startswith(text) for m in MARKERS):
            return None
        return "no '// ---- " + text + "' section in index.html"
    if re.search(r"[<>*{}|\s]|://", span) and not re.match(r"^[A-Za-z_$][\w$]*\(.*\)$", span):
        return None                                   # placeholders, globs, commands, URLs
    m = re.match(r"^([A-Za-z_$][\w$]*)\(.*\)$", span)
    if m:
        return None if defined(m.group(1)) else "function not found"
    if span.startswith("#") and IDENT.match(span[1:].replace("-", "_")):
        return None if f'id="{span[1:]}"' in INDEX_TEXT or f"id=\"{span[1:]}\"" in CODE else "element id not found"
    if span.startswith("akuchie-"):
        return None if span in CODE else "saved-setting key not found"
    if span.endswith(FILE_EXT) or ("/" in span and not span.startswith("/")):
        return None if path_ok(span) else "file not found"
    if IDENT.match(span) and (re.match(r"^[A-Z][A-Z0-9_]{2,}$", span) or re.search(r"[a-z][A-Z]", span)):
        return None if re.search(rf"\b{re.escape(span)}\b", CODE) else "name not found"
    return None


def main():
    docs_dir = os.path.join(REPO, "docs")
    problems, checked = [], 0
    for name in sorted(os.listdir(docs_dir)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(docs_dir, name)
        in_fence = False
        section_tables = False
        for no, line in enumerate(open(path, encoding="utf-8"), 1):
            if line.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if line.startswith("#"):
                # in index-html.md, the tables under "The script, section by section" name sections
                section_tables = name == "index-html.md" and (line.startswith("### ") and section_tables or "section by section" in line)
                if name == "index-html.md" and line.startswith("## ") and "section by section" not in line:
                    section_tables = False
            cells = line.split("|")
            first_cell = cells[1] if line.startswith("|") and len(cells) > 2 else ""
            for span in re.findall(r"`([^`\n]+)`", line):
                in_table = section_tables and f"`{span}`" in first_cell and first_cell.strip().startswith("`")
                checked += 1
                why = check_span(span, name, in_table)
                if why:
                    problems.append(f"docs/{name}:{no}: `{span}`: {why}")
    for p in problems:
        print(p)
    print(f"{checked - len(problems)}/{checked} names in docs/ found in the code"
          + ("" if SIBLINGS else " (the other repository isn't cloned next to this one: its names count as missing)"))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()

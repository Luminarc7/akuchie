#!/bin/bash
B=https://staging-warujie.warujie-mtg.workers.dev
for p in / /CLAUDE.md /dev/README.md /dev/tests/e2e.py /tools/make_preview.py /index.html; do
  curl -sS -o /dev/null -w "$p %{http_code}\n" "$B$p"
done > probe_out/handover_check.txt 2>&1

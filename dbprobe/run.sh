set -x
mkdir -p probe_out/db2
cd dbprobe
mkdir -p tools && cp build_ja_database.py check_database.py update_database.py fix_names.py name_readings.py name_fixes_ja.json tools/
cp old_ja_cards.json.gz ja_cards.json.gz
pip install -q sudachipy sudachidict_full pykakasi
time python3 tools/update_database.py --work ../probe_out/db2/new --note ../probe_out/db2/note.md; echo "update exit $?"
python3 db_diff.py old_ja_cards.json.gz ../probe_out/db2/new/ja_cards.json.gz > ../probe_out/db2/diff.txt 2>&1
python3 - <<'PY' > ../probe_out/db2/printings_stats.txt 2>&1
import gzip, json, collections
d = json.load(gzip.open('../probe_out/db2/new/printings.json.gz'))
n = sum(len(v) for v in d['sets'].values()); print('sets', len(d['sets']), 'printings', n)
langs = collections.Counter(l.split('@')[0] for v in d['sets'].values() for p in v.values() for l in p[0].split())
print(langs.most_common())
print('twins', sum(1 for v in d['sets'].values() for p in v.values() if '@' in p[0]))
print(d['sets'].get('4ed', {}).get('4'), d['sets'].get('m10', {}).get('146'), d['sets'].get('mh3', {}).get('1'))
import os; print('size', os.path.getsize('../probe_out/db2/new/printings.json.gz'))
PY
ls -la ../probe_out/db2/new

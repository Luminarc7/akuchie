set -x
mkdir -p probe_out/db3
cd dbprobe
python3 b23/build_ja_database.py > ../probe_out/db3/b23_log.txt 2>&1 || true

ls -la . ../probe_out/db3
python3 ids.py

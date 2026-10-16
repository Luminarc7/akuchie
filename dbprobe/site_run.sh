set -x
mkdir -p probe_out/site
pip install -q playwright==1.56.0 && python3 -m playwright install --with-deps chromium > /dev/null 2>&1
python3 dbprobe/site_check.py

"""Contact sheets of Japanese card pictures, for reading the Japanese names Scryfall's
data lacks. usage: face_sheets.py all.jsonl.gz targets.json outdir
targets.json: [{"key": ..., "oracle": ..., "id": optional printing id}]"""
import gzip, json, sys, io, os, time, urllib.request
from PIL import Image, ImageDraw, ImageFont

bulk, targets_path, outdir = sys.argv[1:4]
targets = json.load(open(targets_path))
want_oracle = {t['oracle'] for t in targets}
want_id = {t.get('id') for t in targets if t.get('id')}
ja = {}          # oracle -> list of Japanese printings
for line in gzip.open(bulk):
    if not line.strip():
        continue
    c = json.loads(line)
    if c.get('lang') != 'ja':
        continue
    o = c.get('oracle_id') or ((c.get('card_faces') or [{}])[0].get('oracle_id'))
    if o in want_oracle:
        ja.setdefault(o, []).append(c)
os.makedirs(outdir, exist_ok=True)


def pick(t):
    cs = ja.get(t['oracle'], [])
    cs = [c for c in cs if c.get('image_status') in ('highres_scan', 'lowres')] or cs
    for c in cs:
        if c['id'] == t.get('id'):
            return c
    cs.sort(key=lambda c: (c.get('image_status') != 'highres_scan', c.get('promo', False), c.get('released_at', '')))
    return cs[0] if cs else None


def img_url(c):
    u = c.get('image_uris') or ((c.get('card_faces') or [{}])[0].get('image_uris')) or {}
    return u.get('png') or u.get('large')


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Warujie/1.0 (+https://warujie.jp)'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


font = ImageFont.load_default(size=26) if hasattr(ImageFont, 'load_default') else None
info = []
strips = []
for n, t in enumerate(targets):
    c = pick(t)
    if not c or not img_url(c):
        info.append({'n': n, 'key': t['key'], 'none': True})
        continue
    try:
        im = Image.open(io.BytesIO(get(img_url(c)))).convert('RGB')
    except Exception as e:
        info.append({'n': n, 'key': t['key'], 'error': str(e)})
        continue
    time.sleep(0.12)
    W, H = im.size
    layout = c.get('layout')
    faces = c.get('card_faces') or []
    info.append({'n': n, 'key': t['key'], 'id': c['id'], 'set': c['set'], 'cn': c['collector_number'], 'layout': layout,
                 'image_status': c.get('image_status'),
                 'printed_name': c.get('printed_name'), 'faces': [{'name': f.get('name'), 'printed_name': f.get('printed_name'),
                                                                   'printed_text': f.get('printed_text'), 'printed_type_line': f.get('printed_type_line')} for f in faces],
                 'printed_text': c.get('printed_text')})
    if layout in ('split',) or (W > H):
        body = im.rotate(-90, expand=True) if W < H else im
        body = body.resize((1100, int(body.size[1] * 1100 / body.size[0])))
        parts = [body]
    else:
        top = im.crop((0, 0, W, int(H * 0.13))).resize((1100, int(H * 0.13 * 1100 / W)))
        low = im.crop((0, int(H * 0.52), int(W * 0.62), int(H * 0.96)))
        low = low.resize((1100, int(low.size[1] * 1100 / low.size[0])))
        parts = [top] + ([low] if len(faces) > 1 else [])
    label_h = 40
    h = label_h + sum(p.size[1] for p in parts) + 10
    strip = Image.new('RGB', (1100, h), 'white')
    d = ImageDraw.Draw(strip)
    d.text((8, 6), f"#{n}  {t['key']}  [{c['set']} {c['collector_number']} {layout}]", fill='black', font=font)
    y = label_h
    for p in parts:
        strip.paste(p, (0, y)); y += p.size[1]
    strips.append(strip)

# sheets of about 2400 px high
sheet, sh, k = [], 0, 0
def flush():
    global sheet, sh, k
    if not sheet:
        return
    out = Image.new('RGB', (1100, sum(s.size[1] for s in sheet) + 8 * len(sheet)), (60, 60, 60))
    y = 0
    for s in sheet:
        out.paste(s, (0, y)); y += s.size[1] + 8
    out.save(os.path.join(outdir, f'sheet{k:02d}.jpg'), quality=82)
    k += 1; sheet, sh = [], 0
for s in strips:
    if sh + s.size[1] > 2400:
        flush()
    sheet.append(s); sh += s.size[1]
flush()
json.dump(info, open(os.path.join(outdir, 'info.json'), 'w'), ensure_ascii=False, indent=1)
print('sheets', k, 'cards', len(strips), file=sys.stderr)

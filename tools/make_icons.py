# Makes icons/*.png (the app icon): python3 tools/make_icons.py, then copy build output into icons/ under a new -vN name.
# App icons: 悪 centred by its ink (not the font's em box), on the site's dark tile.
from playwright.sync_api import sync_playwright
JS = """([size, scale]) => {
  const c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d');
  g.fillStyle = '#121214'; g.fillRect(0, 0, size, size);
  const fs = Math.round(size * scale);
  g.font = `900 ${fs}px 'Noto Serif CJK JP'`;
  g.textBaseline = 'alphabetic'; g.textAlign = 'left';
  const m = g.measureText('悪');
  const inkW = m.actualBoundingBoxLeft + m.actualBoundingBoxRight, inkH = m.actualBoundingBoxAscent + m.actualBoundingBoxDescent;
  const x = (size - inkW) / 2 + m.actualBoundingBoxLeft, y = (size - inkH) / 2 + m.actualBoundingBoxAscent;
  const ink = () => { const d = g.getImageData(0, 0, size, size).data; let x0 = size, x1 = 0, y0 = size, y1 = 0;
    for (let j = 0; j < size; j++) for (let i = 0; i < size; i++) { const k = (j * size + i) * 4; if (d[k + 1] > 60) { x0 = Math.min(x0, i); x1 = Math.max(x1, i); y0 = Math.min(y0, j); y1 = Math.max(y1, j); } }
    return [x0, y0, x1, y1]; };
  const paint = (px, py) => { g.fillStyle = '#121214'; g.fillRect(0, 0, size, size); g.fillStyle = '#b5e655'; g.fillText('悪', px, py); };
  paint(x, y);
  let [a0, b0, a1, b1] = ink();
  // second pass: move by what the measured ink is off centre
  const dx = size / 2 - (a0 + a1 + 1) / 2, dy = size / 2 - (b0 + b1 + 1) / 2;
  paint(x + dx, y + dy);
  const [x0, y0, x1, y1] = ink();
  return { url: c.toDataURL('image/png'), box: [x0, y0, x1, y1], centre: [(x0 + x1 + 1) / 2, (y0 + y1 + 1) / 2], size };
}"""
import base64
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.set_content("<p style=\"font-family:'Noto Serif CJK JP';font-weight:900\">悪</p>"); pg.wait_for_timeout(300)
    for name, size, scale in [("icon-192", 192, 0.66), ("icon-512", 512, 0.66), ("apple-touch-icon", 180, 0.64), ("maskable-512", 512, 0.52)]:
        r = pg.evaluate(JS, [size, scale])
        open(f"icons/{name}.png", "wb").write(base64.b64decode(r["url"].split(",")[1]))
        print(name, "ink", r["box"], "centre", r["centre"], "of", size)
    b.close()

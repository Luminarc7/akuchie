# Makes icons/*.png, the app icon (home screen, installed app, browser tab):
#   python3 tools/make_icons.py
# The design is the owner's favicon (2026-10-17): 悪 inside a glowing ring on a dark tile, green
# for warujie.jp and pink for the test sites (worker.js shows the pink one there: TEST_ICONS).
# The favicon file only has 48 px and smaller, so this draws the same design at full size
# instead of blowing the small picture up. Needs the font "Noto Sans CJK JP" (Bold) and
# Playwright and Pillow. When the design changes, raise VERSION so phones fetch the new files, and
# change the file names in manifest*.webmanifest, index.html's <head>, sw.js and worker.js.
import base64
import colorsys
import io
from PIL import Image
from playwright.sync_api import sync_playwright

VERSION = "v3"

# Colours read off the favicon (48 px): tile glow from the centre out, ring and letter light at
# the top and deeper green at the bottom, each with a soft glow.
GREEN = {
    "tile": [(0.0, (50, 76, 33)), (0.42, (33, 55, 24)), (0.6, (24, 42, 18)), (0.72, (14, 27, 12)), (1.0, (6, 11, 6))],
    "ring": [(222, 236, 160), (104, 160, 42)],
    "char": [(200, 226, 132), (142, 196, 64)],
    "glow": (150, 220, 80),
}


def pink(rgb):
    """The same colour moved to pink: same lightness and saturation, hue 330°."""
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    r, g, b = colorsys.hls_to_rgb(330 / 360, l, min(1.0, s * 1.05))
    return tuple(round(c * 255) for c in (r, g, b))


PINK = {
    "tile": [(at, pink(c)) for at, c in GREEN["tile"]],
    "ring": [pink(c) for c in GREEN["ring"]],
    "char": [pink(c) for c in GREEN["char"]],
    "glow": pink(GREEN["glow"]),
}

JS = """([size, art, p]) => {
  // art: how much of the tile the design fills (1, or less for the maskable icon's safe zone)
  const c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d');
  const rgb = (a, al = 1) => `rgba(${a[0]},${a[1]},${a[2]},${al})`;
  const S = size, mid = S / 2, R = S / 2 * art;
  const tile = g.createRadialGradient(mid, mid, 0, mid, mid, S / 2 * Math.SQRT2);
  for (const [at, col] of p.tile) tile.addColorStop(at, rgb(col));
  g.fillStyle = tile; g.fillRect(0, 0, S, S);
  const down = (a, b, top, bottom) => { const l = g.createLinearGradient(0, top, 0, bottom); l.addColorStop(0, rgb(a)); l.addColorStop(1, rgb(b)); return l; };
  // the ring, drawn twice: a wide soft glow, then the line itself
  const ringR = R * 0.84, ringW = Math.max(1, S * 0.026 * art);
  g.save();
  g.shadowColor = rgb(p.glow, 0.75); g.shadowBlur = S * 0.05 * art;
  g.strokeStyle = down(p.ring[0], p.ring[1], mid - ringR, mid + ringR); g.lineWidth = ringW;
  g.beginPath(); g.arc(mid, mid, ringR, 0, Math.PI * 2); g.stroke(); g.stroke();
  g.restore();
  // the letter, its ink 0.5 of the design wide, centred by its ink
  g.font = `700 100px 'Noto Sans CJK JP'`;
  const m0 = g.measureText('悪');
  const fs = 100 * (R * 2 * 0.5) / (m0.actualBoundingBoxLeft + m0.actualBoundingBoxRight);
  g.font = `700 ${fs}px 'Noto Sans CJK JP'`;
  const m = g.measureText('悪');
  const w = m.actualBoundingBoxLeft + m.actualBoundingBoxRight, h = m.actualBoundingBoxAscent + m.actualBoundingBoxDescent;
  const x = mid - w / 2 + m.actualBoundingBoxLeft, y = mid - h / 2 + m.actualBoundingBoxAscent - R * 0.02;
  g.save();
  g.shadowColor = rgb(p.glow, 0.55); g.shadowBlur = S * 0.035 * art;
  g.fillStyle = down(p.char[0], p.char[1], y - m.actualBoundingBoxAscent, y + m.actualBoundingBoxDescent);
  g.fillText('悪', x, y);
  g.restore();
  return c.toDataURL('image/png');
}"""

# name, size, how much of the tile the design fills
SIZES = [("icon-192", 192, 1.0), ("icon-512", 512, 1.0), ("apple-touch-icon", 180, 1.0), ("maskable-512", 512, 0.8)]

if __name__ == "__main__":
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        pg.set_content("<p style=\"font-family:'Noto Sans CJK JP';font-weight:700\">悪</p>"); pg.wait_for_timeout(300)
        for colours, suffix in [(GREEN, ""), (PINK, "-test")]:
            for name, size, art in SIZES:
                url = pg.evaluate(JS, [size, art, colours])
                path = f"icons/{name}-{VERSION}{suffix}.png"
                im = Image.open(io.BytesIO(base64.b64decode(url.split(",")[1]))).convert("RGB")
                # 256 colours, dithered: looks the same, a quarter of the size
                im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(path, optimize=True)
                print(path)
        b.close()

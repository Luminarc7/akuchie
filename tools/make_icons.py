# Makes icons/*.png, the app icon (home screen, installed app, browser tab):
#   python3 tools/make_icons.py
# The picture is the owner's own artwork (tools/icon_source.png, 2026-10-17: a brush-drawn 悪
# inside a rough glowing ring on a dark tile), cut to a square and scaled to each size. It makes
# a green set for warujie.jp and a pink copy (the same picture with its colours turned to pink)
# for the test sites (worker.js shows the pink one there: TEST_ICONS). Needs Pillow.
# When the picture changes, raise VERSION so phones fetch the new files, and change the file
# names in manifest*.webmanifest, index.html's <head> and sw.js.
from PIL import Image, ImageDraw, ImageFilter

VERSION = "v4"
SOURCE = "tools/icon_source.png"
PINK_HUE = 234   # 330° on Pillow's 0-255 hue scale


def square(img):
    """The artwork as a 512 px square with the ring in the middle.

    The source is a screenshot: thin grey bands top and bottom, and a few pixels cut off the
    left and right. Drop the bands, centre on the ring's bright pixels and fill the missing
    edge by repeating the outermost (dark, plain) pixels."""
    img = img.convert("RGB")
    w, h = img.size
    grey = lambda y: all(abs(c - 32) <= 2 for c in img.getpixel((w // 2, y)))
    top = next(y for y in range(h) if not grey(y))
    bottom = next(y for y in range(h - 1, -1, -1) if not grey(y)) + 1
    img = img.crop((0, top, w, bottom))
    w, h = img.size
    lit = img.convert("L").point(lambda v: 255 if v > 110 else 0).getbbox()
    cx, cy = (lit[0] + lit[2]) / 2, (lit[1] + lit[3]) / 2
    side = max(w, h)
    out = Image.new("RGB", (side, side))
    ox, oy = round(side / 2 - cx), round(side / 2 - cy)
    out.paste(img, (ox, oy))
    for x in range(side):   # repeat the edge columns and rows into the gaps
        src = min(max(x - ox, 0), w - 1)
        if not 0 <= x - ox < w:
            out.paste(img.crop((src, 0, src + 1, h)), (x, oy))
    for y in range(side):
        if not 0 <= y - oy < h:
            src = oy if y < oy else oy + h - 1
            out.paste(out.crop((0, src, side, src + 1)), (0, y))
    return out.resize((512, 512), Image.LANCZOS)


def maskable(art):
    """Android crops the icon to a circle or squircle inside the middle 80 %: the ring is shrunk
    to fit, on a blurred copy of the same dark tile so the edge doesn't show."""
    back = art.filter(ImageFilter.GaussianBlur(40))
    small = art.resize((436, 436), Image.LANCZOS)
    fade = Image.new("L", (436, 436), 0)
    ImageDraw.Draw(fade).ellipse((10, 10, 426, 426), fill=255)
    back.paste(small, (38, 38), fade.filter(ImageFilter.GaussianBlur(8)))
    return back


def pink(img):
    h, s, v = img.convert("HSV").split()
    h = h.point(lambda _: PINK_HUE)
    return Image.merge("HSV", (h, s, v)).convert("RGB")


def save(img, path):
    # 256 colours, dithered: looks the same, a quarter of the size
    img.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(path, optimize=True)
    print(path)


if __name__ == "__main__":
    green = square(Image.open(SOURCE))
    for art, suffix in [(green, ""), (pink(green), "-test")]:
        save(art.resize((192, 192), Image.LANCZOS), f"icons/icon-192-{VERSION}{suffix}.png")
        save(art, f"icons/icon-512-{VERSION}{suffix}.png")
        save(art.resize((180, 180), Image.LANCZOS), f"icons/apple-touch-icon-{VERSION}{suffix}.png")
        save(maskable(art), f"icons/maskable-512-{VERSION}{suffix}.png")

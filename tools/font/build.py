#!/usr/bin/env python3
"""Build SimPuma's pixel font, Pride, and the title's painted wordmark, and
write both into index.html (the @font and @logo blocks).

    python tools/font/build.py                      # rewrites the blocks in index.html
    python tools/font/build.py --ttf pride.ttf      # writes the font file instead
    python tools/font/build.py --from C:/Windows/Fonts/tahomabd.ttf --px 12

Pride is a bold humanist sans (Verdana Bold by default, 12 px) rasterised
with no anti-aliasing, so every glyph is a crisp bitmap, then rebuilt as a
TTF whose outlines are those pixels: 16 bitmap pixels to the em, so
font-size 32px draws each at 2 by 2, as the map at zoom 2 draws its tiles.
Proportional, mixed case, ASCII and a few symbols.

The wordmark is the same face at 44 px, painted: a vertical gradient with an
ordered dither, a lit edge top and left, a shade bottom and right, a dark
outline and a drop shadow. Two PNGs, "Sim" in cream and "Puma" in amber, as
data URIs in CSS custom properties the title's h1 and the share card read.

Needs Pillow and fontTools, and the source font on this machine.
"""
import base64, io, re, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
U = 100                      # font units per bitmap pixel
EM = 16                      # bitmap pixels to the em
CHARS = [chr(c) for c in range(32, 127)] + list("·×→←↑↓…’“”–—£€°")

def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

def raster(font, text, pad=2):
    """A 1-bit bitmap of text: (rows of 0/1, advance, left bearing)."""
    adv = font.getlength(text)
    w = int(adv) + pad * 2 + 4
    im = Image.new("L", (w, max(EM, int(font.size * 1.5)) + 4), 0)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    d.text((pad, 0), text, font=font, fill=255)
    px = im.load()
    rows = [[1 if px[x, y] > 127 else 0 for x in range(w)] for y in range(im.height)]
    return rows, adv, pad

def build_font(path, px):
    font = ImageFont.truetype(path, px)
    ascent, descent = font.getmetrics()
    order = [".notdef"] + ["g%d" % i for i in range(len(CHARS))]
    fb = FontBuilder(EM * U, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({ord(ch): "g%d" % i for i, ch in enumerate(CHARS)})
    glyphs, metrics = {}, {}
    def outline(rows, pad):
        pen = TTGlyphPen(None)
        for y, row in enumerate(rows):
            x = 0
            while x < len(row):
                if row[x]:
                    x0 = x
                    while x < len(row) and row[x]:
                        x += 1
                    top = (ascent - y) * U
                    pen.moveTo(((x0 - pad) * U, top - U)); pen.lineTo(((x0 - pad) * U, top))
                    pen.lineTo(((x - pad) * U, top)); pen.lineTo(((x - pad) * U, top - U)); pen.closePath()
                else:
                    x += 1
        return pen.glyph()
    for i, ch in enumerate(CHARS):
        rows, adv, pad = raster(font, ch)
        glyphs["g%d" % i] = outline(rows, pad)
        metrics["g%d" % i] = (round(adv) * U, 0)
    rows, adv, pad = raster(font, "?")
    glyphs[".notdef"] = outline(rows, pad); metrics[".notdef"] = (round(adv) * U, 0)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ascent * U, descent=-descent * U)
    fb.setupNameTable({"familyName": "Pride", "styleName": "Regular", "fullName": "Pride", "psName": "Pride-Regular", "version": "Version 2.0",
                       "copyright": "Copyright 2026 Matthew \"Shan\" Romanek. SimPuma's pixel font, rasterised from %s at %d px." % (Path(path).name, px)})
    fb.setupOS2(sTypoAscender=ascent * U, sTypoDescender=-descent * U, sTypoLineGap=0, usWinAscent=ascent * U, usWinDescent=descent * U)
    fb.setupPost()
    buf = io.BytesIO()
    fb.save(buf)
    return buf.getvalue()

def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))

def paint(path, text, px, top, bottom, lite, shade):
    """The wordmark: the text's bitmap, painted. Returns a PNG's bytes and its size."""
    font = ImageFont.truetype(path, px)
    rows, adv, pad = raster(font, text, pad=4)
    h, w = len(rows), len(rows[0])
    ys = [y for y in range(h) if any(rows[y])]
    xs = [x for x in range(w) if any(rows[y][x] for y in range(h))]
    y0, y1, x0, x1 = min(ys), max(ys), min(xs), max(xs)
    M = lambda x, y: 0 <= x < w and 0 <= y < h and rows[y][x]
    out = Image.new("RGBA", (x1 - x0 + 6, y1 - y0 + 6), (0, 0, 0, 0))
    o = out.load()
    OUTLINE, SHADOW = (13, 15, 20, 255), (0, 0, 0, 120)
    bands = 6
    for y in range(y0 - 1, y1 + 2):
        for x in range(x0 - 1, x1 + 2):
            ox, oy = x - x0 + 1, y - y0 + 1
            if M(x, y):
                t = (y - y0) / max(1, y1 - y0)
                b = t * bands
                k = int(b) + (1 if (b - int(b)) > 0.5 and (x + y) % 2 else 0)
                col = lerp(top, bottom, min(1, k / bands))
                if not M(x, y - 1) or not M(x - 1, y):
                    col = lite
                elif not M(x, y + 1) or not M(x + 1, y):
                    col = shade
                o[ox, oy] = col + (255,)
            elif any(M(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                o[ox, oy] = OUTLINE
    # the drop shadow, two pixels down and right, under everything
    for y in range(out.height):
        for x in range(out.width):
            if o[x, y][3] and x + 2 < out.width and y + 2 < out.height and not o[x + 2, y + 2][3]:
                o[x + 2, y + 2] = SHADOW
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue(), out.size

def main():
    path = arg("--from", "C:/Windows/Fonts/verdanab.ttf")
    px = int(arg("--px", 12))
    data = build_font(path, px)
    if "--ttf" in sys.argv:
        Path(arg("--ttf", "pride.ttf")).write_bytes(data)
        print("wrote the font:", len(data), "bytes,", len(CHARS), "glyphs")
        return
    page = ROOT / "index.html"
    html = page.read_text(encoding="utf-8")
    uri = "data:font/ttf;base64," + base64.b64encode(data).decode()
    css = '@font-face{font-family:Pride;src:url(%s) format("truetype");font-display:block}' % uri
    block = re.compile(r"(/\* @font-begin \*/\n)[\s\S]*?(\n/\* @font-end \*/)")
    if not block.search(html):
        sys.exit("index.html has no @font block")
    html = block.sub(lambda m: m.group(1) + css + m.group(2), html)
    # the wordmark: "Sim" in cream, "Puma" in amber, as the title's two lines
    sim, (sw, sh) = paint(path, "Sim", 44, (255, 250, 236), (214, 198, 160), (255, 255, 255), (150, 132, 100))
    puma, (pw, ph) = paint(path, "Puma", 44, (255, 220, 110), (222, 136, 0), (255, 243, 190), (160, 90, 0))
    logo = ":root{--k-logo-sim:url(data:image/png;base64,%s);--k-logo-sim-w:%d;--k-logo-sim-h:%d;--k-logo-puma:url(data:image/png;base64,%s);--k-logo-puma-w:%d;--k-logo-puma-h:%d}" % (
        base64.b64encode(sim).decode(), sw, sh, base64.b64encode(puma).decode(), pw, ph)
    block = re.compile(r"(/\* @logo-begin \*/\n)[\s\S]*?(\n/\* @logo-end \*/)")
    if not block.search(html):
        sys.exit("index.html has no @logo block")
    html = block.sub(lambda m: m.group(1) + logo + m.group(2), html)
    page.write_text(html, encoding="utf-8", newline="\n")
    print("wrote the @font block (%d bytes of TTF, %d glyphs) and the @logo block (Sim %dx%d, Puma %dx%d)" % (len(data), len(CHARS), sw, sh, pw, ph))

if __name__ == "__main__":
    main()

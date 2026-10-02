"""The Global Five - daily briefing image generator.

Usage:  python3 tools/make_briefing.py tools/briefing_configs/<date>.json [outdir]

Renders one 1080x1350 PNG per region (world.png, asia.png, ...) in the house
style: gradient header, five alternating story cards with numbered badges and
round icons, and a sources footer. Colors come from tools/briefing_palettes.json.
Needs: Pillow, cairosvg. Icon names are shared with make_reel.py.
"""
import io, json, os, sys
from PIL import Image, ImageDraw, ImageFont
import cairosvg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_reel import ICONS, hexc, mix, lum  # noqa: E402

W, H = 1080, 1350
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
def F(p, s): return ImageFont.truetype(p, s)

HEADER_H = 176
ROW_TOP, ROW_H = 182, 206
CARD_H, CARD_W = 184, 440
LEFT_X, RIGHT_X = 40, 600
CENTER_X = 542
ICON_R = 70


def icon_png(name, size, color="#fff"):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}" '
           f'fill="none" stroke="{color}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert("RGBA")


def wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines


def background(p):
    tl, tr, bl, br = (hexc(p[k]) for k in ("tl", "tr", "bl", "br"))
    hl, hr = hexc(p["hdr_l"]), hexc(p["hdr_r"])
    img = Image.new("RGB", (W, H)); px = img.load()
    for y in range(H):
        if y < HEADER_H:
            a, b = hl, hr
        else:
            t = (y - HEADER_H) / (H - HEADER_H)
            a, b = mix(tl, bl, t), mix(tr, br, t)
        for x in range(W):
            px[x, y] = mix(a, b, x / (W - 1))
    return img.convert("RGBA")


def dashed(d, xy0, xy1, fill, width=3, dash=10, gap=7):
    (x0, y0), (x1, y1) = xy0, xy1
    if y0 == y1:
        x = x0
        while x < x1:
            d.line([(x, y0), (min(x + dash, x1), y0)], fill=fill, width=width); x += dash + gap
    else:
        y = y0
        while y < y1:
            d.line([(x0, y), (x0, min(y + dash, y1))], fill=fill, width=width); y += dash + gap


def card(story, accent, bar_left):
    img = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, CARD_W - 1, CARD_H - 1], 14, fill=accent + (255,))
    if bar_left: d.rounded_rectangle([8, 0, CARD_W - 1, CARD_H - 1], 14, fill=(248, 247, 251, 255)); d.rectangle([8, 0, 30, CARD_H - 1], fill=(248, 247, 251, 255))
    else: d.rounded_rectangle([0, 0, CARD_W - 9, CARD_H - 1], 14, fill=(248, 247, 251, 255)); d.rectangle([CARD_W - 30, 0, CARD_W - 9, CARD_H - 1], fill=(248, 247, 251, 255))
    x0 = 24 if bar_left else 16
    maxw = CARD_W - 40
    for hs, bs, ss in ((21, 15, 12), (20, 14, 12), (19, 13.5, 11), (18, 13, 11)):
        fh, fb, fs = F(FB, hs), F(FR, int(bs)), F(FB, ss)
        hl, bl, sl = wrap(d, story["h"], fh, maxw), wrap(d, story["s"], fb, maxw), wrap(d, story["src"], fs, maxw)
        lh_h, lh_b, lh_s = int(hs * 1.2), int(bs * 1.3), int(ss * 1.25)
        total = len(hl) * lh_h + 6 + len(bl) * lh_b + 6 + len(sl) * lh_s
        if total <= CARD_H - 28 and len(hl) <= 2: break
    y = (CARD_H - total) // 2
    for l in hl: d.text((x0, y), l, font=fh, fill=(17, 24, 34)); y += lh_h
    y += 6
    for l in bl: d.text((x0, y), l, font=fb, fill=(52, 60, 72)); y += lh_b
    y += 6
    for l in sl: d.text((x0, y), l, font=fs, fill=(78, 90, 104)); y += lh_s
    return img


def icon_disc(name, c1, c2):
    s = 2 * ICON_R + 12
    disc = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    g = Image.new("RGBA", (s, s)); gd = ImageDraw.Draw(g)
    for k in range(2 * s):  # diagonal gradient
        gd.line([(k, 0), (0, k)], fill=mix(c1, c2, k / (2 * s)) + (255,), width=2)
    m = Image.new("L", (s, s), 0); ImageDraw.Draw(m).ellipse([6, 6, s - 6, s - 6], fill=255)
    disc.paste(g, (0, 0), m)
    ImageDraw.Draw(disc).ellipse([6, 6, s - 6, s - 6], outline=(255, 255, 255, 255), width=5)
    glyph = icon_png(name, 82); disc.alpha_composite(glyph, ((s - 82) // 2, (s - 82) // 2))
    return disc


def badge(n, accent):
    b = Image.new("RGBA", (56, 56), (0, 0, 0, 0)); d = ImageDraw.Draw(b)
    d.ellipse([2, 2, 53, 53], fill=(255, 255, 255, 255), outline=accent + (255,), width=4)
    f = F(FB, 28); t = str(n); w = d.textlength(t, font=f)
    d.text(((56 - w) / 2, 10), t, font=f, fill=accent)
    return b


def render(region, date, pal, out):
    accent = hexc(pal["accent"]); ic1, ic2 = hexc(pal["ic1"]), hexc(pal["ic2"])
    img = background(pal); d = ImageDraw.Draw(img)
    hdr_mid = mix(hexc(pal["hdr_l"]), hexc(pal["hdr_r"]), 0.3)
    fg = (255, 255, 255) if lum(hdr_mid) < 0.4 else (8, 50, 79)
    # header
    kick = "THE GLOBAL FIVE · TOP 5 STORIES"; f = F(FB, 21); x = 45
    for ch in kick: d.text((x, 26), ch, font=f, fill=fg); x += d.textlength(ch, font=f) + 5.2
    tf = F(FB, 62)
    while d.textlength(region["title"], font=tf) > 990: tf = F(FB, tf.size - 2)
    d.text((44, 50), region["title"], font=tf, fill=fg)
    d.text((45, 126), f"Daily Briefing — {date}", font=F(FB, 23), fill=fg)
    # grid lines
    body_mid = mix(hexc(pal["tl"]), hexc(pal["br"]), 0.5)
    line = (255, 255, 255, 170) if lum(body_mid) < 0.45 else (11, 92, 138, 120)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    dashed(od, (CENTER_X, HEADER_H), (CENTER_X, 1222), line)
    for k in range(1, 5): dashed(od, (40, ROW_TOP + k * ROW_H), (1040, ROW_TOP + k * ROW_H), line)
    img.alpha_composite(ov)
    # stories
    for i, s in enumerate(region["stories"]):
        top = ROW_TOP + i * ROW_H; cy = top + ROW_H // 2 - 6
        left = i % 2 == 0
        c = card(s, accent, bar_left=left)
        img.alpha_composite(c, (LEFT_X if left else RIGHT_X, top + 12))
        disc = icon_disc(s["icon"], ic1, ic2)
        ix = 820 if left else 260
        img.alpha_composite(disc, (ix - disc.width // 2, cy - disc.height // 2))
        b = badge(i + 1, accent); img.alpha_composite(b, (580 - 28, cy - 28))
    # footer
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([40, 1228, 1040, 1323], 14, fill=(247, 248, 253))
    fb, fr = F(FB, 13), F(FR, 13)
    text = (f"{region['sources']}. Facts as reported by these outlets on the dates shown; where outlets differ, "
            f"both figures are shown. " + (region.get("note", "") + " " if region.get("note") else "") +
            "Icons are original vector art. ·")
    words = ("Sources: " + text).split(); lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fr) <= 960: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur)
    y = 1240
    for k, l in enumerate(lines):
        x = 58
        if k == 0:
            d.text((x, y), "Sources:", font=fb, fill=(17, 17, 17)); x += d.textlength("Sources: ", font=fb); l = l[len("Sources: "):]
        d.text((x, y), l, font=fr, fill=(40, 46, 56))
        if k == len(lines) - 1: d.text((x + d.textlength(l + " ", font=fr), y), "The Global Five", font=fb, fill=(17, 17, 17))
        y += 17
    img.convert("RGB").save(out, optimize=True)


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1])); outdir = sys.argv[2] if len(sys.argv) > 2 else "."
    pals = json.load(open(os.path.join(HERE, "briefing_palettes.json")))
    for r in cfg["regions"]:
        assert len(r["stories"]) == 5, r["key"]
        for s in r["stories"]: assert s["icon"] in ICONS, s["icon"]
        out = os.path.join(outdir, r["key"] + ".png")
        render(r, cfg["date"], pals[r["key"]], out); print(out)

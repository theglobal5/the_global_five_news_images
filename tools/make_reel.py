"""The Global Five - daily Reel generator.

Usage:  python3 tools/make_reel.py <config.json> <output.mp4>

Renders a vertical 1080x1920 Reel (intro, 5 story cards, outro), composes an
original background music track timed to the story changes, and muxes both.
Needs: ffmpeg, Pillow, numpy, cairosvg (pip install --break-system-packages cairosvg).
See tools/example_world.json for the config format. Icon names: see ICONS.
"""
import io, subprocess, sys, math
from PIL import Image, ImageDraw, ImageFont
import cairosvg

W, H, FPS = 1080, 1920, 30
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
def F(p, s): return ImageFont.truetype(p, s)

ICONS = {
 "globe": '<circle cx="32" cy="32" r="22"/><ellipse cx="32" cy="32" rx="9" ry="22"/><path d="M10 32h44M14 20h36M14 44h36"/>',
 "chip": '<rect x="17" y="17" width="30" height="30" rx="4"/><rect x="25" y="25" width="14" height="14"/><path d="M24 8v9M32 8v9M40 8v9M24 47v9M32 47v9M40 47v9M8 24h9M8 32h9M8 40h9M47 24h9M47 32h9M47 40h9"/>',
 "flag": '<path d="M18 56V10"/><path d="M18 12h30l-7 10 7 10H18"/>',
 "ship": '<path d="M8 38h48l-6 12H14z"/><path d="M20 38V24h22v14M32 24V12h8"/>',
 "speech": '<path d="M10 14h44v28H30l-12 10V42h-8z"/><path d="M20 26h24M20 33h14"/>',
 "shield": '<path d="M32 8l20 8v14c0 12-8 20-20 26C20 50 12 42 12 30V16z"/><path d="M24 32l6 6 11-12"/>',
 "drop": '<path d="M32 8C20 24 14 32 14 40a18 18 0 0 0 36 0c0-8-6-16-18-32z"/><path d="M24 42a8 8 0 0 0 8 8"/>',
 "chart": '<path d="M8 8v48h48"/><path d="M16 42l12-14 10 8 16-20"/><path d="M46 16h8v8"/>',
 "building": '<path d="M10 54h44M16 54V26l16-12 16 12v28M26 54V38h12v16M32 14V6"/>',
 "storm": '<path d="M32 32m-4 0a4 4 0 1 0 8 0a4 4 0 1 0 -8 0"/><path d="M32 28c-2-10 4-18 16-18M36 32c10-2 18 4 18 16M32 36c2 10-4 18-16 18M28 32c-10 2-18-4-18-16"/>',
 "scales": '<path d="M32 10v44M18 54h28M12 20h40"/><path d="M12 20L4 38h16zM52 20l-8 18h16z"/>',
 "bank": '<path d="M6 24L32 8l26 16zM12 28v20M24 28v20M40 28v20M52 28v20M6 54h52"/>',
 "plane": '<path d="M6 34l52-20-18 40-8-16z"/><path d="M32 38l26-24"/>',
 "fire": '<path d="M32 6c2 12 16 18 16 34a16 16 0 0 1-32 0c0-8 4-12 8-16 0 6 3 9 6 9-2-9-2-17 2-27z"/>',
 "people": '<circle cx="32" cy="20" r="8"/><path d="M14 54c0-12 8-18 18-18s18 6 18 18"/><circle cx="12" cy="26" r="5"/><circle cx="52" cy="26" r="5"/>',
 "virus": '<circle cx="32" cy="32" r="12"/><path d="M32 8v10M32 46v10M8 32h10M46 32h10M15 15l7 7M42 42l7 7M49 15l-7 7M22 42l-7 7"/>',
 "vote": '<rect x="10" y="30" width="44" height="24" rx="3"/><path d="M24 30V20M40 30V20"/><path d="M20 12l12 10 12-10M26 42h12"/>',
 "crown": '<path d="M10 46l-2-24 14 12 10-18 10 18 14-12-2 24z"/><path d="M12 54h40"/>',
 "drone": '<rect x="24" y="26" width="16" height="12" rx="3"/><path d="M24 28L10 18M40 28l14-10M24 36L10 46M40 36l14 10"/><circle cx="10" cy="18" r="5"/><circle cx="54" cy="18" r="5"/><circle cx="10" cy="46" r="5"/><circle cx="54" cy="46" r="5"/>',
 "trade": '<path d="M8 22h44M42 12l10 10-10 10M56 42H12M22 32L12 42l10 10"/>',
 "snow": '<path d="M32 6v52M10 19l44 26M10 45l44-26"/><path d="M26 10l6 6 6-6M26 54l6-6 6 6"/>',
 "wave": '<path d="M6 26q6-8 13 0t13 0 13 0 13 0M6 38q6-8 13 0t13 0 13 0 13 0M6 50q6-8 13 0t13 0 13 0 13 0"/>',
}
def icon_img(name, size):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>'
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert("RGBA")

def hexc(h): h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def mix(a, b, t): return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))
def lum(c):
    def ch(v):
        v /= 255; return v/12.92 if v <= 0.03928 else ((v+0.055)/1.055)**2.4
    r, g, b = map(ch, c); return 0.2126*r + 0.7152*g + 0.0722*b

def clamp(x): return max(0.0, min(1.0, x))
def prog(t, a, b): return clamp((t-a)/(b-a))
def ease_out(x): return 1-(1-x)**3
def ease_back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3*(x-1)**3 + c1*(x-1)**2

def with_alpha(layer, a):
    if a >= 0.999: return layer
    l = layer.copy(); l.putalpha(layer.getchannel("A").point(lambda v: int(v*a))); return l
def put(base, layer, cx, cy, a=1.0, s=1.0):
    if a <= 0.01 or s <= 0.01: return
    if abs(s-1) > 0.001:
        layer = layer.resize((max(1, int(layer.width*s)), max(1, int(layer.height*s))), Image.LANCZOS)
    layer = with_alpha(layer, a)
    base.alpha_composite(layer, (int(cx-layer.width/2), int(cy-layer.height/2)))

def wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur+" "+w).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def text_layer(text, font, fill, maxw=None, spacing=1.2, align="center"):
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines = wrap(d, text, font, maxw) if maxw else [text]
    asc, desc = font.getmetrics(); lh = int((asc+desc)*spacing)
    w = int(max(d.textlength(l, font=font) for l in lines)) + 8
    img = Image.new("RGBA", (w, lh*len(lines)+8), (0, 0, 0, 0)); dd = ImageDraw.Draw(img)
    for i, l in enumerate(lines):
        lw = dd.textlength(l, font=font)
        x = (w-lw)/2 if align == "center" else 0
        dd.text((x, i*lh), l, font=font, fill=fill)
    return img

def main(cfg, out, preview=None):
    c1, c2, acc = hexc(cfg["c1"]), hexc(cfg["c2"]), hexc(cfg["accent"])
    # background: top-heavy gradient so text zones stay dark enough
    bg = Image.new("RGB", (W, H)); px = ImageDraw.Draw(bg)
    rows = []
    for y in range(H):
        t = (y/(H-1))**2.0
        c = mix(c1, c2, t); rows.append(c); px.line([(0, y), (W, y)], fill=c)
    bg = bg.convert("RGBA")
    deco = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(deco)
    for (x, y, r) in [(980, 180, 260), (80, 1500, 320), (900, 1250, 140)]:
        dd.ellipse([x-r, y-r, x+r, y+r], outline=(255, 255, 255, 34), width=6)
    for y in range(260, 1700, 44):
        dd.line([(540, y), (540, y+20)], fill=(255, 255, 255, 40), width=4)
    bg.alpha_composite(deco)
    def fg_at(y): return (255, 255, 255, 255) if lum(rows[y]) < 0.35 else (18, 28, 40, 255)

    # intro layers
    kick = text_layer("THE GLOBAL FIVE", F(FB, 44), fg_at(560))
    top5 = text_layer("TOP 5", F(FB, 230), fg_at(760))
    reg = text_layer(cfg["title"], F(FB, 92), fg_at(980), maxw=960)
    date = text_layer(cfg["date"], F(FR, 46), fg_at(1100))
    sub = text_layer("stories you need to know today", F(FR, 40), fg_at(1180))
    # outro layers
    o1 = text_layer("That's today's Top 5", F(FB, 76), fg_at(640), maxw=960)
    o2 = text_layer("Full 10-region roundup on our Page", F(FR, 44), fg_at(760), maxw=940)
    o3c = Image.new("RGBA", (720, 130), (0, 0, 0, 0)); ImageDraw.Draw(o3c).rounded_rectangle([0, 0, 719, 129], 65, fill=(255, 255, 255, 250))
    t3 = text_layer("Follow The Global Five", F(FB, 50), acc + (255,)); o3c.alpha_composite(t3, ((720-t3.width)//2, (130-t3.height)//2 + 4))
    o4 = text_layer("Sources: " + cfg["sources"], F(FR, 30), fg_at(1100), maxw=900)
    o5 = text_layer("New briefing every morning", F(FR, 36), fg_at(1200))

    # story layers
    icon_circle_r = 170
    stories = []
    for i, s in enumerate(cfg["stories"]):
        ic = Image.new("RGBA", (2*icon_circle_r+20, 2*icon_circle_r+20), (0, 0, 0, 0))
        g = Image.new("RGBA", ic.size); gd = ImageDraw.Draw(g)
        for y in range(ic.height): gd.line([(0, y), (ic.width, y)], fill=mix(hexc(cfg["ic1"]), hexc(cfg["ic2"]), y/ic.height)+(255,))
        m = Image.new("L", ic.size, 0); ImageDraw.Draw(m).ellipse([10, 10, ic.width-10, ic.height-10], fill=255)
        ic.paste(g, (0, 0), m)
        ImageDraw.Draw(ic).ellipse([10, 10, ic.width-10, ic.height-10], outline=(255, 255, 255, 255), width=10)
        glyph = icon_img(s["icon"], 210); ic.alpha_composite(glyph, ((ic.width-210)//2, (ic.height-210)//2))
        nb = Image.new("RGBA", (140, 140), (0, 0, 0, 0)); nd = ImageDraw.Draw(nb)
        nd.ellipse([4, 4, 136, 136], fill=(255, 255, 255, 255), outline=acc+(255,), width=8)
        nt = text_layer(str(i+1), F(FB, 76), acc+(255,)); nb.alpha_composite(nt, ((140-nt.width)//2, (140-nt.height)//2 + 2))
        # card
        cw = 940; pad = 50; inner = cw - 2*pad - 14
        hl = text_layer(s["h"], F(FB, 62), (16, 24, 34, 255), maxw=inner, spacing=1.15, align="left")
        sm = text_layer(s["s"], F(FR, 40), (40, 52, 64, 255), maxw=inner, spacing=1.3, align="left")
        src = text_layer(s["src"], F(FB, 30), (84, 98, 112, 255), maxw=inner, align="left")
        ch = pad + hl.height + 26 + sm.height + 26 + src.height + pad
        card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
        cd.rounded_rectangle([0, 0, cw-1, ch-1], 36, fill=(255, 255, 255, 255))
        cd.rounded_rectangle([0, 0, 22, ch-1], 11, fill=acc+(255,))
        cd.rectangle([11, 0, 22, ch-1], fill=acc+(255,))
        stories.append(dict(ic=ic, nb=nb, card=card, hl=hl, sm=sm, src=src, pad=pad, ch=ch))

    kick2 = [text_layer(f"THE GLOBAL FIVE  ·  {cfg['short'].upper()}", F(FB, 36), fg_at(150))]

    INTRO, STORY, OUTRO = 3.0, 4.6, 3.6
    total = INTRO + STORY*len(stories) + OUTRO
    nframes = int(total*FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
                           "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in range(nframes):
        t = f/FPS; fr = bg.copy()
        if t < INTRO:
            out_a = 1 - prog(t, INTRO-0.35, INTRO)
            put(fr, kick, 540, 560 - 30*(1-ease_out(prog(t, 0, .5))), prog(t, 0, .5)*out_a)
            put(fr, top5, 540, 770, prog(t, .15, .5)*out_a, 0.6+0.4*ease_back(prog(t, .15, .75)))
            put(fr, reg, 540, 990 + 40*(1-ease_out(prog(t, .5, 1.0))), prog(t, .5, 1.0)*out_a)
            put(fr, date, 540, 1100, prog(t, .8, 1.3)*out_a)
            put(fr, sub, 540, 1180, prog(t, 1.0, 1.5)*out_a)
        elif t < INTRO + STORY*len(stories):
            k = int((t-INTRO)//STORY); lt = (t-INTRO) - k*STORY; S = stories[k]
            put(fr, kick2[0], 540, 150)
            # progress segments
            ov = Image.new("RGBA", (W, 240), (0,0,0,0)); dr = ImageDraw.Draw(ov); segw, gap, x0 = 150, 14, (W - (5*150+4*14))//2
            col = fg_at(215)
            for j in range(5):
                x = x0 + j*(segw+gap)
                dr.rounded_rectangle([x, 208, x+segw, 222], 7, fill=col[:3]+(80,))
                fillw = segw if j < k else (segw*clamp(lt/STORY) if j == k else 0)
                if fillw > 2: dr.rounded_rectangle([x, 208, x+fillw, 222], 7, fill=col)
            fr.alpha_composite(ov)
            out_a = 1 - prog(lt, STORY-0.35, STORY)
            sx = -60*prog(lt, STORY-0.35, STORY)
            put(fr, S["ic"], 540+sx, 520, prog(lt, 0, .35)*out_a, 0.5+0.5*ease_back(prog(t-INTRO-k*STORY, 0, .55)))
            put(fr, S["nb"], 380+sx, 380, prog(lt, .15, .45)*out_a, 0.3+0.7*ease_back(prog(lt, .15, .6)))
            cy = 760 + S["ch"]/2 + 110*(1-ease_out(prog(lt, .3, .9)))
            ca = prog(lt, .3, .8)*out_a
            card = S["card"].copy()
            pad = S["pad"]; y = pad
            card.alpha_composite(with_alpha(S["hl"], prog(lt, .45, .9)), (pad+14, y)); y += S["hl"].height + 26
            card.alpha_composite(with_alpha(S["sm"], prog(lt, .8, 1.3)), (pad+14, y)); y += S["sm"].height + 26
            card.alpha_composite(with_alpha(S["src"], prog(lt, 1.1, 1.5)), (pad+14, y))
            put(fr, card, 540+sx, cy, ca)
        else:
            lt = t - INTRO - STORY*len(stories)
            put(fr, o1, 540, 640 + 30*(1-ease_out(prog(lt, 0, .5))), prog(lt, 0, .5))
            put(fr, o2, 540, 760, prog(lt, .3, .8))
            put(fr, o3c, 540, 920, prog(lt, .6, 1.0), 0.7+0.3*ease_back(prog(lt, .6, 1.1)))
            put(fr, o4, 540, 1100, prog(lt, 1.0, 1.5))
            put(fr, o5, 540, 1200, prog(lt, 1.2, 1.7))
        ff.stdin.write(fr.convert("RGB").tobytes())
        if preview and f == int((INTRO + 1.6)*FPS): fr.convert("RGB").save(preview)
    ff.stdin.close(); ff.wait()
    return total



if __name__ == "__main__":
    import json, os, tempfile
    cfg = json.load(open(sys.argv[1])); out = sys.argv[2]
    assert len(cfg["stories"]) == 5, "exactly 5 stories required"
    for s in cfg["stories"]:
        assert s["icon"] in ICONS, f"unknown icon {s['icon']}; use one of {sorted(ICONS)}"
    tmp = tempfile.mkdtemp()
    silent, music = os.path.join(tmp, "silent.mp4"), os.path.join(tmp, "music.wav")
    total = main(cfg, silent, preview=out.replace(".mp4", "_preview.png"))
    here = os.path.dirname(os.path.abspath(__file__))
    subprocess.run([sys.executable, os.path.join(here, "make_music.py"), f"{total:.2f}", music], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", silent, "-i", music, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    print(out, round(total, 1), "s")

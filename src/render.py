"""Rendert Slides (PNG 1080x1350) und Reel-Cover (1080x1920).
Hintergrund: Foto (photos/<id>/NN.jpg) > Höhenlinien (background_art: topo) > einfarbig."""
import os
import shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from common import *


def font(rel, size, fallback="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
    for c in (path(rel) if rel else None, fallback):
        if c and os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def wrap(draw, text, fnt, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if draw.textlength(t, font=fnt) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + ([cur] if cur else [])


def hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def spaced(dr, xy, text, fnt, fill, gap=5):
    x, y = xy
    for ch in text:
        dr.text((x, y), ch, font=fnt, fill=fill); x += dr.textlength(ch, font=fnt) + gap


def find_photo(pid, idx):
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = path("photos", pid, f"{idx:02d}.{ext}")
        if os.path.exists(p):
            return p


def topo_strip(seed, width, height, levels=16):
    """Zusammenhängendes Höhenlinien-Bild (Alpha 0-1), damit Linien über Slides hinweg weiterlaufen."""
    rng = np.random.default_rng(seed)
    F = np.zeros((height, width), dtype=np.float32)
    for cell, amp in ((700, 1.0), (330, 0.5), (160, 0.22)):
        gh, gw = height // cell + 3, width // cell + 3
        g = Image.fromarray(rng.random((gh, gw)).astype("float32"), mode="F")
        big = g.resize((gw * cell, gh * cell), Image.BICUBIC)
        F += amp * np.asarray(big)[:height, :width]
    F = (F - F.min()) / (F.max() - F.min() + 1e-9)
    L = F * levels
    gy, gx = np.gradient(L); gr = np.hypot(gx, gy) + 1e-4
    frac = L - np.floor(L)
    dist = np.minimum(frac, 1 - frac) / gr
    minor = np.clip(1.3 - dist, 0, 1)
    L5 = L / 4; f5 = L5 - np.floor(L5)
    major = np.clip(1.6 - np.minimum(f5, 1 - f5) / (gr / 4), 0, 1)
    return np.clip(0.12 * minor + 0.25 * major, 0, 1)


def background(d, pid, idx, strip, H, W):
    ph = find_photo(pid, idx)
    if ph:
        img = ImageOps.fit(Image.open(ph).convert("RGB"), (W, H))
        shade = Image.new("L", (1, H))
        for y in range(H):
            shade.putpixel((0, y), int(255 * d["photo_overlay"] * (0.35 + 0.65 * y / H)))
        return Image.composite(Image.new("RGB", (W, H), d["background"]), img, shade.resize((W, H))), True
    base = np.zeros((H, W, 3), dtype=np.float32) + np.array(hex2rgb(d["background"]), dtype=np.float32)
    if strip is not None:
        a = strip[:, (idx - 1) * W: idx * W][..., None]
        base = base * (1 - a) + np.array(hex2rgb(d["text"]), dtype=np.float32) * a
    return Image.fromarray(base.astype("uint8")), False


def header(img, dr, d, W, M, counter=None, top=None):
    y0 = M if top is None else top
    f_small = font(d["font_body"], 24)
    wp = path(d["wordmark"]) if d.get("wordmark") else None
    if wp and os.path.exists(wp):
        lg = Image.open(wp).convert("RGBA"); lh = 38
        lg = lg.resize((int(lg.width * lh / lg.height), lh), Image.LANCZOS)
        img.paste(lg, (M, y0 - 6), lg)
    else:
        dr.text((M, y0), d["handle"].upper(), font=f_small, fill=d["accent"])
    if counter:
        dr.text((W - M - dr.textlength(counter, font=f_small), y0), counter, font=f_small, fill=d["accent"])
    dr.line([(M, y0 + 56), (W - M, y0 + 56)], fill=d["accent"], width=1)


def render_slide(pid, slide, idx, total, out, strip=None):
    d = cfg()["design"]
    W, H, M = d["width"], d["height"], 96
    img, has_photo = background(d, pid, idx, strip, H, W)
    dr = ImageDraw.Draw(img)
    f_title = font(d["font_title"], 112 if idx == 1 else 84)
    f_body = font(d["font_body"], 38)
    f_small = font(d["font_body"], 24)
    header(img, dr, d, W, M, f"{idx:02d} / {total:02d}")
    t_lines = wrap(dr, slide["title"], f_title, W - 2 * M)
    b_lines = wrap(dr, slide.get("body", ""), f_body, W - 2 * M - 120)
    th = len(t_lines) * (f_title.size + 8)
    bh = len(b_lines) * (f_body.size + 16)
    block = th + (80 + bh if b_lines else 0)
    last = idx == total and total > 1
    bottom_limit = H - M - (150 if last else 40)
    y = bottom_limit - block if (has_photo or idx == 1) else 330
    if y + block > bottom_limit + 1:
        print(f"WARNUNG: Text zu lang in {pid} Slide {idx}")
    for ln in t_lines:
        dr.text((M, y), ln, font=f_title, fill=d["text"]); y += f_title.size + 8
    if b_lines:
        y += 28
        dr.line([(M, y), (M + 64, y)], fill=d["accent"], width=2); y += 28
        for ln in b_lines:
            dr.text((M, y), ln, font=f_body, fill=d["text"]); y += f_body.size + 16
    if last:
        spaced(dr, (M, H - M - 70), d.get("tagline", "").upper(), f_small, d["text"], gap=4)
        dr.text((M, H - M - 28), d["handle"], font=f_small, fill=d["accent"])
    img.save(out, "PNG")


def render_cover(pid, title, out):
    """Reel-Cover 1080x1920, Text im Mittelbereich (Feed-Raster schneidet oben/unten ab)."""
    d = cfg()["design"]; W, H, M = 1080, 1920, 96
    strip = topo_strip(abs(hash(pid)) % 10000, W, H)
    base = np.zeros((H, W, 3), dtype=np.float32) + np.array(hex2rgb(d["background"]), dtype=np.float32)
    a = strip[..., None]
    base = base * (1 - a) + np.array(hex2rgb(d["text"]), dtype=np.float32) * a
    img = Image.fromarray(base.astype("uint8")); dr = ImageDraw.Draw(img)
    f_t = font(d["font_title"], 130); f_s = font(d["font_body"], 26)
    header(img, dr, d, W, M, top=360)
    lines = wrap(dr, title, f_t, W - 2 * M)
    y = H // 2 - (len(lines) * (f_t.size + 8)) // 2 + 40
    for ln in lines:
        dr.text((M, y), ln, font=f_t, fill=d["text"]); y += f_t.size + 8
    spaced(dr, (M, y + 40), "REEL", f_s, d["accent"], gap=8)
    img.save(out, "PNG")


def run():
    d = cfg()["design"]
    failed = []
    for r in load_calendar():
        if r["status"] not in ("draft", "approved"):
            continue
        out = path("media", r["id"])
        if os.path.isdir(out) and os.listdir(out):
            continue
        try:
            content = load_content(r["id"])
            os.makedirs(out, exist_ok=True)
            if r["format"] == "reel":
                render_cover(r["id"], content.get("cover_title", r["topic"]), os.path.join(out, "cover.png"))
                print(f"Cover gerendert: {r['id']}"); continue
            slides = content["slides"]
            if not slides:
                raise ValueError("Entwurf enthält keine Slides")
            strip = None
            if d.get("background_art") == "topo":
                strip = topo_strip(int(r["id"][1:] or 1) * 7919, d["width"] * len(slides), d["height"])
            for i, s in enumerate(slides, 1):
                render_slide(r["id"], s, i, len(slides), os.path.join(out, f"{i:02d}.png"), strip)
            print(f"Gerendert: {r['id']} ({len(slides)} Slides)")
        except Exception as e:                       # ein kaputter Entwurf blockiert nicht die anderen
            shutil.rmtree(out, ignore_errors=True)   # unvollständige Ausgabe entfernen, nächster Lauf versucht es erneut
            failed.append(r["id"])
            print(f"::warning::Rendern von {r['id']} fehlgeschlagen: {type(e).__name__}: {e}")
    if failed:
        print(f"Nicht gerendert: {', '.join(failed)}")


if __name__ == "__main__":
    run()

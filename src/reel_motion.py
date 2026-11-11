"""Erzeugt ein 20-Sek.-Motion-Graphic-Reel (1080x1920, 30 fps) aus content/<id>.motion.json.
  python src/reel_motion.py p003  ->  media/p003/reel.mp4
Kein Footage: Linien-Icons, Höhenlinien, Typografie. Musik in Instagram hinzufügen (Lizenz beachten)."""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageChops
from common import *
from render import topo_strip, font, hex2rgb, wrap

W, H, FPS = 1080, 1920, 30
SC_START, SC_LEN, HOOK_LEN = 2.5, 3.0, 2.5


from functools import lru_cache
_probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))


@lru_cache(maxsize=None)
def _font(rel, size):
    return font(rel, size)


@lru_cache(maxsize=None)
def fit_font(rel, size, txt, maxw=888):
    while size > 40 and _probe.textlength(txt, font=_font(rel, size)) > maxw:
        size -= 6
    return _font(rel, size)


def ease(x):
    x = min(max(x, 0), 1); return 1 - (1 - x) ** 3


def icon(name, col):
    S, lw = 1200, 12                       # 2x Supersampling
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = col + (255,)
    def line(pts, w=lw):
        d.line(pts, fill=c, width=w, joint="curve")
        for p in (pts[0], pts[-1]): d.ellipse((p[0]-w/2, p[1]-w/2, p[0]+w/2, p[1]+w/2), fill=c)
    if name == "tent":
        line([(160,960),(600,240),(1040,960),(160,960)]); line([(600,420),(470,960)]); line([(600,420),(730,960)])
        line([(60,960),(1140,960)])
    elif name == "bag":
        d.rounded_rectangle((260,160,940,1040), radius=300, outline=c, width=lw)
        line([(600,300),(600,980)])
        for y in (480,640,800): line([(330,y),(540,y)]); line([(660,y),(870,y)])
    elif name == "stove":
        d.rounded_rectangle((330,420,870,700), radius=40, outline=c, width=lw)
        line([(330,500),(230,500)]); line([(870,500),(970,500)])
        line([(420,700),(380,820),(820,820),(780,700)]); line([(380,820),(380,860)]); line([(820,820),(820,860)])
        for x in (470,600,730):
            d.arc((x-45,900,x+45,1040), 200, 340, fill=c, width=lw)
        for x in (500,690): d.arc((x-40,230,x+40,380), 90, 270, fill=c, width=lw-2)
    elif name == "lamp":
        d.ellipse((350,350,850,850), outline=c, width=lw); d.ellipse((480,480,720,720), outline=c, width=lw)
        d.arc((100,150,1100,1050), 205, 335, fill=c, width=lw)
        for a in ((1000,560,1120,520),(1000,620,1140,620),(1000,680,1120,720)): line([a[:2],a[2:]])
    elif name == "feather":
        import math
        A, B, w = (250, 980), (950, 220), 190
        dx, dy = B[0]-A[0], B[1]-A[1]; L = math.hypot(dx, dy); nx, ny = -dy/L, dx/L
        top, bot = [], []
        for i in range(0, 41):
            t = i/40; k = w*math.sin(math.pi*t)**0.8
            cx, cy = A[0]+dx*t, A[1]+dy*t
            top.append((cx+nx*k, cy+ny*k)); bot.append((cx-nx*k, cy-ny*k))
        line(top + bot[::-1] + [top[0]]); line([(A[0]-90, A[1]+90), B])
        for t in (0.3, 0.45, 0.6, 0.75):
            cx, cy = A[0]+dx*t, A[1]+dy*t; line([(cx, cy), (cx+nx*120+dx/L*70, cy+ny*120+dy/L*70)])
    elif name == "shield":
        line([(600,180),(980,320),(960,620),(800,860),(600,1010),(400,860),(240,620),(220,320),(600,180)])
        line([(420,600),(550,730),(790,470)])
    elif name == "scale":
        line([(600,300),(600,960)]); line([(380,960),(820,960)]); line([(260,400),(940,400)])
        d.ellipse((565,210,635,280), outline=c, width=lw)
        for cx in (260, 940):
            line([(cx,400),(cx-110,650)]); line([(cx,400),(cx+110,650)])
            d.arc((cx-150,590,cx+150,780), 0, 180, fill=c, width=lw)
    elif name == "none":
        pass
    elif name == "camera":
        d.rounded_rectangle((160,380,1040,900), radius=70, outline=c, width=lw)
        d.rectangle((440,270,760,380), outline=c, width=lw)
        d.ellipse((410,430,790,810), outline=c, width=lw); d.ellipse((510,530,690,710), outline=c, width=lw)
        d.ellipse((900,450,940,490), fill=c)
    return im.resize((600, 600), Image.LANCZOS)


def alpha_mul(im, a):
    im = im.copy(); al = im.getchannel("A").point(lambda v: int(v * a)); im.putalpha(al); return im


def main(pid):
    d = cfg()["design"]; spec = json.load(open(path("content", f"{pid}.motion.json"), encoding="utf-8"))
    n = len(spec["scenes"]); total = HOOK_LEN + n * SC_LEN + 2.5; frames = int(total * FPS)
    bg_col, txt, acc = hex2rgb(d["background"]), hex2rgb(d["text"]), hex2rgb(d["accent"])
    strip = topo_strip(4242, W, H + 500)
    base = np.zeros((H + 500, W, 3), dtype=np.float32) + np.array(bg_col, dtype=np.float32)
    a = strip[..., None]; base = base * (1 - a) + np.array(txt, dtype=np.float32) * a
    base = base.astype("uint8")
    f_t, f_h, f_b, f_n = font(d["font_title"], 150), font(d["font_title"], 170), font(d["font_body"], 42), font(d["font_body"], 30)
    icons = {s["icon"]: icon(s["icon"], txt) for s in spec["scenes"]}
    wm = Image.open(path(d["wordmark"])).convert("RGBA"); wm = wm.resize((520, int(wm.height * 520 / wm.width)), Image.LANCZOS)
    os.makedirs(path("media", pid), exist_ok=True); out = path("media", pid, "reel.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17",
                           "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    def text(layer, s, f, xy, a, center=True, fill=txt):
        dr = ImageDraw.Draw(layer); f = fit_font(f.path, f.size, s); w = dr.textlength(s, font=f)
        x = xy[0] - w / 2 if center else xy[0]
        dr.text((x, xy[1]), s, font=f, fill=fill + (int(255 * a),))
    for i in range(frames):
        t = i / FPS
        oy = int(t / total * 500)                           # langsame Drift des Höhenlinien-Hintergrunds
        frame = Image.fromarray(base[oy:oy + H]).convert("RGBA")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if t < HOOK_LEN:                                    # Hook
            fo = min(1, (HOOK_LEN - t) / 0.35)
            a1, a2 = ease(t / 0.5) * fo, ease((t - 0.7) / 0.5) * fo
            L.alpha_composite(alpha_mul(wm, a1), ((W - wm.width) // 2, 640))
            text(L, spec["hook"][0], f_h, (W / 2, 800 + 30 * (1 - ease(t / 0.6))), a1)
            text(L, spec["hook"][1], f_h, (W / 2, 1000 + 30 * (1 - ease((t - 0.7) / 0.6))), a2, fill=acc if False else txt)
        elif t < HOOK_LEN + n * SC_LEN:                     # Szenen
            k = int((t - HOOK_LEN) // SC_LEN); lt = (t - HOOK_LEN) - k * SC_LEN; sc = spec["scenes"][k]
            fo = min(1, (SC_LEN - lt) / 0.35)
            ai, at, ab = ease(lt / 0.5) * fo, ease((lt - 0.15) / 0.5) * fo, ease((lt - 0.3) / 0.5) * fo
            dr = ImageDraw.Draw(L)
            segw = (W - 2 * 108 - 4 * 16) / n
            for j in range(n):                              # Fortschritt (5 Segmente)
                x0 = 108 + j * (segw + 16)
                fill = (txt + (255,)) if j < k else (acc + (110,))
                dr.rectangle((x0, 310, x0 + segw, 316), fill=fill)
                if j == k: dr.rectangle((x0, 310, x0 + segw * min(1, lt / SC_LEN), 316), fill=txt + (255,))
            text(L, sc["no"], f_n, (W / 2, 520), ai, fill=acc)
            L.alpha_composite(alpha_mul(icons[sc["icon"]], ai), ((W - 600) // 2, 600 + int(40 * (1 - ease(lt / 0.6)))))
            text(L, sc["title"], f_t, (W / 2, 1260 + 24 * (1 - ease((lt - 0.15) / 0.6))), at)
            text(L, sc["sub"], f_b, (W / 2, 1450), ab, fill=acc)
        else:                                               # Outro
            lt = t - (HOOK_LEN + n * SC_LEN)
            a1, a2, a3 = ease(lt / 0.5), ease((lt - 0.4) / 0.5), ease((lt - 1.0) / 0.5)
            text(L, spec["outro"][0], f_h, (W / 2, 720), a1)
            text(L, spec["outro"][1], f_b, (W / 2, 960), a2, fill=acc)
            L.alpha_composite(alpha_mul(wm, a3), ((W - wm.width) // 2, 1160))
            text(L, d.get("tagline", "").upper(), f_n, (W / 2, 1290), a3, fill=acc)
        frame.alpha_composite(L); ff.stdin.write(frame.convert("RGB").tobytes())
    ff.stdin.close(); ff.wait(); print("Video:", out, f"({total:.1f}s)")


def run_auto():
    """Erzeugt fehlende Reel-Videos für Reels der nächsten Tage und trägt die video_url ein."""
    from datetime import timedelta
    rows = load_calendar(); changed = False
    horizon = now() + timedelta(days=cfg().get("render_days_ahead", 14))
    base = cfg()["media_base_url"].rstrip("/")
    for r in rows:
        pid = r["id"]
        if r["format"] != "reel" or r["status"] not in ("draft", "approved") or parse_dt(r["publish_at"]) > horizon:
            continue
        if not os.path.exists(path("content", f"{pid}.motion.json")):
            continue
        try:
            if not os.path.exists(path("media", pid, "reel.mp4")):
                main(pid)
            if not r["video_url"]:
                r["video_url"] = f"{base}/media/{pid}/reel.mp4"; changed = True
        except Exception as e:
            print(f"::warning::Reel-Video {pid} fehlgeschlagen: {type(e).__name__}: {e}")
    if changed:
        save_calendar(rows)


if __name__ == "__main__":
    run_auto() if sys.argv[1] == "--auto" else main(sys.argv[1])

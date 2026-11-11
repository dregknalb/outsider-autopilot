"""Veröffentlicht fällige, FREIGEGEBENE Posts über die Instagram Graph API.
Benötigte Umgebungsvariablen: IG_USER_ID, IG_ACCESS_TOKEN
  python src/publish.py [--dry-run]
"""
import os, sys, time, requests
from common import *

DRY = "--dry-run" in sys.argv


def api(method, endpoint, **params):
    c = cfg()
    url = f"https://graph.facebook.com/{c['graph_api_version']}/{endpoint}"
    params["access_token"] = os.environ.get("IG_ACCESS_TOKEN", "")
    r = requests.request(method, url, params=params, timeout=60)
    if not r.ok:
        raise RuntimeError(f"Graph API Fehler {r.status_code}: {r.text}")
    return r.json()


def wait_ready(cid, tries=30):
    for _ in range(tries):
        s = api("GET", cid, fields="status_code").get("status_code")
        if s == "FINISHED":
            return
        if s == "ERROR":
            raise RuntimeError("Container-Verarbeitung fehlgeschlagen")
        time.sleep(5)
    raise RuntimeError("Container-Timeout")


def url_ready(u):
    for _ in range(12):
        if requests.head(u, timeout=20).status_code == 200:
            return True
        time.sleep(10)
    return False


def caption_of(content):
    tags = " ".join(content.get("hashtags", []))
    prefix = "Werbung\n\n" if content.get("werbung") else ""
    return f"{prefix}{content['caption'].strip()}\n\n{tags}".strip()


def publish_row(r):
    uid, c = os.environ["IG_USER_ID"], cfg()
    content, base = load_content(r["id"]), c["media_base_url"].rstrip("/")
    cap = caption_of(content)
    if r["format"] == "reel":
        if not r["video_url"]:
            raise RuntimeError("Reel ohne video_url")
        extra = {}
        if os.path.exists(path("media", r["id"], "cover.png")):
            extra["cover_url"] = f"{base}/media/{r['id']}/cover.png"
        cont = api("POST", f"{uid}/media", media_type="REELS", video_url=r["video_url"],
                   caption=cap, share_to_feed="true", **extra)["id"]
        wait_ready(cont)
    else:
        files = sorted(f for f in os.listdir(path("media", r["id"]))
                       if f.lower().endswith((".png", ".jpg", ".jpeg")))   # nur Bilder, keine Markierungsdateien
        if not files:
            raise RuntimeError("Keine Bilder im Ordner media/" + r["id"])
        urls = [f"{base}/media/{r['id']}/{f}" for f in files]
        for u in urls:
            if not url_ready(u):
                raise RuntimeError(f"Bild nicht öffentlich erreichbar: {u}")
        if len(urls) == 1:
            cont = api("POST", f"{uid}/media", image_url=urls[0], caption=cap)["id"]
        else:
            kids = [api("POST", f"{uid}/media", image_url=u, is_carousel_item="true")["id"] for u in urls[:10]]
            cont = api("POST", f"{uid}/media", media_type="CAROUSEL", children=",".join(kids), caption=cap)["id"]
        wait_ready(cont)
    return api("POST", f"{uid}/media_publish", creation_id=cont)["id"]


def run():
    rows, n_today, limit = load_calendar(), 0, cfg()["max_posts_per_day"]
    for r in rows:
        if r["status"] == "published" and parse_dt(r["publish_at"]).date() == now().date():
            n_today += 1
    for r in rows:
        if r["status"] != "approved" or parse_dt(r["publish_at"]) > now() or n_today >= limit:
            continue
        if DRY:
            print(f"[dry-run] würde veröffentlichen: {r['id']} – {r['topic']}")
            continue
        try:
            r["media_id"] = publish_row(r)
            r["status"] = "published"
            n_today += 1
            print(f"Veröffentlicht: {r['id']} -> {r['media_id']}")
        except Exception as e:
            r["status"] = "failed"
            print(f"FEHLER {r['id']}: {e}")
    if not DRY:
        save_calendar(rows)


if __name__ == "__main__":
    run()

"""Erstellt für jeden neuen Entwurf (status=draft, Termin in den nächsten N Tagen) ein GitHub-Ticket
mit Vorschau. Freigabe: im Ticket `ok` kommentieren (verarbeitet src/approve.py)."""
import json, os, requests
from datetime import timedelta
from common import *

ISSUES = path("issues.json")


def gh(method, url, **kw):
    if os.environ.get("DRY"):
        print("DRY", method, url, json.dumps(kw.get("json", {}), ensure_ascii=False)[:2000])
        class R:  # Platzhalter-Antwort
            def json(self): return {"number": 99}
        return R()
    r = requests.request(method, f"https://api.github.com{url}", timeout=30, **kw,
                         headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                                  "Accept": "application/vnd.github+json"})
    r.raise_for_status(); return r


def body_for(r, content, base):
    pid = r["id"]; folder = path("media", pid)
    files = sorted(f for f in os.listdir(folder) if f.endswith(".png")) if os.path.isdir(folder) else []
    imgs = " ".join(f'<img src="{base}/media/{pid}/{f}" width="200">' for f in files)
    ad = " · ⚠️ Werbung" if content.get("werbung") else ""
    parts = [f"**{r['pillar']} · {r['format']} · geplant für {r['publish_at']} Uhr**{ad}", imgs,
             "**Caption**", "```\n" + content["caption"].strip() + "\n\n" + " ".join(content.get("hashtags", [])) + "\n```",
             f"**Alt-Text:** {content.get('alt_text', '')}"]
    if content.get("photo_hint"):
        parts.append(f"**Fotoidee:** {content['photo_hint']}")
    if r["format"] == "reel":
        parts.append("**Reel-Skript**\n```\n" + (content.get("reel_script") or "") + "\n```")
        parts.append("⚠️ Reel: Vor der Freigabe die Video-Adresse in `content_calendar.csv` (Spalte `video_url`) eintragen.")
    parts.append("---\n**Freigeben:** Kommentiere `ok`  ·  **Zurückhalten:** Kommentiere `stopp`\n"
                 f"Caption ändern? Vorher `content/{pid}.json` bearbeiten.")
    return "\n\n".join(p for p in parts if p)


def main():
    c = cfg(); base = c["media_base_url"].rstrip("/"); repo = os.environ.get("GITHUB_REPOSITORY", "owner/repo")
    done = json.load(open(ISSUES, encoding="utf-8")) if os.path.exists(ISSUES) else {}
    limit = now() + timedelta(days=c.get("notify_days_ahead", 7))
    for r in sorted(load_calendar(), key=lambda x: x["publish_at"]):
        if r["status"] != "draft" or r["id"] in done or parse_dt(r["publish_at"]) > limit:
            continue
        try:
            content = load_content(r["id"])
        except FileNotFoundError:
            continue
        folder = path("media", r["id"])
        if not (os.path.isdir(folder) and any(f.endswith(".png") for f in os.listdir(folder))):
            print(f"Noch keine Bilder für {r['id']}, Ticket folgt beim nächsten Lauf")
            continue
        title = f"Freigabe {r['id']} – {r['topic'][:70]}"
        num = gh("POST", f"/repos/{repo}/issues", json={"title": title, "body": body_for(r, content, base),
                                                         "labels": ["freigabe"]}).json()["number"]
        done[r["id"]] = num
        with open(ISSUES, "w", encoding="utf-8") as f:
            json.dump(done, f, indent=2)
        print(f"Ticket #{num} für {r['id']}")


if __name__ == "__main__":
    main()

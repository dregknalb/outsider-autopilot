"""Verarbeitet einen Kommentar im Freigabe-Ticket: `ok` = freigeben, `stopp` = zurückhalten.
Erwartet die Umgebungsvariablen ISSUE_NUMBER, ISSUE_TITLE, COMMENT, GITHUB_TOKEN, GITHUB_REPOSITORY."""
import os, re
from notify import gh
from common import *

OK = {"ok", "freigeben", "freigabe", "ja", "approve", "/ok", "✅", "👍"}
STOP = {"stopp", "stop", "nein", "halt", "/stopp"}


def reply(text, close=False):
    repo, num = os.environ.get("GITHUB_REPOSITORY", "owner/repo"), os.environ["ISSUE_NUMBER"]
    gh("POST", f"/repos/{repo}/issues/{num}/comments", json={"body": text})
    if close:
        gh("PATCH", f"/repos/{repo}/issues/{num}", json={"state": "closed"})


def main():
    m = re.match(r"Freigabe (p\d+)", os.environ["ISSUE_TITLE"])
    if not m:
        return
    pid = m.group(1)
    cmd = os.environ["COMMENT"].strip().lower().rstrip(".! ")
    if cmd not in OK | STOP:
        return                                   # normaler Kommentar, nichts zu tun
    rows = load_calendar()
    r = next((x for x in rows if x["id"] == pid), None)
    if not r:
        return reply(f"❌ {pid} steht nicht im Kalender.")
    st = r["status"]
    if cmd in STOP:
        if st in ("draft", "approved"):
            r["status"] = "hold"; save_calendar(rows)
            return reply("⏸️ Zurückgehalten. Es wird nichts veröffentlicht.", close=True)
        return reply(f"ℹ️ Status ist `{st}`, nichts geändert.")
    if st == "approved":
        return reply("ℹ️ Bereits freigegeben.", close=True)
    if st == "published":
        return reply("ℹ️ Bereits veröffentlicht.", close=True)
    if st not in ("draft", "hold", "failed"):
        return reply(f"❌ Status `{st}`: Es gibt noch keinen Entwurf für diesen Beitrag.")
    if r["format"] == "reel" and not r["video_url"]:
        return reply("❌ Reel nicht freigegeben: Es fehlt die `video_url` in `content_calendar.csv`. "
                     "Eintragen und danach erneut `ok` kommentieren.")
    r["status"] = "approved"; save_calendar(rows)
    when = ("Der Termin liegt in der Vergangenheit: Veröffentlichung beim nächsten stündlichen Lauf (bis ca. 1 Stunde)."
            if parse_dt(r["publish_at"]) <= now() else
            f"Geplant für {r['publish_at']} Uhr (Veröffentlichung im stündlichen Lauf, bis ca. 1 Stunde danach).")
    reply(f"✅ Freigegeben. {when}", close=True)


if __name__ == "__main__":
    main()

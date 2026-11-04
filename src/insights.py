"""Holt Kennzahlen veröffentlichter Posts und schreibt performance.csv."""
import csv, os
from publish import api
from common import *

METRICS = "reach,saved,shares,likes,comments,total_interactions"


def run():
    uid, out = os.environ["IG_USER_ID"], []
    acc = api("GET", uid, fields="followers_count,media_count")
    print(f"Follower: {acc.get('followers_count')} | Posts: {acc.get('media_count')}")
    for r in load_calendar():
        if r["status"] != "published" or not r["media_id"]:
            continue
        try:
            data = api("GET", f"{r['media_id']}/insights", metric=METRICS)["data"]
        except RuntimeError as e:
            print(f"Insights {r['id']} nicht verfügbar: {e}"); continue
        m = {d["name"]: d["values"][0]["value"] for d in data}
        reach = m.get("reach", 0) or 1
        out.append({"id": r["id"], "topic": r["topic"], "format": r["format"], "pillar": r["pillar"],
                    **m, "save_share_rate": round((m.get("saved", 0) + m.get("shares", 0)) / reach, 4),
                    "followers_total": acc.get("followers_count")})
    if out:
        with open(path("performance.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
        print(f"{len(out)} Posts ausgewertet -> performance.csv")


if __name__ == "__main__":
    run()

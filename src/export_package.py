"""Exportiert Beiträge als Upload-Paket für manuelles/halbautomatisches Planen
(Meta Business Suite, Instagram-App, Buffer, Later, Metricool …) – ohne Meta-App/API.
  python src/export_package.py                 # nur status=approved
  python src/export_package.py --include-draft # auch Entwürfe
  python src/export_package.py --mark          # exportierte Posts auf status=scheduled setzen
"""
import csv, os, shutil, sys
from common import *

INCL_DRAFT, MARK = "--include-draft" in sys.argv, "--mark" in sys.argv


def caption_of(c):
    prefix = "Werbung\n\n" if c.get("werbung") else ""
    return f"{prefix}{c['caption'].strip()}\n\n{' '.join(c.get('hashtags', []))}".strip()


def run():
    rows = load_calendar()
    ok = {"approved"} | ({"draft"} if INCL_DRAFT else set())
    out_root = path("export"); shutil.rmtree(out_root, ignore_errors=True); os.makedirs(out_root)
    plan = []
    for r in sorted(rows, key=lambda x: x["publish_at"]):
        if r["status"] not in ok:
            continue
        c = load_content(r["id"])
        dt = r["publish_at"].replace(" ", "_").replace(":", "")
        folder = os.path.join(out_root, f"{dt}_{r['id']}_{r['format']}"); os.makedirs(folder)
        src = path("media", r["id"])
        if os.path.isdir(src):
            for f in sorted(os.listdir(src)):
                shutil.copy(os.path.join(src, f), os.path.join(folder, f))
        with open(os.path.join(folder, "caption.txt"), "w", encoding="utf-8") as f:
            f.write(caption_of(c))
        with open(os.path.join(folder, "alt_text.txt"), "w", encoding="utf-8") as f:
            f.write(c.get("alt_text", ""))
        if c.get("reel_script"):
            with open(os.path.join(folder, "reel_skript.txt"), "w", encoding="utf-8") as f:
                f.write(c["reel_script"])
        d, t = r["publish_at"].split(" ")
        plan.append({"datum": d, "uhrzeit": t, "id": r["id"], "format": r["format"], "thema": r["topic"],
                     "werbung": "ja" if c.get("werbung") else "nein", "ordner": os.path.basename(folder)})
        if MARK:
            r["status"] = "scheduled"
    with open(os.path.join(out_root, "plan.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["datum", "uhrzeit", "id", "format", "thema", "werbung", "ordner"])
        w.writeheader(); w.writerows(plan)
    if MARK:
        save_calendar(rows)
    print(f"{len(plan)} Beiträge exportiert -> export/")


if __name__ == "__main__":
    run()

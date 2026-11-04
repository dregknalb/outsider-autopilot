import csv, json, os, yaml
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELDS = ["id", "publish_at", "pillar", "format", "topic", "status", "media_id", "video_url"]


def cfg():
    with open(os.path.join(ROOT, "config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def path(*p):
    return os.path.join(ROOT, *p)


def load_calendar():
    with open(path(cfg()["calendar"]), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save_calendar(rows):
    with open(path(cfg()["calendar"]), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def now():
    return datetime.now(ZoneInfo(cfg()["timezone"]))


def parse_dt(s):
    return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(cfg()["timezone"]))


def load_content(pid):
    with open(path("content", f"{pid}.json"), encoding="utf-8") as f:
        return json.load(f)


def save_content(pid, data):
    with open(path("content", f"{pid}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def brand_profile():
    with open(path(cfg()["brand_profile"]), encoding="utf-8") as f:
        return f.read()

"""Claude erzeugt Entwürfe (status idea -> draft) und neue Ideen.
  python src/generate.py drafts
  python src/generate.py ideas
"""
import csv, json, os, sys
import anthropic
from common import *

SYSTEM = """Du bist Instagram-Content-Stratege und Texter für den deutschsprachigen Raum.
Halte dich strikt an das Brand-Profil. Regeln: Hook zuerst (max. 8 Wörter im Slide-1-Titel),
ein Post = eine Idee = ein CTA (bevorzugt Speichern/Teilen), kurze Sätze, keine KI-Floskeln,
keine erfundenen Fakten, Zahlen oder Produkt-Testergebnisse, 3-5 Hashtags, Alt-Text liefern.
Stil: understated luxury, ruhig, präzise, Kennerhaltung, kein Verkäuferton, keine Ausrufezeichen-Flut.
Nenne keine konkreten Preise oder Rabatte. Setze "werbung" auf true, wenn der Post Marken/Produkte bewirbt, verlinkt oder gesponsert sein könnte.
Antworte AUSSCHLIESSLICH mit gültigem JSON ohne Markdown-Codeblock."""


def ask(prompt):
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=cfg()["model"], max_tokens=3000, system=SYSTEM,
        messages=[{"role": "user", "content": prompt}])
    txt = "".join(b.text for b in msg.content if b.type == "text").strip()
    txt = txt.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(txt)


def drafts():
    rows, profile = load_calendar(), brand_profile()
    for r in rows:
        if r["status"] != "idea":
            continue
        fmt = r["format"]
        prompt = f"""BRAND-PROFIL:\n{profile}\n\nERSTELLE EINEN POST.
Säule: {r['pillar']} | Format: {fmt} | Thema: {r['topic']}
Schema: {{"hook": str, "slides": [{{"title": str, "body": str}}] (6-9 Slides bei carousel, 1 bei image, [] bei reel, Slide 1 = Hook, letzte = CTA),
"caption": str (Zeile 1 = Hook, kurze Absätze, ein CTA), "hashtags": [str],
"alt_text": str, "werbung": bool, "photo_hint": str (kurze Beschreibung des idealen Fotos pro Slide-Hintergrund), "reel_script": str oder null (bei reel: Szenen mit Sekundenangaben und Text-Overlays)}}"""
        data = ask(prompt)
        save_content(r["id"], data)
        r["status"] = "draft"
        print(f"Entwurf erstellt: {r['id']}")
    save_calendar(rows)


def ideas():
    rows, profile = load_calendar(), brand_profile()
    perf = ""
    if os.path.exists(path("performance.csv")):
        perf = open(path("performance.csv"), encoding="utf-8").read()[-4000:]
    n = cfg()["ideas_per_run"]
    prompt = f"""BRAND-PROFIL:\n{profile}\n\nBISHERIGE LEISTUNG (CSV, kann leer sein):\n{perf}\n\nBISHERIGE THEMEN:
{[r['topic'] for r in rows][-40:]}\n\nLiefere {n} neue, nicht doppelte Post-Ideen, Säulen gemäß Profil gemischt,
Formate nur carousel oder image. Wiederhole Muster der erfolgreichsten Posts.
Schema: [{{"pillar": str, "format": "carousel"|"image", "topic": str}}]"""
    new = ask(prompt)
    start = max([int(r["id"][1:]) for r in rows if r["id"][1:].isdigit()] + [0])
    last = max([parse_dt(r["publish_at"]) for r in rows if r["publish_at"]] + [now()])
    from datetime import timedelta
    for i, it in enumerate(new, 1):
        last = (last + timedelta(days=2)).replace(hour=18, minute=0)
        rows.append({"id": f"p{start + i:03d}", "publish_at": last.strftime("%Y-%m-%d %H:%M"),
                     "pillar": it["pillar"], "format": it["format"], "topic": it["topic"],
                     "status": "idea", "media_id": "", "video_url": ""})
    save_calendar(rows)
    print(f"{len(new)} Ideen hinzugefügt")


if __name__ == "__main__":
    {"drafts": drafts, "ideas": ideas}[sys.argv[1]]()

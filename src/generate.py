"""Claude erzeugt Entwürfe (status idea -> draft) und neue Ideen.
  python src/generate.py drafts
  python src/generate.py ideas
"""
import csv, json, os, sys
from datetime import timedelta
import anthropic
from common import *

SYSTEM = """Du bist Instagram-Content-Stratege und Texter für den deutschsprachigen Raum.
Halte dich strikt an das Brand-Profil. Regeln: Hook zuerst (max. 8 Wörter im Slide-1-Titel),
ein Post = eine Idee = ein CTA (bevorzugt Speichern/Teilen), kurze Sätze, keine KI-Floskeln,
keine erfundenen Fakten, Zahlen oder Produkt-Testergebnisse, 3-5 Hashtags, Alt-Text liefern.
Stil: understated luxury, ruhig, präzise, Kennerhaltung, kein Verkäuferton, keine Ausrufezeichen-Flut.
Nenne keine konkreten Preise oder Rabatte. Setze "werbung" auf true, wenn der Post Marken/Produkte bewirbt, verlinkt oder gesponsert sein könnte.
Antworte AUSSCHLIESSLICH mit gültigem JSON ohne Markdown-Codeblock."""


def ask(prompt, max_tokens=8000):
    """Fragt Claude und liefert geparstes JSON. Wiederholt bei abgeschnittener/ungültiger Antwort."""
    client = anthropic.Anthropic()
    last = None
    for attempt in range(1, 4):
        msg = client.messages.create(
            model=cfg()["model"], max_tokens=max_tokens * attempt, system=SYSTEM,
            messages=[{"role": "user", "content": prompt}])
        txt = "".join(b.text for b in msg.content if b.type == "text").strip()
        txt = txt.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        starts = [i for i in (txt.find("{"), txt.find("[")) if i >= 0]
        if starts:
            txt = txt[min(starts):max(txt.rfind("}"), txt.rfind("]")) + 1]
        try:
            return json.loads(txt)
        except json.JSONDecodeError as e:
            last = f"{e} (stop_reason={msg.stop_reason})"
            print(f"Versuch {attempt}: ungültiges JSON, wiederhole … {last}")
    raise RuntimeError(f"Claude lieferte kein gültiges JSON: {last}")


def drafts():
    rows, profile = load_calendar(), brand_profile()
    failed = []
    horizon = now() + timedelta(days=cfg().get("draft_days_ahead", 14))
    for r in rows:
        if r["status"] != "idea" or parse_dt(r["publish_at"]) > horizon:
            continue                                  # nur Beiträge der nächsten Tage ausarbeiten
        fmt = r["format"]
        prompt = f"""BRAND-PROFIL:\n{profile}\n\nERSTELLE EINEN POST.
Säule: {r['pillar']} | Format: {fmt} | Thema: {r['topic']}
Schema: {{"hook": str, "slides": [{{"title": str, "body": str}}] (6-9 Slides bei carousel, 1 bei image, [] bei reel, Slide 1 = Hook, letzte = CTA, body max. 25 Wörter),
"caption": str (Zeile 1 = Hook, kurze Absätze, ein CTA), "hashtags": [str],
"alt_text": str, "werbung": bool, "photo_hint": str (kurze Beschreibung des idealen Fotos pro Slide-Hintergrund), "reel_script": str oder null (bei reel: Szenen mit Sekundenangaben und Text-Overlays)}}"""
        try:
            data = ask(prompt)
            if fmt != "reel":                      # Schema prüfen, damit das Rendern nicht an Claude-Abweichungen scheitert
                sl = data.get("slides")
                if not isinstance(sl, list) or not sl or not all(isinstance(x, dict) and x.get("title") for x in sl):
                    raise ValueError("Slides fehlen oder haben kein 'title'")
            if not data.get("caption"):
                raise ValueError("Caption fehlt")
            save_content(r["id"], data)
            r["status"] = "draft"
            save_calendar(rows)          # sofort sichern, damit bei späteren Fehlern nichts verloren geht
            print(f"Entwurf erstellt: {r['id']}")
        except Exception as e:
            failed.append(r["id"])
            print(f"::warning::Entwurf {r['id']} fehlgeschlagen: {e}")
    if failed:
        print(f"Nicht erstellt (beim nächsten Lauf erneut versucht): {', '.join(failed)}")


def ideas():
    rows, profile = load_calendar(), brand_profile()
    offen = [r for r in rows if r["status"] in ("idea", "draft", "approved", "hold")]
    puffer = cfg().get("buffer_posts", 12)
    if len(offen) >= puffer:                          # genug Vorrat: keine neuen Ideen
        print(f"{len(offen)} offene Beiträge (Puffer {puffer}), keine neuen Ideen nötig")
        return
    perf = ""
    if os.path.exists(path("performance.csv")):
        perf = open(path("performance.csv"), encoding="utf-8").read()[-4000:]
    n = cfg()["ideas_per_run"]
    prompt = f"""BRAND-PROFIL:\n{profile}\n\nBISHERIGE LEISTUNG (CSV, kann leer sein):\n{perf}\n\nBISHERIGE THEMEN:
{[r['topic'] for r in rows][-40:]}\n\nLiefere {n} neue, nicht doppelte Post-Ideen, Säulen gemäß Profil gemischt,
Formate nur carousel oder image. Wiederhole Muster der erfolgreichsten Posts.
Schema: [{{"pillar": str, "format": "carousel"|"image", "topic": str}}]"""
    new = ask(prompt, max_tokens=3000)
    start = max([int(r["id"][1:]) for r in rows if r["id"][1:].isdigit()] + [0])
    last = max([parse_dt(r["publish_at"]) for r in rows if r["publish_at"]] + [now()])
    for i, it in enumerate(new, 1):
        last = (last + timedelta(days=2)).replace(hour=18, minute=0)
        rows.append({"id": f"p{start + i:03d}", "publish_at": last.strftime("%Y-%m-%d %H:%M"),
                     "pillar": it["pillar"], "format": it["format"], "topic": it["topic"],
                     "status": "idea", "media_id": "", "video_url": ""})
    save_calendar(rows)
    print(f"{len(new)} Ideen hinzugefügt")


if __name__ == "__main__":
    {"drafts": drafts, "ideas": ideas}[sys.argv[1]]()

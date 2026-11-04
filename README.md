# Instagram-Autopilot

Kalender (CSV) → Claude schreibt Entwürfe → Slides werden als PNG gerendert → **du gibst frei** → Veröffentlichung über die Instagram Graph API → Insights → bessere Ideen.

## Ablauf (Status-Spalte in `content_calendar.csv`)
`idea` → `draft` (Claude hat Text + Slides erzeugt) → **`approved` (du setzt das von Hand)** → `published` (oder `failed`)

Es wird nie etwas ohne deine Freigabe veröffentlicht. Prüfe Entwürfe in `content/<id>.json` und `media/<id>/`.

## Einmalige Einrichtung
1. **Instagram-Konto** auf Business oder Creator umstellen und mit einer Facebook-Seite verknüpfen.
2. **Meta-App** unter developers.facebook.com anlegen, Produkt "Instagram" bzw. Graph API hinzufügen. Berechtigungen: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `instagram_manage_insights`, `pages_read_engagement`. Für das eigene Konto reicht der Entwicklermodus (kein App-Review nötig, solange du Admin/Tester der App bist).
3. **Long-Lived Access Token** erzeugen (ca. 60 Tage gültig, vor Ablauf erneuern) und die **Instagram-User-ID** über `GET /me/accounts?fields=instagram_business_account` ermitteln.
4. **Öffentliches GitHub-Repo** anlegen und diesen Ordner hochladen (Instagram muss Bilder per öffentlicher URL laden können). Alternative: eigener Bucket (S3/R2) und `media_base_url` anpassen.
5. **Secrets** im Repo (Settings → Secrets → Actions): `ANTHROPIC_API_KEY`, `IG_USER_ID`, `IG_ACCESS_TOKEN`.
6. `config.yaml` anpassen (`media_base_url`, `handle`, Farben) und `brand_profile.md` ausfüllen (Vorlage im Skill `instagram-growth`).

## Variante ohne Meta-App (empfohlen, wenn die App-Erstellung nicht klappt)
`python src/export_package.py --include-draft` erzeugt `export/` mit einem Ordner pro Beitrag (Slides/Video, `caption.txt`, `alt_text.txt`, Reel-Skript) und `plan.csv` mit Datum und Uhrzeit. Diese Beiträge planst du einmal pro Woche selbst: in der Instagram-App oder der Meta Business Suite (Planen-Funktion) oder in einem Planer wie Buffer, Later oder Metricool. Mit `--mark` setzt das Skript den Status auf `scheduled`. Der Rest der Pipeline (Ideen, Entwürfe, Slides, Reel-Grafiken) bleibt unverändert.

## Lokal testen
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python src/generate.py ideas     # neue Ideen in den Kalender
python src/generate.py drafts    # Entwürfe erzeugen
python src/render.py             # Slides rendern
python src/publish.py --dry-run  # zeigt, was veröffentlicht würde
```

## Zeitplan (GitHub Actions, `.github/workflows/instagram.yml`)
- Montags: Ideen + Entwürfe + Slides werden erzeugt und committet.
- Stündlich: Freigegebene, fällige Posts werden veröffentlicht (max. `max_posts_per_day`).
- Sonntags: Insights → `performance.csv`, fließt in die nächsten Ideen ein.
Cron-Zeiten sind UTC.

## Fotos (wichtig für diese Nische)
Lege eigene Fotos unter `photos/<id>/01.jpg`, `02.jpg` … ab (z. B. `photos/p001/01.jpg`). Beim Rendern werden sie zugeschnitten, abgedunkelt und mit Text versehen. Ohne Foto entsteht eine monochrome Textfläche. Der Entwurf enthält `photo_hint`, also eine Beschreibung des idealen Fotos pro Post. Reihenfolge: Entwurf lesen → Foto ablegen → `python src/render.py` (vorhandene Slides in `media/<id>/` vorher löschen, damit neu gerendert wird).

## Werbekennzeichnung
Steht im Entwurf `"werbung": true`, setzt die Pipeline "Werbung" an den Anfang der Caption. Bei bezahlten Kooperationen zusätzlich die Instagram-Funktion "Bezahlte Partnerschaft" nutzen.

## Reels
Videoschnitt wird nicht automatisiert. Claude liefert das Reel-Skript (`reel_script`). Lade das fertige Video an eine öffentliche URL, trage sie in `video_url` ein, setze Format `reel` und Status `approved`. Der Rest läuft automatisch.

## Motion-Graphic-Reels (ohne eigenes Footage)
`python src/reel_motion.py p003` erzeugt aus `content/p003.motion.json` ein 20-Sekunden-Reel (1080×1920, 30 fps) mit Höhenlinien, Linien-Icons und Typografie unter `media/p003/reel.mp4`. Szenen, Texte und Icons (tent, bag, stove, lamp, camera) lassen sich in der JSON-Datei ändern. Benötigt ffmpeg. Musik in der Instagram-App ergänzen (Lizenz beachten). Zum Veröffentlichen die Datei an einer öffentlichen URL ablegen und in `video_url` eintragen.

## Grenzen & Hinweise
- Graph API: Karussell max. 10 Bilder, Bilder als JPEG/PNG; Limit pro Konto ca. 100 API-Posts / 24 h. API-Versionen ändern sich: `graph_api_version` regelmäßig prüfen.
- Stories, Kommentare beantworten und DMs sind nicht enthalten (Kommentieren bei anderen Accounts bleibt bewusst manuell, das ist ein starker Wachstumshebel).
- Bei realistisch wirkenden KI-Bildern/-Videos die Instagram-Kennzeichnung ("AI info") beachten.
- Token alle ~60 Tage erneuern; Fehler zeigt der Actions-Log, der Post bekommt Status `failed`.

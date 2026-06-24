# 🚀 Code Launcher

Ein kleines Tool, das **Python-Skripte ohne Terminal-Kenntnisse** ausführbar
macht. Perfekt, um Code, den eine KI (ChatGPT, Claude, Gemini …) ausgespuckt
hat, einfach im Browser laufen zu lassen – inklusive automatischer
Erkennung von Web-Apps (Streamlit, Flask, Gradio, Dash, FastAPI).

> **Update-Modell:** Die App lebt in einem Git-Repo. Beim Start wird sie
> automatisch auf den neuesten Stand gebracht. Du als Maintainer musst nur
> in den `main`-Branch pushen – alle Kolleg:innen haben beim nächsten
> Doppelklick die neue Version.

---

## Aufbau

```
code-launcher/                  ← dieses Repo (lebt auf GitHub)
├── Start_macOS.command         ← Bootstrap (kommt 1× per Drive zum User)
├── Start_Windows.bat           ← Bootstrap (kommt 1× per Drive zum User)
├── run.sh                      ← Runner: venv + Streamlit (macOS/Linux)
├── run.bat                     ← Runner: venv + Streamlit (Windows)
├── app.py                      ← die Streamlit-App
├── requirements.txt
├── scripts/                    ← Beispiel-Skripte (nur Demo, kein User-Speicher)
└── README.md
```

Beim ersten Start klont der Bootstrap das Repo nach
`~/.code-launcher-app/`. Bei jedem weiteren Start wird per
`git fetch + reset --hard` der `main`-Branch übernommen.

---

## Setup (einmalig, du als Maintainer)

1. **Repo auf GitHub anlegen** (privat reicht – aber Kolleg:innen brauchen
   dann Lese-Zugriff. Am einfachsten: öffentliches Repo, da kein Geheimnis
   drin steht).
2. Dieses Verzeichnis als initialen Commit hochladen:
   ```bash
   git init
   git add .
   git commit -m "Initial code launcher"
   git branch -M main
   git remote add origin https://github.com/<dein-name>/code-launcher.git
   git push -u origin main
   ```
3. In **beiden** Bootstrap-Dateien die `REPO_URL` anpassen:
   - `Start_macOS.command` → Zeile mit `REPO_URL="…"`
   - `Start_Windows.bat` → Zeile mit `set "REPO_URL=…"`
4. Die beiden angepassten Bootstrap-Dateien (`Start_macOS.command` und
   `Start_Windows.bat`) **in Google Drive** ablegen und mit dem Team teilen.

**Updates später:** einfach Änderung committen + `git push`. Fertig.

---

## Setup (deine Kolleg:innen)

1. **Python** installieren (einmalig):
   - macOS: <https://www.python.org/downloads/macos/>
   - Windows: <https://www.python.org/downloads/> – beim Installer
     **unbedingt** `Add Python to PATH` ankreuzen.
2. **Git** installieren (einmalig):
   - macOS: im Terminal `xcode-select --install`
     oder <https://git-scm.com/download/mac>
   - Windows: <https://git-scm.com/download/win>
3. Die `Start_*`-Datei aus Drive auf den Desktop ziehen und doppelklicken.

Beim ersten Mal dauert es ca. 1–2 Minuten (Repo-Clone + Streamlit-Install).
Danach startet sich der Code Launcher automatisch im Browser unter
<http://localhost:8501>.

> **macOS:** Falls die `.command`-Datei beim Doppelklick blockiert wird,
> Rechtsklick → **Öffnen** → **Öffnen**. macOS merkt sich das dauerhaft.

---

## Bedienung

Im Browser stehen zwei Tabs zur Verfügung:

1. **📝 Code einfügen** – Code aus der KI direkt einkleben → **Ausführen**.
2. **📤 Datei hochladen** – `.py`-Datei vom Computer wählen.

In der **Sidebar** liegen Beispiel-Skripte zum schnellen Ausprobieren.

### Web-Apps (Streamlit/Flask/Gradio/…)
Wird automatisch erkannt. Die App startet auf einem freien `localhost`-Port
und wird direkt eingebettet angezeigt – ein Klick öffnet sie im Browser-Tab.

### Kommandozeilen-Skripte (`argparse`)
Wenn das Skript `--in`, `--out` etc. erwartet, klappt automatisch der
Bereich **⚙️ Argumente & Eingabedateien** auf:

- Eingabedateien hochladen
- Argumente eintippen (`--in data.xlsx --out result.xlsx --rules rules.json`)
- Optional: `--help` des Skripts anzeigen
- Ausführen → erzeugte Dateien (`result.xlsx`, …) erscheinen unten als
  **Download-Buttons**

### Speicher-Verhalten
**Es wird nichts auf der Festplatte gespeichert.** Jeder Lauf passiert in
einem temporären Ordner, der mit dem nächsten Neustart wieder weg ist.
Dadurch bleibt die App immer sauber updatebar.

---

## Pakete fehlen?

Bei `ModuleNotFoundError: No module named 'pandas'` einfach am Anfang
des Skripts ergänzen lassen (von der KI):

```python
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas"])
import pandas as pd
```

---

## Troubleshooting

| Problem | Lösung |
|---|---|
| „Git ist nicht installiert" | siehe Setup-Schritt 2 |
| „Python wurde nicht gefunden" | Python neu installieren, bei Windows *Add to PATH* ankreuzen |
| macOS blockiert die `.command` | Rechtsklick → **Öffnen** → **Öffnen** |
| Browser öffnet sich nicht | manuell <http://localhost:8501> aufrufen |
| Port belegt | das Terminal-Fenster schließen und neu starten |
| Updates kommen nicht an | Internet checken, dann Launcher neu starten – das Update wird **vor** Streamlit gezogen |

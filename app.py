"""
Code Launcher – eine einfache Web-Oberfläche, mit der man Python-Skripte
aus einem Ordner ausführen, einfügen oder hochladen kann. Web-Apps
(Streamlit, Flask, Gradio, Dash, FastAPI/Uvicorn) werden automatisch
erkannt und in einem neuen Tab auf localhost geöffnet.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = APP_DIR / "scripts"  # nur Beispiele aus dem Repo, read-only
EXAMPLES_DIR.mkdir(exist_ok=True)

PYTHON_EXE = sys.executable
APP_VERSION = os.environ.get("CODE_LAUNCHER_VERSION", "")

# ---------------------------------------------------------------------------
# Helfer: Skript-Typ erkennen
# ---------------------------------------------------------------------------

WEB_FRAMEWORKS = {
    "streamlit": re.compile(r"\bimport\s+streamlit\b|\bfrom\s+streamlit\b"),
    "gradio": re.compile(r"\bimport\s+gradio\b|\bfrom\s+gradio\b"),
    "flask": re.compile(r"\bimport\s+flask\b|\bfrom\s+flask\b"),
    "dash": re.compile(r"\bimport\s+dash\b|\bfrom\s+dash\b"),
    "fastapi": re.compile(r"\bimport\s+fastapi\b|\bfrom\s+fastapi\b"),
}


def detect_framework(code: str) -> Optional[str]:
    for name, pattern in WEB_FRAMEWORKS.items():
        if pattern.search(code):
            return name
    return None


ARGPARSE_PATTERN = re.compile(r"\b(import\s+argparse|from\s+argparse\b|add_argument\s*\()")
SYSARGV_PATTERN = re.compile(r"\bsys\.argv\b")


def uses_cli_args(code: str) -> bool:
    """Heuristik: nutzt das Skript Kommandozeilen-Argumente?"""
    return bool(ARGPARSE_PATTERN.search(code) or SYSARGV_PATTERN.search(code))


def get_script_help(script_path: Path, timeout: float = 10.0) -> Optional[str]:
    """Versucht, die --help-Ausgabe eines Skripts zu holen."""
    try:
        result = subprocess.run(
            [PYTHON_EXE, str(script_path), "--help"],
            cwd=str(script_path.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        text = result.stdout or ""
        if "usage:" in text.lower() or "options:" in text.lower():
            return text
    except Exception:
        pass
    return None


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_port(port: int, timeout: float = 20.0) -> bool:
    """Wartet bis ein Port erreichbar ist (Web-App ist gestartet)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.3)
    return False


# ---------------------------------------------------------------------------
# Datenmodell für laufende Prozesse
# ---------------------------------------------------------------------------


@dataclass
class RunningJob:
    name: str
    framework: Optional[str]
    process: subprocess.Popen
    port: Optional[int] = None
    log_lines: list[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)

    @property
    def url(self) -> Optional[str]:
        if self.port:
            return f"http://localhost:{self.port}"
        return None

    @property
    def is_running(self) -> bool:
        return self.process.poll() is None


def _reader_thread(job: RunningJob) -> None:
    assert job.process.stdout is not None
    for line in job.process.stdout:
        job.log_lines.append(line.rstrip("\n"))
        if len(job.log_lines) > 2000:
            del job.log_lines[: len(job.log_lines) - 2000]


# ---------------------------------------------------------------------------
# Skripte starten
# ---------------------------------------------------------------------------


def _build_command(script_path: Path, framework: Optional[str], port: int) -> list[str]:
    if framework == "streamlit":
        return [
            PYTHON_EXE, "-m", "streamlit", "run", str(script_path),
            "--server.port", str(port),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ]
    if framework in {"flask", "dash", "fastapi", "gradio"}:
        env_hint_cmd = [PYTHON_EXE, str(script_path)]
        return env_hint_cmd
    return [PYTHON_EXE, "-u", str(script_path)]


def launch_script(script_path: Path, framework: Optional[str]) -> RunningJob:
    port = free_port() if framework else None
    env = os.environ.copy()
    if framework == "gradio":
        env["GRADIO_SERVER_PORT"] = str(port)
        env["GRADIO_SERVER_NAME"] = "127.0.0.1"
    elif framework == "flask":
        env["FLASK_RUN_PORT"] = str(port)
        env["FLASK_RUN_HOST"] = "127.0.0.1"
    elif framework == "dash":
        env["PORT"] = str(port)
    elif framework == "fastapi":
        env["UVICORN_PORT"] = str(port)
        env["PORT"] = str(port)

    cmd = _build_command(script_path, framework, port or 0)

    process = subprocess.Popen(
        cmd,
        cwd=str(script_path.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )

    job = RunningJob(name=script_path.name, framework=framework, process=process, port=port)
    threading.Thread(target=_reader_thread, args=(job,), daemon=True).start()
    return job


def run_plain_script_and_capture(
    script_path: Path,
    args: Optional[list[str]] = None,
    cwd: Optional[Path] = None,
    timeout: float = 300.0,
) -> tuple[int, str]:
    """Führt ein normales Skript aus und liefert (returncode, output)."""
    cmd = [PYTHON_EXE, "-u", str(script_path), *(args or [])]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd or script_path.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout or ""
    except subprocess.TimeoutExpired as exc:
        return -1, (exc.stdout or "") + f"\n\n[Abbruch: Skript lief länger als {timeout:.0f} Sekunden]"


def snapshot_files(directory: Path) -> dict[str, float]:
    """Schnappschuss: Dateipfad → mtime, um neue/veränderte Dateien zu finden."""
    out: dict[str, float] = {}
    if not directory.exists():
        return out
    for p in directory.rglob("*"):
        if p.is_file():
            try:
                out[str(p.relative_to(directory))] = p.stat().st_mtime
            except OSError:
                continue
    return out


def changed_or_new_files(before: dict[str, float], directory: Path) -> list[Path]:
    """Liefert Dateien, die seit dem Schnappschuss neu oder geändert sind."""
    after = snapshot_files(directory)
    result: list[Path] = []
    for rel, mtime in after.items():
        if before.get(rel) != mtime:
            result.append(directory / rel)
    return sorted(result, key=lambda p: p.stat().st_mtime, reverse=True)


# ---------------------------------------------------------------------------
# Streamlit-UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Code Launcher", page_icon="🚀", layout="wide")

if "jobs" not in st.session_state:
    st.session_state.jobs: list[RunningJob] = []

st.title("🚀 Code Launcher")
st.caption(
    "Python-Skripte einfach laden, ausführen und Web-Apps direkt im Browser öffnen – "
    "ganz ohne Terminal-Kenntnisse."
)

with st.sidebar:
    st.header("Beispiel-Skripte")
    st.caption(
        'Klicke ein Beispiel an, um es in den Tab **„Code einfügen"** zu laden. '
        "Es wird nichts gespeichert – jeder Lauf passiert in einem temporären Ordner."
    )
    example_files = sorted(EXAMPLES_DIR.glob("*.py"))
    if not example_files:
        st.info("Keine Beispiele vorhanden.")
    for f in example_files:
        if st.button(f"📄 {f.name}", key=f"pick_{f.name}", use_container_width=True):
            st.session_state["loaded_code"] = f.read_text(encoding="utf-8")
            st.session_state["loaded_name"] = f.name

    st.divider()
    st.header("Laufende Apps")
    alive = [j for j in st.session_state.jobs if j.is_running]
    if not alive:
        st.caption("Aktuell läuft nichts.")
    for job in alive:
        st.markdown(f"**{job.name}**  \n_{job.framework or 'Skript'}_")
        if job.url:
            st.markdown(f"🌐 [{job.url}]({job.url})")
        if st.button("⏹ Stoppen", key=f"stop_{id(job)}"):
            try:
                job.process.terminate()
            except Exception:
                pass
            st.rerun()
        st.divider()

    if APP_VERSION:
        st.caption(f"Version: `{APP_VERSION}`")

tab_paste, tab_upload, tab_help = st.tabs(
    ["📝 Code einfügen", "📤 Datei hochladen", "❓ Hilfe"]
)


def render_cli_options(code: str, key_prefix: str) -> tuple[list[str], list, bool]:
    """Zeigt die UI für Argumente & Datei-Uploads. Liefert (args, uploaded_files, show_help_clicked)."""
    needs_args = uses_cli_args(code)
    label = (
        "⚙️ Argumente & Eingabedateien (dieses Skript erwartet Argumente)"
        if needs_args
        else "⚙️ Argumente & Eingabedateien (optional)"
    )
    with st.expander(label, expanded=needs_args):
        if needs_args:
            st.caption(
                "Dieses Skript wurde als Kommandozeilen-Tool gebaut. "
                "Lade hier die Eingabedateien hoch und gib die Argumente ein, "
                "z. B. `--in data.xlsx --out result.xlsx --rules rules.json`."
            )
        uploaded = st.file_uploader(
            "Eingabedateien (werden ins Arbeitsverzeichnis kopiert)",
            type=None,
            accept_multiple_files=True,
            key=f"{key_prefix}_files",
        )
        args_str = st.text_input(
            "Kommandozeilen-Argumente",
            value=st.session_state.get(f"{key_prefix}_args", ""),
            placeholder="--in data.xlsx --out result.xlsx --rules rules.json",
            key=f"{key_prefix}_args_input",
            help="Mit Leerzeichen getrennt. Anführungszeichen für Werte mit Leerzeichen.",
        )
        show_help = st.checkbox(
            "Hilfe (`--help`) des Skripts anzeigen",
            key=f"{key_prefix}_show_help",
            help="Führt das Skript mit --help aus, damit du siehst welche Argumente es erwartet.",
        )
        try:
            args = shlex.split(args_str) if args_str.strip() else []
        except ValueError as exc:
            st.error(f"Konnte Argumente nicht parsen: {exc}")
            args = []
    return args, uploaded or [], show_help


def _execute(
    code: str,
    name: str,
    cli_args: Optional[list[str]] = None,
    uploaded_files: Optional[list] = None,
    show_help: bool = False,
) -> None:
    cli_args = cli_args or []
    uploaded_files = uploaded_files or []

    tmp = Path(tempfile.mkdtemp(prefix="codelauncher_")) / (name or "snippet.py")
    tmp.write_text(code, encoding="utf-8")
    script_path = tmp

    framework = detect_framework(code)

    if show_help and not framework:
        with st.spinner("Hole `--help`-Ausgabe …"):
            help_text = get_script_help(script_path)
        if help_text:
            st.subheader("Hilfe des Skripts")
            st.code(help_text)
        else:
            st.warning("Konnte keine `--help`-Ausgabe ermitteln.")
        return

    if not framework and (cli_args or uploaded_files):
        workdir = Path(tempfile.mkdtemp(prefix="codelauncher_run_"))
        script_in_workdir = workdir / script_path.name
        shutil.copy2(script_path, script_in_workdir)
        for uf in uploaded_files:
            (workdir / uf.name).write_bytes(uf.getvalue())
        st.caption(f"Arbeitsverzeichnis: `{workdir}`")
        before = snapshot_files(workdir)
        with st.spinner("Skript läuft …"):
            rc, output = run_plain_script_and_capture(
                script_in_workdir, args=cli_args, cwd=workdir
            )
        if rc == 0:
            st.success("Fertig (Exit-Code 0).")
        else:
            st.error(f"Skript endete mit Fehler (Exit-Code {rc}).")
        st.subheader("Ausgabe")
        st.code(output or "(keine Ausgabe)")
        new_files = [
            p for p in changed_or_new_files(before, workdir) if p.name != script_path.name
        ]
        if new_files:
            st.subheader("📥 Erzeugte Dateien")
            for p in new_files:
                try:
                    data = p.read_bytes()
                except OSError:
                    continue
                st.download_button(
                    label=f"⬇️ {p.relative_to(workdir)} ({len(data) / 1024:.1f} KB)",
                    data=data,
                    file_name=p.name,
                    key=f"dl_{p}",
                )
        return

    if framework:
        st.info(f"Web-App erkannt: **{framework}**. Wird auf localhost gestartet …")
        job = launch_script(script_path, framework)
        st.session_state.jobs.append(job)
        with st.spinner("Warte auf Start der Web-App …"):
            ok = wait_for_port(job.port, timeout=30.0) if job.port else False
        if ok and job.url:
            st.success(f"✅ App läuft: {job.url}")
            st.markdown(
                f'<a href="{job.url}" target="_blank">'
                f'<button style="padding:0.6em 1.2em;font-size:1rem;cursor:pointer;'
                f'background:#2563eb;color:white;border:none;border-radius:6px;">'
                f'🌐 Im Browser öffnen</button></a>',
                unsafe_allow_html=True,
            )
            st.components.v1.iframe(job.url, height=600, scrolling=True)
        else:
            st.error("Die App ist nicht innerhalb von 30 Sekunden gestartet. Log:")
        with st.expander("Log anzeigen", expanded=not ok):
            st.code("\n".join(job.log_lines[-200:]) or "(noch keine Ausgabe)")
    else:
        st.info("Klassisches Skript – wird ausgeführt, die Ausgabe erscheint unten.")
        with st.spinner("Skript läuft …"):
            rc, output = run_plain_script_and_capture(script_path)
        if rc == 0:
            st.success("Fertig (Exit-Code 0).")
        else:
            st.error(f"Skript endete mit Fehler (Exit-Code {rc}).")
        st.subheader("Ausgabe")
        st.code(output or "(keine Ausgabe)")


with tab_paste:
    st.subheader("Python-Code direkt einfügen")
    st.caption(
        "Kopiere den Code aus ChatGPT, Claude, Gemini & Co. hier hinein. "
        "Es wird nichts gespeichert – jeder Lauf passiert in einem temporären Ordner."
    )
    default_code = st.session_state.get(
        "loaded_code",
        '# Beispiel: einfache Streamlit-App\n'
        'import streamlit as st\n\n'
        'st.title("Hallo Welt!")\n'
        'name = st.text_input("Wie heißt du?")\n'
        'if name:\n'
        '    st.success(f"Schön dich zu sehen, {name}!")\n',
    )
    name = st.text_input("Dateiname", value=st.session_state.get("loaded_name", "mein_skript.py"))
    code = st.text_area("Code", value=default_code, height=320)
    args, files, show_help = render_cli_options(code, key_prefix="paste")
    if st.button("▶️ Ausführen", key="run_paste", type="primary"):
        if code.strip():
            _execute(
                code,
                name or "snippet.py",
                cli_args=args,
                uploaded_files=files,
                show_help=show_help,
            )
        else:
            st.warning("Bitte zuerst Code einfügen.")


with tab_upload:
    st.subheader("Python-Datei hochladen")
    st.caption("Wähle eine `.py`-Datei von deinem Computer. Sie wird nicht gespeichert.")
    uploaded = st.file_uploader("Python-Datei", type=["py"], key="py_upload")
    if uploaded is not None:
        code = uploaded.getvalue().decode("utf-8")
        with st.expander("Vorschau", expanded=False):
            st.code(code, language="python")
        args, files, show_help = render_cli_options(code, key_prefix="upload")
        if st.button("▶️ Ausführen", key="run_upload", type="primary"):
            _execute(
                code,
                uploaded.name,
                cli_args=args,
                uploaded_files=files,
                show_help=show_help,
            )


with tab_help:
    st.subheader("So benutzt du den Code Launcher")
    st.markdown(
        """
**Zwei Wege, ein Skript zu starten:**

1. **Code einfügen** – Kopiere den Code aus ChatGPT/Claude/Gemini direkt
   ins Textfeld und klicke **Ausführen**.
2. **Datei hochladen** – Wähle eine `.py`-Datei von deinem Computer.

> Es wird **nichts gespeichert**. Jeder Lauf passiert in einem temporären
> Ordner, der mit dem nächsten Neustart wieder weg ist. So bleibt die App
> immer sauber updatebar.

In der Sidebar findest du **Beispiele**, die du mit einem Klick in den
Code-Editor laden kannst.

**Was passiert dann?**

- Der Launcher schaut, ob es sich um eine **Web-App** handelt
  (Streamlit, Flask, Gradio, Dash, FastAPI). Falls ja, wird sie auf einer
  freien `localhost`-Adresse gestartet und direkt eingebettet angezeigt.
- Sonst läuft das Skript ganz normal und du siehst die Konsolen-Ausgabe.

**Skript erwartet Argumente (`--in`, `--out`, …)?**

Manche KI-Skripte sind als *Kommandozeilen-Tools* gebaut und erwarten Argumente.
Wenn du beim Ausführen so etwas siehst:

```
usage: skript.py [-h] --in IN_PATH --out OUT_PATH
skript.py: error: the following arguments are required: --in, --out
```

dann öffne den Bereich **⚙️ Argumente & Eingabedateien** über dem
**Ausführen**-Knopf:

1. Lade die nötigen Eingabedateien hoch (z. B. `data.xlsx`, `rules.json`).
2. Gib die Argumente ins Textfeld ein, z. B.
   `--in data.xlsx --out result.xlsx --rules rules.json`.
3. Optional: Häkchen bei *Hilfe anzeigen* setzen und einmal ausführen,
   um die `--help`-Ausgabe des Skripts zu sehen.
4. **Ausführen** klicken. Erzeugte Dateien (z. B. `result.xlsx`)
   erscheinen darunter als **Download-Buttons**.

**Pakete fehlen?**

Falls beim Ausführen eine Meldung wie *„ModuleNotFoundError: No module named 'pandas'“*
erscheint, kannst du das Paket einfach am Anfang des Skripts so installieren:

```python
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas"])
import pandas as pd
```

Oder bitte deine KI, diese drei Zeilen zu ergänzen.
        """
    )

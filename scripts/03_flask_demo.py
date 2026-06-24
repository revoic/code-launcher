"""Beispiel einer kleinen Flask-Web-App.

Der Code Launcher erkennt Flask automatisch und startet die App auf
einem freien Port (über die Umgebungsvariable FLASK_RUN_PORT).
"""

import os
from flask import Flask

app = Flask(__name__)


@app.get("/")
def index() -> str:
    return """
    <html><body style="font-family: system-ui; padding: 3em; text-align:center;">
      <h1>🌶️ Flask läuft!</h1>
      <p>Diese Seite wurde von einem Python-Skript erzeugt.</p>
    </body></html>
    """


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_RUN_PORT", "5000"))
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=False)

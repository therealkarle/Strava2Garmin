"""Interactive Strava OAuth setup."""

from __future__ import annotations

import json
import os
import secrets
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "Strava2Garmin"
TOKEN_FILE = APP_DIR / "strava-token.json"
REDIRECT_URI = "http://localhost:8765/callback"


def main() -> None:
    client_id = input("Strava Client-ID: ").strip()
    client_secret = input("Strava Client-Secret: ").strip()
    if not client_id or not client_secret:
        raise SystemExit("Client-ID und Client-Secret dürfen nicht leer sein.")
    state = secrets.token_urlsafe(24)
    result: dict[str, str] = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if query.get("state", [""])[0] != state:
                self.send_error(400, "Invalid OAuth state")
                return
            if "error" in query:
                self.send_error(400, query["error"][0])
                return
            result["code"] = query.get("code", [""])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write("Strava-Anmeldung erfolgreich. Dieses Fenster kann geschlossen werden.".encode())

        def log_message(self, *_args: object) -> None:
            return

    params = urllib.parse.urlencode(
        {"client_id": client_id, "redirect_uri": REDIRECT_URI, "response_type": "code", "approval_prompt": "auto", "scope": "read,activity:read_all", "state": state}
    )
    print("Browser wird geöffnet. Falls nicht, diese URL öffnen:")
    url = f"https://www.strava.com/oauth/authorize?{params}"
    print(url)
    webbrowser.open(url)
    HTTPServer(("localhost", 8765), Callback).handle_request()
    if not result.get("code"):
        raise SystemExit("Kein OAuth-Code empfangen.")
    form = urllib.parse.urlencode({"client_id": client_id, "client_secret": client_secret, "code": result["code"], "grant_type": "authorization_code"}).encode()
    request = urllib.request.Request("https://www.strava.com/oauth/token", data=form, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        token = json.load(response)
    APP_DIR.mkdir(parents=True, exist_ok=True)
    token.update({"client_id": client_id, "client_secret": client_secret})
    TOKEN_FILE.write_text(json.dumps(token, indent=2), encoding="utf-8")
    print(f"Strava-Token gespeichert: {TOKEN_FILE}")


if __name__ == "__main__":
    main()

"""Interactive Garmin Connect token setup, including MFA."""

from __future__ import annotations

import getpass
import os
from pathlib import Path

APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "Strava2Garmin"
TOKEN_DIR = APP_DIR / "garmin-tokens"


def main() -> None:
    try:
        from garminconnect import Garmin
    except ImportError as exc:
        raise SystemExit("python-garminconnect is missing; run pip install -r requirements.txt first.") from exc

    email = input("Garmin email: ").strip()
    password = getpass.getpass("Garmin password: ")

    def prompt_mfa() -> str:
        return input("Garmin MFA code: ").strip()

    APP_DIR.mkdir(parents=True, exist_ok=True)
    client = Garmin(email, password, prompt_mfa=prompt_mfa)
    try:
        mfa_required, _ = client.login(tokenstore=str(TOKEN_DIR))
        if mfa_required:
            raise RuntimeError("MFA was not completed.")
    except Exception as exc:
        raise SystemExit(f"Garmin login failed: {exc}") from exc
    print(f"Garmin token saved: {TOKEN_DIR}")


if __name__ == "__main__":
    main()

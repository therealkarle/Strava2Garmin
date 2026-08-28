"""Delay the automatic startup run, then start the synchronizer."""

from __future__ import annotations

import subprocess
import sys
import time
import os
from datetime import datetime
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback is not supported
    tomllib = None


WINDOWS_ERROR_NOTIFICATION = (
    "Add-Type -AssemblyName PresentationFramework; "
    "[System.Windows.MessageBox]::Show($env:STRAVA2GARMIN_STARTUP_ERROR, "
    "'Strava2Garmin startup failed', 'OK', 'Error')"
)


def load_startup_delay(path: Path) -> int:
    if tomllib is None:
        raise RuntimeError("Python 3.11 or newer is required.")
    with path.open("rb") as handle:
        delay = tomllib.load(handle).get("startup_delay_minutes", 0)
    if not isinstance(delay, int) or delay < 0:
        raise ValueError("startup_delay_minutes must be a non-negative integer.")
    return delay


def report_startup_error(error: Exception, log_path: Path) -> None:
    message = str(error)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{datetime.now().isoformat(timespec='seconds')} {message}\n")
    if sys.platform == "win32":
        environment = os.environ.copy()
        environment["STRAVA2GARMIN_STARTUP_ERROR"] = message
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", WINDOWS_ERROR_NOTIFICATION],
                env=environment,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:
            pass


def main() -> int:
    project_directory = Path(__file__).resolve().parent
    config_path = project_directory / "config.toml"
    error_log = Path(os.environ.get("APPDATA", Path.home())) / "Strava2Garmin" / "startup-error.log"
    try:
        delay = load_startup_delay(config_path)
        print(f"Waiting {delay} minute(s) before starting sync.", flush=True)
        if delay:
            time.sleep(delay * 60)
        result = subprocess.run(
            [sys.executable, str(project_directory / "sync.py"), "--config", str(config_path)],
            cwd=project_directory,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if result.returncode:
            details = result.stdout.strip() or f"Sync exited with code {result.returncode}."
            raise RuntimeError(details)
        return 0
    except Exception as exc:
        report_startup_error(exc, error_log)
        return 1


if __name__ == "__main__":
    sys.exit(main())

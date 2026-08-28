"""Delay the automatic startup run, then start the synchronizer."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback is not supported
    tomllib = None


def load_startup_delay(path: Path) -> int:
    if tomllib is None:
        raise RuntimeError("Python 3.11 or newer is required.")
    with path.open("rb") as handle:
        delay = tomllib.load(handle).get("startup_delay_minutes", 0)
    if not isinstance(delay, int) or delay < 0:
        raise ValueError("startup_delay_minutes must be a non-negative integer.")
    return delay


def main() -> int:
    project_directory = Path(__file__).resolve().parent
    config_path = project_directory / "config.toml"
    delay = load_startup_delay(config_path)
    print(f"Waiting {delay} minute(s) before starting sync.", flush=True)
    if delay:
        time.sleep(delay * 60)
    return subprocess.run(
        [sys.executable, str(project_directory / "sync.py"), "--config", str(config_path)],
        cwd=project_directory,
        check=False,
    ).returncode


if __name__ == "__main__":
    sys.exit(main())

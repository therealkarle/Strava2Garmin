"""Interactively select activities, then run the existing synchronizer."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Callable

import sync
from sync import load_config, parse_date


CONFIG_PATH = Path(__file__).resolve().parent / "config.toml"


def _ask_date(prompt: str, input_func: Callable[[str], str], *, allow_empty: bool = False) -> dt.date | None:
    while True:
        value = input_func(prompt).strip()
        if not value and allow_empty:
            return None
        try:
            return parse_date(value)
        except ValueError:
            print("Enter a date as YYYY-MM-DD.")


def _ask_limit(input_func: Callable[[str], str], default: int) -> int:
    while True:
        value = input_func(f"Number of recent activities [{default}]: ").strip()
        if not value:
            return default
        try:
            limit = int(value)
            if limit > 0:
                return limit
        except ValueError:
            pass
        print("Enter a positive whole number.")


def main(input_func: Callable[[str], str] = input, today: dt.date | None = None) -> int:
    today = today or dt.date.today()
    mode = input_func("Use date range mode? [Y/n]: ").strip().lower()
    arguments = ["--config", str(CONFIG_PATH)]
    if mode in ("", "y", "yes"):
        start_date = _ask_date("Start date (YYYY-MM-DD): ", input_func)
        end_date = _ask_date("End date (YYYY-MM-DD, blank for today): ", input_func, allow_empty=True) or today
        arguments.extend(("--start-date", start_date.isoformat(), "--end-date", end_date.isoformat()))
    elif mode == "n":
        arguments.extend(("--limit", str(_ask_limit(input_func, load_config(CONFIG_PATH)["limit"]))))
    else:
        print("Enter Y for date range mode or N for recent activities.")
        return main(input_func, today)
    return sync.main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())

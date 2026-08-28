from pathlib import Path

import startup_launcher
from startup_launcher import load_startup_delay


def test_load_startup_delay_reads_config(tmp_path: Path):
    config = tmp_path / "config.toml"
    config.write_text("startup_delay_minutes = 7\n", encoding="utf-8")

    assert load_startup_delay(config) == 7


def test_report_startup_error_logs_and_notifies_on_windows(tmp_path: Path, monkeypatch):
    calls = []
    monkeypatch.setattr(startup_launcher.sys, "platform", "win32")
    monkeypatch.setattr(startup_launcher.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    startup_launcher.report_startup_error(RuntimeError("Garmin login failed"), tmp_path / "startup-error.log")

    assert "Garmin login failed" in (tmp_path / "startup-error.log").read_text(encoding="utf-8")
    assert calls[0][0][0] == ["powershell", "-NoProfile", "-Command", startup_launcher.WINDOWS_ERROR_NOTIFICATION]

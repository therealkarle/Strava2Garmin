from pathlib import Path

from startup_launcher import load_startup_delay


def test_load_startup_delay_reads_config(tmp_path: Path):
    config = tmp_path / "config.toml"
    config.write_text("startup_delay_minutes = 7\n", encoding="utf-8")

    assert load_startup_delay(config) == 7

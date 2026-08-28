import os
import shutil
import subprocess
from pathlib import Path


def test_setup_batch_runs_selected_steps_in_order(tmp_path: Path):
    """Catches a setup step being skipped or run out of order."""
    project = tmp_path / "project"
    project.mkdir()
    shutil.copy(Path("setup.bat"), project / "setup.bat")
    (project / "config.toml.example").write_text("example = true\n", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "commands.log"
    (bin_dir / "py.bat").write_text("@echo py %*>> \"%SETUP_LOG%\"\n", encoding="utf-8")
    (bin_dir / "powershell.bat").write_text("@echo powershell %*>> \"%SETUP_LOG%\"\n", encoding="utf-8")
    environment = os.environ | {"PATH": f"{bin_dir};{os.environ['PATH']}", "SETUP_LOG": str(log)}

    subprocess.run(
        ["cmd", "/d", "/c", "setup.bat"],
        cwd=project,
        env=environment,
        input="y\ny\ny\n",
        text=True,
        check=True,
    )

    assert (project / "config.toml").read_text(encoding="utf-8") == "example = true\n"
    assert log.read_text(encoding="utf-8").splitlines() == [
        "py -m pip install -r requirements.txt",
        "py setup_strava.py",
        "py setup_garmin.py",
        "powershell -ExecutionPolicy Bypass -File .\\setup_startup.ps1",
    ]


def test_setup_batch_reports_skipped_options_and_setup_progress(tmp_path: Path):
    """Catches hidden choices or silent skips in the interactive setup."""
    project = tmp_path / "project"
    project.mkdir()
    shutil.copy(Path("setup.bat"), project / "setup.bat")
    (project / "config.toml.example").write_text("example = true\n", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "commands.log"
    (bin_dir / "py.bat").write_text("@echo py %*>> \"%SETUP_LOG%\"\n", encoding="utf-8")
    (bin_dir / "powershell.bat").write_text("@echo powershell %*>> \"%SETUP_LOG%\"\n", encoding="utf-8")
    environment = os.environ | {"PATH": f"{bin_dir};{os.environ['PATH']}", "SETUP_LOG": str(log)}

    result = subprocess.run(
        ["cmd", "/d", "/c", "setup.bat"],
        cwd=project,
        env=environment,
        input="n\nn\nn\n",
        text=True,
        capture_output=True,
        check=True,
    )

    assert "[Y,N]?" in result.stdout
    assert "Skipped Python requirements." in result.stdout
    assert "Skipped config.toml creation." in result.stdout
    assert "Starting Strava setup..." in result.stdout
    assert "Starting Garmin setup..." in result.stdout
    assert "Skipped automatic startup setup." in result.stdout
    assert log.read_text(encoding="utf-8").splitlines() == ["py setup_strava.py", "py setup_garmin.py"]

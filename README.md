# Strava2Garmin

Copies names and descriptions from recent Strava activities to the matching existing Garmin activities.

## Setup

Python 3.11+ is required.

```powershell
py -m pip install -r requirements.txt
Copy-Item config.toml.example config.toml
py setup_strava.py
py setup_garmin.py
```

Strava requires an API application with `http://localhost:8765/callback` configured as the callback URL. The Garmin script prompts for an MFA code when needed.

## Manual run

```powershell
py sync.py --dry-run
py sync.py --limit 5
py sync.py --match-tolerance 10 --log-level DEBUG
```

A Strava activity is matched to exactly one Garmin activity by start time and sport. With `ignore_sport_type = true`, the sport is ignored and only the start time is used. Ambiguous matches are skipped. Use `--no-overwrite` to protect existing Garmin text.

Set `sync_event_type = true` to optionally copy Strava classifications to Garmin: race → `Wettkampf`, workout and long run → `Training`, and Strava commute → `Verkehrsmittel`. Other Garmin event categories remain unchanged because Strava has no direct equivalent.

## Startup

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_startup.ps1
```

The task starts when Windows logs in; `startup_launcher.py` applies `startup_delay_minutes` from `config.toml` before starting the sync. Running `sync.py` manually starts immediately.

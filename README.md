# Strava2Garmin: Sync Strava Activity Names and Descriptions to Garmin Connect

Strava2Garmin is a small Windows-friendly Python tool that copies activity metadata from Strava to the matching activity already in Garmin Connect. It helps keep Garmin activity names, descriptions, and optional event categories consistent with Strava without uploading or duplicating activities.

## What Strava2Garmin Syncs

- **Activity names** from Strava to Garmin Connect.
- **Activity descriptions**, including descriptions fetched from the individual Strava activity when they are not returned in the activity list.
- **Optional event categories**: Strava races become Garmin `Wettkampf`; workouts and long runs become `Training`; commutes become `Verkehrsmittel`.
- **Existing Garmin names in the description** when `add_old_garmin_name_to_description = true`.

The script only changes activities that need updating. It does not create, upload, or delete activities in either service.

## Safe Activity Matching

Each Strava activity is matched with one existing Garmin activity by:

1. Start time, within the configured tolerance.
2. Sport type, unless `ignore_sport_type = true` (recomended).

Ambiguous matches and activities without exactly one Garmin match are skipped. Use `--dry-run` to inspect proposed changes before updating Garmin.

Other safeguards include:

- Optional protection for existing Garmin text with `overwrite = false` or `--no-overwrite`.
- Garmin description truncation at Garmin's 2,000 UTF-16-character limit.
- Automatic retry of temporary Garmin/Cloudflare HTTP 504 errors, using Garmin's requested retry delay.
- Clear errors for missing setup, expired Strava credentials, Strava rate limits, and Garmin login failures.

## Requirements

- Windows (for the provided batch files and optional Windows Task Scheduler automation)
- Python 3.11 or later
- A Strava API application
- A Garmin Connect account

Install the Python dependency with:

```powershell
py -m pip install -r requirements.txt
```

## Setup

Choose the automatic setup for the quickest first run, or manual setup when you want to control each step.

### Automatic Setup (Recommended)

Double-click `setup.bat`, or run it from PowerShell:

```powershell
.\setup.bat
```

The interactive installer can:

1. Install the Python requirements.
2. Copy `config.toml.example` to `config.toml` when no configuration exists.
3. Start Strava authorization.
4. Start Garmin Connect login.
5. Register automatic synchronization at Windows sign-in.

You can skip optional installer steps. Strava and Garmin authorization are still required before a successful sync.

### Manual Setup

#### 1. Install the dependency

```powershell
py -m pip install -r requirements.txt
```

#### 2. Create your configuration

```powershell
Copy-Item config.toml.example config.toml
```

Review and adjust `config.toml` before the first sync.

#### 3. Connect Strava

Create a Strava API application, then set its authorization callback domain and redirect URI to:

```text
http://localhost:8765/callback
```

Run the setup script and enter the application's Client ID and Client Secret. It opens a browser for Strava authorization and saves the token locally.

```powershell
py setup_strava.py
```

#### 4. Connect Garmin Connect

Run the Garmin setup script, enter your Garmin account details, and provide an MFA code when Garmin requests one.

```powershell
py setup_garmin.py
```

## Configuration Reference

`config.toml` controls normal synchronization runs.

| Setting | Script fallback | Meaning |
| --- | --- | --- |
| `limit` | `10` | Number of most recent activities to check when no date range is supplied. |
| `match_tolerance_minutes` | `5` | Maximum permitted difference between Strava and Garmin start times. |
| `ignore_sport_type` | `false` | Match by time only; useful when Strava and Garmin use different sport keys. |
| `overwrite` | `true` | Replace existing Garmin names and descriptions. Set to `false` to fill empty fields only. |
| `sync_name` | `true` | Copy activity names. |
| `sync_description` | `true` | Copy descriptions. |
| `sync_event_type` | `false` | Copy supported Strava classifications to Garmin event categories. |
| `add_old_garmin_name_to_description` | `false` | Append the prior Garmin name to the copied description. |
| `startup_delay_minutes` | `0` | Delay an automated sign-in run. |
| `log_level` | `"INFO"` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, or `ERROR`. |

Command-line options override the applicable configuration settings for that run.

## Run a Strava to Garmin Sync

### Preview Changes First

```powershell
py sync.py --dry-run
```

`--dry-run` lists the changes without modifying Garmin Connect.

### Sync Recent Activities

```powershell
py sync.py
py sync.py --limit 5
```

### Sync an Inclusive UTC Date Range

```powershell
py sync.py --start-date 2026-08-01 --end-date 2026-08-28
py sync.py --start-date 2026-08-01
```

Dates use `YYYY-MM-DD` and UTC calendar dates. If `--end-date` is omitted, the current date is used. `--end-date` requires `--start-date`.

### Adjust Matching or Logging for One Run

```powershell
py sync.py --match-tolerance 10 --log-level DEBUG
py sync.py --no-overwrite
py sync.py --config .\config.toml
```

## Command Reference

### `sync.py`

Synchronizes Strava activity metadata to Garmin Connect.

| Command | Purpose |
| --- | --- |
| `py sync.py` | Sync using `config.toml`. |
| `py sync.py --help` | Show every available option. |
| `py sync.py --config PATH` | Use a different TOML configuration file. |
| `py sync.py --limit NUMBER` | Check a number of recent activities. |
| `py sync.py --start-date YYYY-MM-DD` | Sync from a date through today. |
| `py sync.py --start-date YYYY-MM-DD --end-date YYYY-MM-DD` | Sync an inclusive UTC date range. |
| `py sync.py --match-tolerance MINUTES` | Override the matching tolerance. |
| `py sync.py --overwrite` | Replace existing Garmin names and descriptions. |
| `py sync.py --no-overwrite` | Preserve existing Garmin names and descriptions. |
| `py sync.py --dry-run` | Preview updates without writing to Garmin. |
| `py sync.py --add-old-garmin-name-to-description` | Append the original Garmin name to copied descriptions. |
| `py sync.py --log-level LEVEL` | Set `DEBUG`, `INFO`, `WARNING`, or `ERROR` logging. |

### `manual_sync.py` and `Strava2Garmin.bat`

`manual_sync.py` provides an interactive manual run. It lets you choose either an inclusive date range or a number of recent activities, validates entries, and then calls `sync.py`.

#### `Strava2Garmin.bat`

For a double-clickable launcher, use:

```powershell
.\Strava2Garmin.bat
```

The batch file provides a convenient Windows launcher that:

- Changes to the script directory automatically (no need to navigate first)
- Runs `manual_sync.py` for interactive sync options
- Keeps the console window open after completion so you can review the results
- Requires no command-line knowledge—just double-click to start

This is the easiest way to run a manual sync on Windows without opening a terminal.

### `setup.bat`

Runs the interactive automatic setup described above. It is the fastest way to install dependencies, configure both services, and optionally enable scheduled startup.

### `setup_strava.py`

Runs the Strava OAuth flow on `http://localhost:8765/callback`, stores its token locally, and refreshes it automatically during later syncs when possible. Run it again if Strava authorization expires or becomes invalid.

### `setup_garmin.py`

Authenticates with Garmin Connect and stores the Garmin session tokens locally. Run it again after Garmin login or token failures.

### `setup_startup.ps1` and `startup_launcher.py`

Enable automatic synchronization after Windows sign-in:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_startup.ps1
```

`setup_startup.ps1` creates or replaces the Windows Scheduled Task named `Strava2Garmin Sync`. At sign-in, it runs `startup_launcher.py`, which waits for `startup_delay_minutes`, runs `sync.py`, and records failures in `%APPDATA%\Strava2Garmin\startup-error.log`. On Windows, it also shows a desktop error message when an automated run fails.

Manual `sync.py` runs do not wait for the startup delay.

## Local Credentials and Data

Strava and Garmin credentials are stored outside the project directory under:

```text
%APPDATA%\Strava2Garmin\
```

This directory contains the Strava token, Garmin tokens, and any startup error log. Keep these files private and do not commit them.

## Troubleshooting

| Problem | What to do |
| --- | --- |
| Strava is not configured or the token is invalid | Run `py setup_strava.py` again. |
| Garmin is not configured or login fails | Run `py setup_garmin.py` again. |
| No unique Garmin activity is found | Check the start time, sport type, and `match_tolerance_minutes`; use `--dry-run` and `--log-level DEBUG`. |
| Strava rate limit reached | Wait and run the command later. |
| Garmin HTTP 504 | The script retries temporary failures automatically; try again later if retries are exhausted. |
| Automated startup fails | Check `%APPDATA%\Strava2Garmin\startup-error.log`. |

## License

No license file is currently included in this repository.

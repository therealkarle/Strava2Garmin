# Strava2Garmin

Überträgt Namen und Beschreibungen der letzten Strava-Aktivitäten auf die passenden, bereits vorhandenen Garmin-Aktivitäten.

## Einrichtung

Voraussetzung ist Python 3.11+.

```powershell
py -m pip install -r requirements.txt
Copy-Item config.toml.example config.toml
py setup_strava.py
py setup_garmin.py
```

Für Strava wird eine API-Anwendung mit `http://localhost:8765/callback` als Callback-URL benötigt. Das Garmin-Script fragt den MFA-Code bei Bedarf interaktiv ab.

## Manueller Lauf

```powershell
py sync.py --dry-run
py sync.py --limit 5
py sync.py --match-tolerance 10 --log-level DEBUG
```

Die Strava-Aktivität wird anhand von Startzeit und Sportart genau einer Garmin-Aktivität zugeordnet. Mit `ignore_sport_type = true` wird die Sportart ignoriert und nur die Startzeit verwendet. Mehrdeutige Treffer werden übersprungen. Mit `--no-overwrite` werden vorhandene Garmin-Texte geschützt.

## Autostart

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_startup.ps1
```

Die Aufgabe startet beim Windows-Login; `startup_delay_minutes` aus `config.toml` verzögert den eigentlichen Sync.

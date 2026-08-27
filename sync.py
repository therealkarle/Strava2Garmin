"""Copy names and descriptions from recent Strava activities to Garmin."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback is not supported
    tomllib = None


APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "Strava2Garmin"
STRAVA_TOKEN_FILE = APP_DIR / "strava-token.json"
GARMIN_TOKEN_DIR = APP_DIR / "garmin-tokens"
STRAVA_API = "https://www.strava.com/api/v3"
GARMIN_DESCRIPTION_MAX_LENGTH = 2000


@dataclass(frozen=True)
class Activity:
    id: str
    start_time: dt.datetime
    sport: str
    name: str
    description: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--match-tolerance", type=int, dest="match_tolerance_minutes")
    overwrite = parser.add_mutually_exclusive_group()
    overwrite.add_argument("--overwrite", action="store_true", default=None)
    overwrite.add_argument("--no-overwrite", action="store_false", dest="overwrite")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--startup-delay", type=int, dest="startup_delay_minutes")
    parser.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("Python 3.11 oder neuer wird benötigt.")
    try:
        with path.open("rb") as handle:
            config = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Config-Datei nicht gefunden: {path}") from exc
    config.setdefault("limit", 10)
    config.setdefault("match_tolerance_minutes", 5)
    config.setdefault("ignore_sport_type", False)
    config.setdefault("overwrite", True)
    config.setdefault("startup_delay_minutes", 0)
    config.setdefault("log_level", "INFO")
    config["dry_run"] = False
    if not isinstance(config["limit"], int) or config["limit"] < 1:
        raise RuntimeError("limit muss eine positive Ganzzahl sein.")
    if config["match_tolerance_minutes"] < 0:
        raise RuntimeError("match_tolerance_minutes darf nicht negativ sein.")
    return config


def apply_overrides(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    result = dict(config)
    for key in ("limit", "match_tolerance_minutes", "overwrite", "startup_delay_minutes", "log_level"):
        value = getattr(args, key, None)
        if value is not None:
            result[key] = value
    result["dry_run"] = bool(args.dry_run)
    if result["limit"] < 1 or result["match_tolerance_minutes"] < 0:
        raise ValueError("limit muss positiv sein und match_tolerance_minutes darf nicht negativ sein.")
    return result


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)


def normalize_sport(value: str | None) -> str:
    value = (value or "").lower().replace(" ", "_").replace("-", "_")
    aliases = {"run": "running", "ride": "cycling", "virtualride": "cycling", "walk": "walking"}
    return aliases.get(value, value)


def find_match(
    source: Activity,
    candidates: list[Activity],
    tolerance_minutes: int,
    *,
    ignore_sport_type: bool = False,
) -> Activity | None:
    tolerance = dt.timedelta(minutes=tolerance_minutes)
    matches = [
        candidate
        for candidate in candidates
        if (ignore_sport_type or normalize_sport(candidate.sport) == normalize_sport(source.sport))
        and abs(candidate.start_time - source.start_time) <= tolerance
    ]
    return matches[0] if len(matches) == 1 else None


def build_updates(source: Activity, target: Activity, *, overwrite: bool) -> list[tuple[str, str]]:
    updates: list[tuple[str, str]] = []
    if overwrite or not target.name:
        if target.name != source.name:
            updates.append(("Name", source.name))
    if overwrite or not target.description:
        if target.description != source.description:
            updates.append(("Beschreibung", source.description))
    return updates


def set_activity_description(garmin: Any, activity_id: str, description: str) -> Any:
    units = 0
    limited_description = []
    for char in description:
        char_units = 2 if ord(char) > 0xFFFF else 1
        if units + char_units > GARMIN_DESCRIPTION_MAX_LENGTH:
            break
        limited_description.append(char)
        units += char_units
    description = "".join(limited_description)
    return garmin.client.put(
        "connectapi",
        f"{garmin.garmin_connect_activity}/{activity_id}",
        json={"activityId": activity_id, "description": description},
        api=True,
    )


def _json_request(url: str, *, token: str, method: str = "GET", data: bytes | None = None) -> Any:
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError("Strava-Token ist ungültig oder abgelaufen; setup_strava.py erneut ausführen.") from exc
        if exc.code == 429:
            raise RuntimeError("Strava-Rate-Limit erreicht; später erneut versuchen.") from exc
        raise RuntimeError(f"Strava API-Fehler HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Strava-Netzwerkfehler: {exc.reason}") from exc


def _strava_token() -> str:
    try:
        token = json.loads(STRAVA_TOKEN_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise RuntimeError("Strava ist nicht eingerichtet; zuerst setup_strava.py ausführen.") from exc
    if token.get("expires_at", 0) <= int(time.time()) and token.get("refresh_token"):
        form = urllib.parse.urlencode(
            {
                "client_id": token.get("client_id", ""),
                "client_secret": token.get("client_secret", ""),
                "refresh_token": token["refresh_token"],
                "grant_type": "refresh_token",
            }
        ).encode()
        request = urllib.request.Request("https://www.strava.com/oauth/token", data=form, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                refreshed = json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError("Strava-Token konnte nicht erneuert werden; setup_strava.py erneut ausführen.") from exc
        refreshed.update({"client_id": token.get("client_id"), "client_secret": token.get("client_secret")})
        STRAVA_TOKEN_FILE.write_text(json.dumps(refreshed, indent=2), encoding="utf-8")
        token = refreshed
    try:
        return token["access_token"]
    except KeyError as exc:
        raise RuntimeError("Strava-Token ist unvollständig; setup_strava.py erneut ausführen.") from exc


def load_strava_activities(limit: int) -> list[Activity]:
    token = _strava_token()
    query = urllib.parse.urlencode({"per_page": limit, "page": 1})
    rows = _json_request(f"{STRAVA_API}/athlete/activities?{query}", token=token)
    return [
        Activity(
            id=str(row["id"]),
            start_time=parse_time(row["start_date"]),
            sport=row.get("sport_type") or row.get("type", ""),
            name=row.get("name") or "",
            description=(
                row.get("description")
                or _json_request(f"{STRAVA_API}/activities/{row['id']}", token=token).get("description")
                or ""
            ),
        )
        for row in rows[:limit]
    ]


def load_garmin_activities(limit: int) -> tuple[Any, list[Activity]]:
    try:
        from garminconnect import Garmin
    except ImportError as exc:
        raise RuntimeError("python-garminconnect fehlt; pip install -r requirements.txt ausführen.") from exc
    if not GARMIN_TOKEN_DIR.exists():
        raise RuntimeError("Garmin ist nicht eingerichtet; zuerst setup_garmin.py ausführen.")
    client = Garmin()
    try:
        client.login(tokenstore=str(GARMIN_TOKEN_DIR))
        rows = client.get_activities(0, limit)
    except Exception as exc:
        raise RuntimeError("Garmin-Login/API fehlgeschlagen; setup_garmin.py erneut ausführen oder später versuchen.") from exc
    activities = [
        Activity(
            id=str(row["activityId"]),
            start_time=parse_time(row.get("startTimeGMT") or row["startTimeLocal"]),
            sport=((row.get("activityType") or {}).get("typeKey") or ""),
            name=row.get("activityName") or "",
            description=row.get("description") or "",
        )
        for row in rows
        if row.get("activityId") is not None and (row.get("startTimeGMT") or row.get("startTimeLocal"))
    ]
    return client, activities


def sync(config: dict[str, Any]) -> int:
    if config["startup_delay_minutes"]:
        logging.info("Warte %s Minuten vor dem Start.", config["startup_delay_minutes"])
        time.sleep(config["startup_delay_minutes"] * 60)
    strava = load_strava_activities(config["limit"])
    garmin, targets = load_garmin_activities(config["limit"])
    changed = 0
    for source in strava:
        target = find_match(
            source,
            targets,
            config["match_tolerance_minutes"],
            ignore_sport_type=config["ignore_sport_type"],
        )
        if target is None:
            logging.warning("Keine eindeutige Garmin-Aktivität für Strava %s (%s).", source.id, source.name)
            continue
        updates = build_updates(source, target, overwrite=config["overwrite"])
        if not updates:
            logging.info("Unverändert: %s", source.name)
            continue
        logging.info("%s -> Garmin %s: %s", source.name, target.id, ", ".join(label for label, _ in updates))
        if not config["dry_run"]:
            for label, value in updates:
                if label == "Name":
                    garmin.set_activity_name(target.id, value)
                else:
                    set_activity_description(garmin, target.id, value)
        changed += 1
    return changed


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = apply_overrides(load_config(args.config), args)
        logging.basicConfig(level=getattr(logging, config["log_level"]), format="%(asctime)s %(levelname)s %(message)s")
        changed = sync(config)
        logging.info("Fertig: %s Aktivität(en) geändert%s.", changed, " (Dry-Run)" if config["dry_run"] else "")
        return 0
    except (RuntimeError, ValueError) as exc:
        logging.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

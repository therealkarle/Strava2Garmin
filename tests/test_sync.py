import datetime as dt

from sync import (
    Activity,
    apply_overrides,
    build_updates,
    find_match,
    parse_args,
)


def activity(activity_id, start, sport="RUNNING", name="old", description="old"):
    return Activity(
        id=activity_id,
        start_time=dt.datetime.fromisoformat(start),
        sport=sport,
        name=name,
        description=description,
    )


def test_find_match_requires_unique_time_and_sport_match():
    source = activity("s1", "2026-08-27T10:00:00+00:00", name="New")
    candidates = [
        activity("g1", "2026-08-27T10:03:00+00:00"),
        activity("g2", "2026-08-27T10:04:00+00:00"),
        activity("g3", "2026-08-27T10:02:00+00:00", sport="CYCLING"),
    ]

    assert find_match(source, candidates, tolerance_minutes=5) is None
    assert find_match(source, candidates[:1], tolerance_minutes=5).id == "g1"


def test_find_match_can_ignore_sport_type():
    source = activity("s1", "2026-08-27T10:00:00+00:00", sport="Ride")
    target = activity("g1", "2026-08-27T10:00:30+00:00", sport="road_biking")

    assert find_match(source, [target], tolerance_minutes=5, ignore_sport_type=True) == target


def test_cli_overrides_config_values():
    config = {
        "limit": 10,
        "match_tolerance_minutes": 5,
        "overwrite": True,
        "startup_delay_minutes": 10,
        "log_level": "INFO",
    }
    args = parse_args(["--limit", "2", "--no-overwrite", "--dry-run", "--log-level", "DEBUG"])

    result = apply_overrides(config, args)

    assert result == {
        "limit": 2,
        "match_tolerance_minutes": 5,
        "overwrite": False,
        "startup_delay_minutes": 10,
        "log_level": "DEBUG",
        "dry_run": True,
    }


def test_build_updates_only_returns_changed_fields():
    source = activity("s1", "2026-08-27T10:00:00+00:00", name="Same", description="new")
    target = activity("g1", "2026-08-27T10:00:30+00:00", name="Same", description="old")

    assert build_updates(source, target, overwrite=True) == [("Beschreibung", "new")]

import datetime as dt
from pathlib import Path

from sync import (
    Activity,
    apply_overrides,
    build_updates,
    find_match,
    load_config,
    load_strava_activities,
    set_activity_description,
    set_activity_event_type,
    parse_args,
    translate_event_type,
)


def activity(activity_id, start, sport="RUNNING", name="old", description="old", workout_type=None, event_type=""):
    return Activity(
        id=activity_id,
        start_time=dt.datetime.fromisoformat(start),
        sport=sport,
        name=name,
        description=description,
        workout_type=workout_type,
        event_type=event_type,
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
    unrelated = activity("g2", "2026-08-27T11:00:00+00:00", sport="hiking")

    assert find_match(source, [target, unrelated], tolerance_minutes=5, ignore_sport_type=True) == target


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


def test_load_strava_activities_reads_description_from_activity_detail(monkeypatch):
    responses = iter([
        [{"id": 42, "start_date": "2026-08-27T10:00:00Z", "sport_type": "Run", "name": "Morning run"}],
        {"description": "Great run"},
    ])
    monkeypatch.setattr("sync._strava_token", lambda: "token")
    monkeypatch.setattr("sync._json_request", lambda *args, **kwargs: next(responses))

    activities = load_strava_activities(1)

    assert activities[0].description == "Great run"


def test_set_activity_description_uses_garmin_activity_endpoint():
    calls = []

    class Client:
        def put(self, *args, **kwargs):
            calls.append((args, kwargs))

    class Garmin:
        client = Client()
        garmin_connect_activity = "/activity-service/activity"

    set_activity_description(Garmin(), "42", "Great run")

    assert calls == [
        (("connectapi", "/activity-service/activity/42"), {
            "json": {"activityId": "42", "description": "Great run"},
            "api": True,
        })
    ]


def test_set_activity_description_limits_text_to_garmin_maximum():
    payload = {}

    class Client:
        def put(self, *args, **kwargs):
            payload.update(kwargs["json"])

    class Garmin:
        client = Client()
        garmin_connect_activity = "/activity-service/activity"

    set_activity_description(Garmin(), "42", "x" * 2001)

    assert payload["description"] == "x" * 2000


def test_set_activity_description_counts_non_bmp_characters_as_two_units():
    payload = {}

    class Client:
        def put(self, *args, **kwargs):
            payload.update(kwargs["json"])

    class Garmin:
        client = Client()
        garmin_connect_activity = "/activity-service/activity"

    set_activity_description(Garmin(), "42", "x" * 1998 + "𝘀" * 3)

    assert len(payload["description"].encode("utf-16-le")) // 2 == 2000


def test_build_updates_only_returns_changed_fields():
    source = activity("s1", "2026-08-27T10:00:00+00:00", name="Same", description="new")
    target = activity("g1", "2026-08-27T10:00:30+00:00", name="Same", description="old")

    assert build_updates(source, target, overwrite=True) == [("Description", "new")]


def test_build_updates_can_disable_name_sync():
    source = activity("s1", "2026-08-27T10:00:00+00:00", name="new", description="same")
    target = activity("g1", "2026-08-27T10:00:00+00:00", name="old", description="same")

    assert build_updates(source, target, overwrite=True, sync_name=False) == []


def test_build_updates_can_disable_description_sync():
    source = activity("s1", "2026-08-27T10:00:00+00:00", name="same", description="new")
    target = activity("g1", "2026-08-27T10:00:00+00:00", name="same", description="old")

    assert build_updates(source, target, overwrite=True, sync_description=False) == []


def test_disabling_description_sync_also_disables_old_name_append():
    source = activity("s1", "2026-08-27T10:00:00+00:00", name="new", description="new")
    target = activity("g1", "2026-08-27T10:00:00+00:00", name="old", description="")

    assert build_updates(
        source,
        target,
        overwrite=True,
        sync_name=False,
        sync_description=False,
        add_old_garmin_name=True,
    ) == []

def test_build_updates_preserves_old_garmin_name_at_end_of_description():
    source = activity("s1", "2026-08-27T10:00:00+00:00", name="Old Garmin name", description="Strava description")
    target = activity("g1", "2026-08-27T10:00:00+00:00", name="Old Garmin name", description="")

    assert build_updates(
        source,
        target,
        overwrite=True,
        add_old_garmin_name=True,
    ) == [("Description", "Strava description\n\nOldGarminName: Old Garmin name")]

def test_old_garmin_name_takes_priority_over_description_limit():
    source = activity("s1", "2026-08-27T10:00:00+00:00", name="Old Garmin name", description="x" * 2000)
    target = activity("g1", "2026-08-27T10:00:00+00:00", name="Old Garmin name", description="")

    description = build_updates(
        source,
        target,
        overwrite=True,
        add_old_garmin_name=True,
    )[0][1]

    assert description.endswith("\n\nOldGarminName: Old Garmin name")
    assert len(description.encode("utf-16-le")) // 2 == 2000

def test_active_config_enables_old_garmin_name_append():
    assert load_config(Path("config.toml"))["add_old_garmin_name_to_description"] is True


def test_translate_strava_event_types_to_garmin_categories():
    assert translate_event_type(1) == "Wettkampf"
    assert translate_event_type(2) == "Training"
    assert translate_event_type(3) == "Training"
    assert translate_event_type(None) is None
    assert translate_event_type(None, True) == "Verkehrsmittel"


def test_set_activity_event_type_uses_garmin_event_type_payload():
    payload = {}

    class Client:
        def put(self, *args, **kwargs):
            payload.update(kwargs["json"])

    class Garmin:
        client = Client()
        garmin_connect_activity = "/activity-service/activity"

    set_activity_event_type(Garmin(), "42", "Verkehrsmittel")
    assert payload == {
        "activityId": "42",
        "eventTypeDTO": {"typeId": 5, "typeKey": "transportation"},
    }


def test_build_updates_can_optionally_sync_event_type():
    source = activity("s1", "2026-08-27T10:00:00+00:00", workout_type=1)
    target = activity("g1", "2026-08-27T10:00:00+00:00", event_type="training")
    assert build_updates(source, target, overwrite=False, sync_event_type=True) == [("EventType", "Wettkampf")]


def test_build_updates_skips_matching_garmin_event_type():
    source = activity("s1", "2026-08-27T10:00:00+00:00", workout_type=3)
    target = activity("g1", "2026-08-27T10:00:00+00:00", event_type="training")
    assert build_updates(source, target, overwrite=False, sync_event_type=True) == []

"""Tests for playlist pagination, de-duplication and expiry handling."""

import datetime

import pytest

pytest.importorskip("beets")

from beets import ui  # noqa: E402

from beetsplug.listenbrainz import ListenBrainzPlugin  # noqa: E402

EXT = "https://musicbrainz.org/doc/jspf#playlist"


class RecordingLog:
    def __init__(self):
        self.warnings = []

    def warning(self, message, *args):
        self.warnings.append(message.format(*args) if args else str(message))

    def debug(self, message, *args):
        pass


@pytest.fixture
def plugin(monkeypatch):
    from beets import config

    # confuse views are incompatible with monkeypatch.setitem
    config["plugins"] = ["listenbrainz"]
    config["listenbrainz"]["token"] = "test-token"
    config["listenbrainz"]["username"] = "test-user"
    instance = ListenBrainzPlugin()
    instance._log = RecordingLog()
    return instance


def entry(pid, title, modified, expires=None):
    return {
        "playlist": {
            "creator": "listenbrainz",
            "title": title,
            "date": modified,
            "identifier": f"https://listenbrainz.org/playlist/{pid}",
            "extension": {
                EXT: {
                    "created_for": "test-user",
                    "last_modified_at": modified,
                    "additional_metadata": {"expires_at": expires} if expires else {},
                }
            },
        }
    }


JAMS_OLD = entry(
    "aaaa",
    "Weekly Jams for u, week of 2026-10-12 Mon",
    "2026-10-13T12:31:11.238470+00:00",
    "2026-10-27T12:31:09+00:00",
)
JAMS_NEW = entry(
    "bbbb",
    "Weekly Jams for u, week of 2026-10-12 Mon",
    "2026-10-13T12:32:20.593994+00:00",
    "2026-10-27T12:32:19+00:00",
)
EXPLORATION = entry(
    "cccc",
    "Weekly Exploration for u, week of 2026-10-12 Mon",
    "2026-10-13T12:34:38+00:00",
    "2026-10-27T12:34:36+00:00",
)
YEAR_END = entry("dddd", "Top Discoveries of 2025 for u", "2026-02-22T10:41:57+00:00")


def jams_only(expires_at):
    return {
        "type": "Jams",
        "date": datetime.date(2026, 10, 12),
        "identifier": "bbbb",
        "expires_at": expires_at,
    }


def test_pagination_collects_every_page(plugin, monkeypatch):
    pages = {
        0: {"playlists": [JAMS_OLD, JAMS_NEW], "playlist_count": 3, "offset": 0},
        2: {"playlists": [EXPLORATION], "playlist_count": 3, "offset": 2},
    }
    requested = []

    def fake(url, params=None):
        requested.append(params["offset"])
        return pages[params["offset"]]

    monkeypatch.setattr(plugin, "_make_request", fake)
    resp = plugin.get_playlists_createdfor("test-user", count=2)

    ids = [p["playlist"]["identifier"][-4:] for p in resp["playlists"]]
    assert ids == ["aaaa", "bbbb", "cccc"]
    assert requested == [0, 2]


def test_failed_request_returns_no_data(plugin, monkeypatch):
    monkeypatch.setattr(plugin, "_make_request", lambda url, params=None: None)
    assert plugin.get_playlists_createdfor("test-user") is None
    assert plugin.get_listenbrainz_playlists() == []


def test_keeps_newest_playlist_per_type_and_week(plugin, monkeypatch):
    monkeypatch.setattr(
        plugin,
        "get_playlists_createdfor",
        lambda username, count=100: {
            "playlists": [JAMS_OLD, JAMS_NEW, EXPLORATION, YEAR_END]
        },
    )
    playlists = plugin.get_listenbrainz_playlists()

    assert [(p["type"], str(p["date"]), p["identifier"]) for p in playlists] == [
        ("Exploration", "2026-10-12", "cccc"),
        ("Jams", "2026-10-12", "bbbb"),
    ]


def test_warns_when_selected_playlist_is_expired(plugin, monkeypatch):
    expired = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    monkeypatch.setattr(
        plugin, "get_listenbrainz_playlists", lambda: [jams_only(expired.isoformat())]
    )
    monkeypatch.setattr(plugin, "get_playlist", lambda identifier: {})
    monkeypatch.setattr(plugin, "get_tracks_from_playlist", lambda playlist: ["track"])

    assert plugin.get_weekly_jams() == ["track"]
    assert plugin._log.warnings == [
        f"Weekly Jams playlist for 2026-10-12 expired on {expired.date()};"
        " ListenBrainz has not generated a newer one."
    ]


def test_no_warning_when_selected_playlist_is_current(plugin, monkeypatch):
    future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    monkeypatch.setattr(
        plugin, "get_listenbrainz_playlists", lambda: [jams_only(future.isoformat())]
    )
    monkeypatch.setattr(plugin, "get_playlist", lambda identifier: {})
    monkeypatch.setattr(plugin, "get_tracks_from_playlist", lambda playlist: ["track"])

    assert plugin.get_weekly_jams() == ["track"]
    assert plugin._log.warnings == []


def test_last_week_needs_two_weeks(plugin, monkeypatch):
    monkeypatch.setattr(plugin, "get_listenbrainz_playlists", lambda: [jams_only(None)])
    with pytest.raises(ui.UserError):
        plugin.get_last_weekly_jams()

"""Beets >= 2.5 treats plugins with a `data_source` attribute as metadata sources."""

import pytest

pytest.importorskip("beets")

from beets.metadata_plugins import find_metadata_source_plugins  # noqa: E402

from beetsplug.listenbrainz import ListenBrainzPlugin  # noqa: E402


def test_no_data_source_attribute():
    assert not hasattr(ListenBrainzPlugin, "data_source")


def test_id_lookup_methods_are_consistent():
    if hasattr(ListenBrainzPlugin, "albums_for_ids"):
        assert hasattr(ListenBrainzPlugin, "album_for_id")


def test_not_registered_as_metadata_source():
    from beets import config, plugins

    config["plugins"] = ["listenbrainz"]
    config["listenbrainz"]["token"] = "test-token"
    config["listenbrainz"]["username"] = "test-user"

    try:  # beets >= 2.0
        plugins.load_plugins()
    except TypeError:  # beets < 2.0 took the plugin names
        plugins.load_plugins(config["plugins"].as_str_seq())

    assert any(isinstance(p, ListenBrainzPlugin) for p in plugins.find_plugins())
    assert not any(
        isinstance(p, ListenBrainzPlugin) for p in find_metadata_source_plugins()
    )

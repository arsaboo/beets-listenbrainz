"""
Adds Listenbrainz support to Beets.
"""

import requests
import datetime
from beets import config, ui
from beets.plugins import BeetsPlugin
import musicbrainzngs as mb

mb.set_useragent("ListenBrainz", "1.0", "https://github.com/arsaboo/beets-listenbrainz")


class ListenBrainzPlugin(BeetsPlugin):
    data_source = "ListenBrainz"
    ROOT = "http://api.listenbrainz.org/1/"

    def __init__(self):
        super().__init__()
        self.token = self.config["token"].get()
        self.username = self.config["username"].get()
        self.AUTH_HEADER = {"Authorization": f"Token {self.token}"}
        config["listenbrainz"]["token"].redact = True

    def commands(self):
        """Add beet UI commands to interact with ListenBrainz."""
        lbupdate_cmd = ui.Subcommand(
            "lbupdate", help=f"Update {self.data_source} views"
        )

        def func(lib, opts, args):
            items = lib.items(ui.decargs(args))
            self._lbupdate(items, ui.should_write())

        lbupdate_cmd.func = func
        return [lbupdate_cmd]

    def _lbupdate(self, items, write):
        """Obtain view count from Listenbrainz."""
        ls = self.get_listenbrainz_playlists(self.username)
        self._log.debug(f"Found {len(ls)} playlists")

    def _make_request(self, url):
        try:
            response = requests.get(
                url=url,
                headers=self.AUTH_HEADER,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._log.debug(f"Invalid Search Error: {e}")
            return None

    def get_playlists_createdfor(self, username):
        """Returns a list of playlists created by a user."""
        url = f"{self.ROOT}/user/{username}/playlists/createdfor"
        return self._make_request(url)

    def get_listenbrainz_playlists(self):
        resp = self.get_playlists_createdfor(self.username)
        playlists = resp.get("playlists")
        listenbrainz_playlists = []

        for playlist in playlists:
            playlist_info = playlist.get("playlist")
            if playlist_info.get("creator") == "listenbrainz":
                title = playlist_info.get("title")
                self._log.debug(f"Playlist title: {title}")
                playlist_type = "Exploration" if "Exploration" in title else "Jams"
                if "week of" in title:
                    date_str = title.split("week of ")[1].split(" ")[0]
                    date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                else:
                    continue
                identifier = playlist_info.get("identifier")
                id = identifier.split("/")[-1]
                listenbrainz_playlists.append(
                    {"type": playlist_type, "date": date, "identifier": id}
                )
        listenbrainz_playlists = sorted(listenbrainz_playlists, key=lambda x: x["type"])
        listenbrainz_playlists = sorted(
            listenbrainz_playlists, key=lambda x: x["date"], reverse=True
        )
        for playlist in listenbrainz_playlists:
            self._log.debug(f'Playlist: {playlist["type"]} - {playlist["date"]}')
        return listenbrainz_playlists

    def get_playlist(self, identifier):
        """Returns a playlist."""
        url = f"{self.ROOT}/playlist/{identifier}"
        return self._make_request(url)

    def get_tracks_from_playlist(self, playlist):
        """This function returns a list of tracks in the playlist."""
        tracks = []
        for track in playlist.get("playlist").get("track"):
            tracks.append(
                {
                    "artist": track.get("creator"),
                    "identifier": track.get("identifier").split("/")[-1],
                    "title": track.get("title"),
                }
            )
        return self.get_track_info(tracks)

    def get_track_info(self, tracks):
        track_info = []
        for track in tracks:
            identifier = track.get("identifier")
            resp = mb.get_recording_by_id(
                identifier, includes=["releases", "artist-credits"]
            )
            recording = resp.get("recording")
            title = recording.get("title")
            artist_credit = recording.get("artist-credit", [])
            if artist_credit:
                artist = artist_credit[0].get("artist", {}).get("name")
            else:
                artist = None
            releases = recording.get("release-list", [])
            if releases:
                album = releases[0].get("title")
                date = releases[0].get("date")
                year = date.split("-")[0] if date else None
            else:
                album = None
                year = None
            track_info.append(
                {
                    "identifier": identifier,
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "year": year,
                }
            )
        return track_info

    def get_weekly_playlist(self, index):
        """Returns a list of weekly playlists based on the index."""
        playlists = self.get_listenbrainz_playlists()
        playlist = self.get_playlist(playlists[index].get("identifier"))
        return self.get_tracks_from_playlist(playlist)

    def get_weekly_exploration(self):
        """Returns a list of weekly exploration."""
        return self.get_weekly_playlist(0)

    def get_weekly_jams(self):
        """Returns a list of weekly jams."""
        return self.get_weekly_playlist(2)

    def get_last_weekly_exploration(self):
        """Returns a list of weekly exploration."""
        return self.get_weekly_playlist(1)

    def get_last_weekly_jams(self):
        """Returns a list of weekly jams."""
        return self.get_weekly_playlist(3)

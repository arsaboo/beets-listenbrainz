"""
Adds Listenbrainz support to Beets.
"""

import requests
import datetime
from beets import config, ui
from beets.plugins import BeetsPlugin

class ListenBrainzPlugin(BeetsPlugin):
    data_source = "ListenBrainz"
    ROOT = "http://api.listenbrainz.org/1/"

    def __init__(self):
        super().__init__()
        self.token = self.config["token"].get()
        self.username = self.config["username"].get()
        self.AUTH_HEADER = {"Authorization": f"Token {self.token}"}
        config['listenbrainz']['token'].redact = True

    def commands(self):
        """Add beet UI commands to interact with ListenBrainz."""
        lbupdate_cmd = ui.Subcommand(
            'lbupdate', help=f'Update {self.data_source} views')

        def func(lib, opts, args):
            items = lib.items(ui.decargs(args))
            self._lbupdate(items, ui.should_write())

        lbupdate_cmd.func = func
        return [lbupdate_cmd]

    def _lbupdate(self, items, write):
        """Obtain view count from Youtube."""
        ls = self.get_listenbrainz_playlists(self.username)
        self._log.debug('Found {} playlists', len(ls))


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
            return []

    def get_playlists_createdfor(self, username):
        """Returns a list of playlists created by a user."""
        url = f"{self.ROOT}/user/{username}/playlists/createdfor"
        return self._make_request(url)

    def get_listenbrainz_playlists(self, username):
        resp = self.get_playlists_createdfor(username)
        playlists = resp.get("playlists")
        listenbrainz_playlists = []

        for playlist in playlists:
            list = playlist.get("playlist")
            if list.get("creator") == "listenbrainz":
                title = list.get("title")
                if "Exploration" in title:
                    type = "Exploration"
                elif "Jams" in title:
                    type = "Jams"
                date = title.split("week of ")[1].split(" ")[0]
                date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
                identifier = list.get("identifier")
                id = identifier.split("/")[-1]
                listenbrainz_playlists.append(
                    {"type": type, "date": date, "identifier": id}
                )
        return listenbrainz_playlists

    def get_playlist(self, identifier):
        """Returns a playlist."""
        url = f"{self.ROOT}/1/playlist/{identifier}"
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
        return tracks

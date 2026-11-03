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
    # Not named `data_source`: beets >= 2.5 treats plugins exposing it as a
    # metadata source and calls album_for_id(), which this plugin lacks.
    SOURCE_NAME = "ListenBrainz"
    ROOT = "https://api.listenbrainz.org/1/"

    def __init__(self):
        super().__init__()
        self.token = self.config["token"].get()
        self.username = self.config["username"].get()
        self.AUTH_HEADER = {"Authorization": f"Token {self.token}"}
        config["listenbrainz"]["token"].redact = True

    def commands(self):
        """Add beet UI commands to interact with ListenBrainz."""
        lbupdate_cmd = ui.Subcommand(
            "lbupdate", help=f"Update {self.SOURCE_NAME} views"
        )

        def func(lib, opts, args):
            items = lib.items(ui.decargs(args))
            self._lbupdate(items, ui.should_write())

        lbupdate_cmd.func = func
        return [lbupdate_cmd]

    def _lbupdate(self, items, write):
        """Obtain view count from Listenbrainz."""
        ls = self.get_listenbrainz_playlists()
        self._log.debug(f"Found {len(ls)} playlists")

    def _make_request(self, url, params=None):
        try:
            response = requests.get(
                url=url,
                headers=self.AUTH_HEADER,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._log.debug(f"Invalid Search Error: {e}")
            return None

    def get_playlists_createdfor(self, username, count=100):
        """Returns all playlists created for a user, following pagination."""
        url = f"{self.ROOT}/user/{username}/playlists/createdfor"
        playlists = []
        offset = 0
        while True:
            resp = self._make_request(url, params={"count": count, "offset": offset})
            if not resp:
                break
            page = resp.get("playlists") or []
            playlists.extend(page)
            total = resp.get("playlist_count")
            offset += len(page)
            if not page or total is None or offset >= total:
                break
        if not playlists:
            return None
        return {"playlists": playlists}

    @staticmethod
    def _playlist_extension(playlist_info):
        extension = playlist_info.get("extension") or {}
        return extension.get("https://musicbrainz.org/doc/jspf#playlist") or {}

    @staticmethod
    def _parse_timestamp(value):
        try:
            parsed = datetime.datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed

    def get_listenbrainz_playlists(self):
        """Returns the weekly playlists, newest first, one per type and week."""
        resp = self.get_playlists_createdfor(self.username)
        if not resp:
            self._log.warning("ListenBrainz API returned no data for playlists.")
            return []
        playlists = resp.get("playlists") or []
        if not isinstance(playlists, list):
            self._log.warning("ListenBrainz API response missing playlists list.")
            return []
        weekly = {}

        for playlist in playlists:
            playlist_info = playlist.get("playlist")
            if not playlist_info:
                continue
            if playlist_info.get("creator") == "listenbrainz":
                title = playlist_info.get("title") or ""
                self._log.debug(f"Playlist title: {title}")
                if "Weekly " not in title or "week of " not in title:
                    continue
                playlist_type = "Exploration" if "Exploration" in title else "Jams"
                date_str = title.split("week of ")[1].split(" ")[0]
                try:
                    date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    self._log.debug(f"Unparsable week in playlist title: {title}")
                    continue
                identifier = playlist_info.get("identifier")
                if not isinstance(identifier, str) or not identifier:
                    self._log.warning(
                        "ListenBrainz playlist missing valid identifier; skipping."
                    )
                    continue
                playlist_id = identifier.split("/")[-1]
                extension = self._playlist_extension(playlist_info)
                entry = {
                    "type": playlist_type,
                    "date": date,
                    "identifier": playlist_id,
                    "last_modified": extension.get("last_modified_at")
                    or playlist_info.get("date"),
                    "expires_at": (extension.get("additional_metadata") or {}).get(
                        "expires_at"
                    ),
                }
                # ListenBrainz can generate more than one playlist for the same
                # week, so keep the most recently generated one.
                previous = weekly.get((playlist_type, date))
                if previous:
                    if (entry["last_modified"] or "") <= (
                        previous["last_modified"] or ""
                    ):
                        self._log.debug(
                            f"Skipping older {playlist_type} playlist {playlist_id}"
                            f" for {date}"
                        )
                        continue
                    self._log.debug(
                        f"Replacing {previous['identifier']} with newer"
                        f" {playlist_type} playlist {playlist_id} for {date}"
                    )
                weekly[(playlist_type, date)] = entry

        listenbrainz_playlists = sorted(
            weekly.values(),
            key=lambda x: (-x["date"].toordinal(), x["type"]),
        )
        for playlist in listenbrainz_playlists:
            self._log.debug(f'Playlist: {playlist["type"]} - {playlist["date"]}')
        return listenbrainz_playlists

    def get_playlist(self, identifier):
        """Returns a playlist."""
        if not identifier:
            raise ui.UserError("ListenBrainz playlist identifier is missing.")
        url = f"{self.ROOT}/playlist/{identifier}"
        resp = self._make_request(url)
        if not resp:
            raise ui.UserError("ListenBrainz playlist request failed.")
        return resp

    def get_tracks_from_playlist(self, playlist):
        """This function returns a list of tracks in the playlist."""
        if not playlist or "playlist" not in playlist:
            raise ui.UserError("ListenBrainz playlist data is missing.")
        if "track" not in playlist.get("playlist", {}):
            raise ui.UserError("ListenBrainz playlist has no tracks.")
        tracks = []
        for track in playlist.get("playlist").get("track"):
            identifier = track.get("identifier")
            if isinstance(identifier, list):
                identifier = identifier[0]
            artist = track.get(
                "creator", "Unknown artist"
            )  # Set a default value if 'creator' key is not present
            track_dict = {
                "artist": artist,
                "identifier": identifier.split("/")[-1],
                "title": track.get("title"),
            }
            tracks.append(track_dict)
        return self.get_track_info(tracks)

    def get_track_info(self, tracks):
        track_info = []
        for track in tracks:
            identifier = track.get("identifier")
            try:
                resp = mb.get_recording_by_id(
                    identifier, includes=["releases", "artist-credits"]
                )
            except mb.MusicBrainzError as e:
                self._log.debug(
                    f"MusicBrainz lookup failed for identifier {identifier}: {e}"
                )
                continue
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

    def get_weekly_playlist(self, playlist_type, most_recent=True):
        # Fetch all playlists
        playlists = self.get_listenbrainz_playlists()
        if not playlists:
            raise ui.UserError(
                "No ListenBrainz playlists found. Check token, username, or API status."
            )
        # Filter playlists by type
        filtered_playlists = [p for p in playlists if p.get("type") == playlist_type]
        if not filtered_playlists:
            raise ui.UserError(f"No weekly {playlist_type} playlists found.")
        # Sort playlists by date in descending order
        sorted_playlists = sorted(
            filtered_playlists, key=lambda x: x["date"], reverse=True
        )
        # Select the most recent or older playlist based on the most_recent flag
        if not most_recent and len(sorted_playlists) < 2:
            raise ui.UserError(
                f"Not enough weekly {playlist_type} playlists to select last week."
            )
        selected_playlist = sorted_playlists[0] if most_recent else sorted_playlists[1]
        self._log.debug(
            f"Selected playlist: {selected_playlist['type']}"
            f" - {selected_playlist['date']}"
        )
        expires = self._parse_timestamp(selected_playlist.get("expires_at"))
        if expires and expires < datetime.datetime.now(datetime.timezone.utc):
            self._log.warning(
                f"Weekly {selected_playlist['type']} playlist for"
                f" {selected_playlist['date']} expired on {expires.date()};"
                " ListenBrainz has not generated a newer one."
            )
        # Fetch and return tracks from the selected playlist
        playlist = self.get_playlist(selected_playlist.get("identifier"))
        return self.get_tracks_from_playlist(playlist)

    def get_weekly_exploration(self):
        return self.get_weekly_playlist("Exploration", most_recent=True)

    def get_weekly_jams(self):
        return self.get_weekly_playlist("Jams", most_recent=True)

    def get_last_weekly_exploration(self):
        return self.get_weekly_playlist("Exploration", most_recent=False)

    def get_last_weekly_jams(self):
        return self.get_weekly_playlist("Jams", most_recent=False)

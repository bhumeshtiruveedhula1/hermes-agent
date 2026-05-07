# core/integrations/spotify.py — Phase 14: Spotify Integration
# Uses spotipy. Install: pip install spotipy
# Pattern: matches telegram.py structure (AuditLogger, _get_config, try/except)
# NOTE: First run opens a browser for OAuth. Token is cached in .spotify_cache.

import os
import re
from pathlib import Path
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent


def _get_config() -> dict:
    """Read Spotify credentials from .env or environment."""
    env_file = Path(".env")
    cfg = {"client_id": "", "client_secret": "", "redirect_uri": ""}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("SPOTIFY_CLIENT_ID="):
                cfg["client_id"] = line.split("=", 1)[1].strip()
            elif line.startswith("SPOTIFY_CLIENT_SECRET="):
                cfg["client_secret"] = line.split("=", 1)[1].strip()
            elif line.startswith("SPOTIFY_REDIRECT_URI="):
                cfg["redirect_uri"] = line.split("=", 1)[1].strip()
    cfg["client_id"]     = cfg["client_id"]     or os.environ.get("SPOTIFY_CLIENT_ID", "")
    cfg["client_secret"] = cfg["client_secret"] or os.environ.get("SPOTIFY_CLIENT_SECRET", "")
    cfg["redirect_uri"]  = cfg["redirect_uri"]  or os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

    if not cfg["client_id"] or not cfg["client_secret"]:
        raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET not set in .env")
    return cfg


_SCOPE = " ".join([
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "playlist-read-private",
])


class SpotifyCapability:
    def __init__(self):
        self.audit = AuditLogger()
        self._sp   = None

    def _get_client(self):
        if self._sp:
            return self._sp
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
        cfg = _get_config()
        self._sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=cfg["client_id"],
            client_secret=cfg["client_secret"],
            redirect_uri=cfg["redirect_uri"],
            scope=_SCOPE,
            cache_path=".spotify_cache",
            open_browser=True,
        ))
        return self._sp

    def execute(self, *, action: str, query: str = "", **kwargs) -> str:
        try:
            sp = self._get_client()

            if action == "current":
                return self._current(sp)
            elif action == "search":
                return self._search(sp, query)
            elif action == "play":
                return self._play(sp, query)
            elif action == "pause":
                sp.pause_playback(); return "Spotify paused ⏸"
            elif action == "resume":
                sp.start_playback(); return "Spotify resumed ▶"
            elif action == "next":
                sp.next_track(); return "Skipped to next track ⏭"
            elif action == "previous":
                sp.previous_track(); return "Went back to previous track ⏮"
            elif action == "playlists":
                return self._playlists(sp)
            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            self.audit.log(AuditEvent(
                phase="plugin", action=action,
                tool_name="spotify", decision="blocked",
                metadata={"reason": str(e)}
            ))
            return f"[BLOCKED] Spotify error: {e}"

    # ── Actions ──────────────────────────────────────────────────────────

    def _current(self, sp) -> str:
        track = sp.current_playback()
        if not track or not track.get("item"):
            return "Nothing is playing on Spotify right now"
        item   = track["item"]
        artist = ", ".join(a["name"] for a in item["artists"])
        name   = item["name"]
        prog   = track.get("progress_ms", 0) // 1000
        dur    = item.get("duration_ms", 0) // 1000
        state  = "▶ Playing" if track["is_playing"] else "⏸ Paused"
        self.audit.log(AuditEvent(phase="plugin", action="current",
            tool_name="spotify_current", decision="allowed"))
        return f"{state}: {name} by {artist}  [{prog//60}:{prog%60:02d} / {dur//60}:{dur%60:02d}]"

    def _search(self, sp, query: str) -> str:
        q = re.sub(r'^query=', '', query).strip() or query
        results = sp.search(q=q, limit=5, type="track")
        tracks  = results["tracks"]["items"]
        if not tracks:
            return f"No Spotify results for: {q}"
        lines = []
        for t in tracks:
            artist = ", ".join(a["name"] for a in t["artists"])
            lines.append(f"• {t['name']} by {artist}\n  URI: {t['uri']}")
        self.audit.log(AuditEvent(phase="plugin", action="search",
            tool_name="spotify_search", decision="allowed",
            metadata={"query": q}))
        return "Spotify results:\n" + "\n".join(lines)

    def _play(self, sp, query: str) -> str:
        uri_match   = re.search(r'uri=(spotify:track:\S+)', query)
        query_clean = re.sub(r'^(?:query=|play\s+)', '', query).strip()

        uri = uri_match.group(1) if uri_match else ""

        if not uri and query_clean:
            results = sp.search(q=query_clean, limit=1, type="track")
            tracks  = results["tracks"]["items"]
            if not tracks:
                return f"[ERROR] Song not found: {query_clean}"
            uri = tracks[0]["uri"]
            song_name = f"{tracks[0]['name']} by {', '.join(a['name'] for a in tracks[0]['artists'])}"
        else:
            song_name = uri

        devices = sp.devices().get("devices", [])
        if not devices:
            return "[ERROR] No active Spotify device. Open Spotify on any device first, then try again."

        device_id = devices[0]["id"]
        sp.start_playback(device_id=device_id, uris=[uri])

        self.audit.log(AuditEvent(phase="plugin", action="play",
            tool_name="spotify_play", decision="allowed",
            metadata={"track": song_name}))
        return f"Now playing: {song_name} ▶"

    def _playlists(self, sp) -> str:
        items = sp.current_user_playlists(limit=15).get("items", [])
        if not items:
            return "No playlists found in your Spotify library"
        lines = [f"• {p['name']} ({p['tracks']['total']} tracks)" for p in items]
        self.audit.log(AuditEvent(phase="plugin", action="playlists",
            tool_name="spotify_playlists", decision="allowed"))
        return "Your Spotify playlists:\n" + "\n".join(lines)

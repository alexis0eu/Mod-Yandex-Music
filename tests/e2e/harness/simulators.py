"""
Simulators for Electron runtime, IPC bus, Discord named pipes,
and external Cascading Lyrics API endpoints.
Provides realistic, isolated in-memory test environments.
"""

import json
import time
from typing import Dict, Any, Callable, List, Optional
from .contracts import (
    TrackMetadata,
    PlayerProgress,
    PlayerState,
    LyricsPayload,
    LyricsLine,
    DISCORD_HANDSHAKE_TIMEOUT_MS,
    DISCORD_WATCHDOG_INTERVAL_MS,
    RENDERER_POLLER_SILENCE_THRESHOLD_MS,
)
from .oracles import (
    encode_discord_ipc_packet,
    decode_discord_ipc_packet,
    compute_musixmatch_signature,
    clean_lrc_metadata_tags,
    parse_lrc_timestamps,
)


class MockWebContents:
    def __init__(self, name: str):
        self.name = name
        self.sent_messages: List[Dict[str, Any]] = []
        self.is_destroyed = False

    def send(self, channel: str, *args):
        if self.is_destroyed:
            raise RuntimeError(f"Cannot send to destroyed window {self.name}")
        self.sent_messages.append({"channel": channel, "args": list(args), "timestamp": time.time()})

    def executeJavaScript(self, script: str) -> Any:
        return True


class MockBrowserWindow:
    def __init__(self, name: str):
        self.name = name
        self.webContents = MockWebContents(name)
        self.destroyed = False

    def isDestroyed(self) -> bool:
        return self.destroyed

    def destroy(self):
        self.destroyed = True
        self.webContents.is_destroyed = True


class MockElectronIPC:
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._listeners: Dict[str, List[Callable]] = {}

    def handle(self, channel: str, fn: Callable):
        self._handlers[channel] = fn

    def on(self, channel: str, fn: Callable):
        if channel not in self._listeners:
            self._listeners[channel] = []
        self._listeners[channel].append(fn)

    def remove_all_listeners(self, channel: Optional[str] = None):
        if channel:
            self._listeners.pop(channel, None)
        else:
            self._listeners.clear()

    def invoke(self, channel: str, *args) -> Any:
        if channel not in self._handlers:
            raise KeyError(f"No IPC handler registered for '{channel}'")
        return self._handlers[channel](None, *args)

    def emit_renderer_event(self, channel: str, *args):
        if channel in self._listeners:
            for fn in self._listeners[channel]:
                fn(None, *args)


class MockDiscordServer:
    """Simulates Discord desktop application named pipe server."""

    def __init__(self, pipe_id: int = 0):
        self.pipe_path = f"\\\\.\\pipe\\discord-ipc-{pipe_id}"
        self.is_running = True
        self.received_packets: List[Dict[str, Any]] = []
        self.handshake_received = False
        self.client_ready = False
        self.last_activity: Optional[Dict[str, Any]] = None

    def receive_client_packet(self, raw_bytes: bytes) -> bytes:
        if not self.is_running:
            raise ConnectionResetError("Pipe is closed/unavailable")

        opcode, length, payload_str, _ = decode_discord_ipc_packet(raw_bytes)
        payload = json.loads(payload_str)
        self.received_packets.append({"opcode": opcode, "payload": payload})

        if opcode == 0:  # Handshake
            self.handshake_received = True
            self.client_ready = True
            ready_response = json.dumps({
                "cmd": "DISPATCH",
                "data": {"v": 1, "user": {"id": "test_user_id", "username": "Tester"}},
                "evt": "READY",
            })
            return encode_discord_ipc_packet(1, ready_response)

        elif opcode == 1:  # Frame / Activity
            self.last_activity = payload
            ack_response = json.dumps({
                "cmd": payload.get("cmd", "SET_ACTIVITY"),
                "data": payload.get("args", {}),
                "evt": None,
                "nonce": payload.get("nonce"),
            })
            return encode_discord_ipc_packet(1, ack_response)

        return b""


class MockCascadingLyricsEngine:
    """
    Simulates the 3-tier cascading lyrics engine:
    1. Yandex Music Supplement API (with session cookies)
    2. Musixmatch Android Subtitles API (with HMAC-SHA1 signature)
    3. LRCLib API (get + stripped search fallback) + LRC tag cleaner
    """

    def __init__(self):
        # Database of mock responses
        self.yandex_supplement_db: Dict[str, Dict[str, Any]] = {}
        self.musixmatch_db: Dict[str, str] = {}
        self.lrclib_db: Dict[str, str] = {}
        self.user_session_cookies: Dict[str, str] = {"Session_id": "valid_session_token_123"}
        self.simulate_musixmatch_block = False
        self.simulate_network_failure = False

    def query_yandex_supplement(self, track_id: str, cookies: Dict[str, str]) -> Optional[Dict[str, Any]]:
        if self.simulate_network_failure:
            raise TimeoutError("Network timeout")

        # Supplement requires valid Session_id
        if "Session_id" not in cookies or not cookies["Session_id"]:
            return None  # Unauthenticated, cascade

        data = self.yandex_supplement_db.get(track_id)
        if not data or not data.get("lyrics"):
            return None  # No lyrics in supplement, cascade
        return data

    def query_musixmatch(self, track_title: str, artist: str, duration: int) -> Optional[str]:
        if self.simulate_network_failure or self.simulate_musixmatch_block:
            return None  # Network block or timeout, cascade

        key = f"{track_title.lower()}:{artist.lower()}"
        return self.musixmatch_db.get(key)

    def query_lrclib(self, track_title: str, artist: str) -> Optional[str]:
        if self.simulate_network_failure:
            raise TimeoutError("LRCLib timeout")

        key = f"{track_title.lower()}:{artist.lower()}"
        lrc = self.lrclib_db.get(key)
        if lrc:
            return clean_lrc_metadata_tags(lrc)

        # Fallback to search query (stripping parentheses/brackets)
        clean_title = re_strip_parentheses(track_title)
        search_key = f"{clean_title.lower()}:{artist.lower()}"
        fallback_lrc = self.lrclib_db.get(search_key)
        if fallback_lrc:
            return clean_lrc_metadata_tags(fallback_lrc)
        return None

    def fetch_lyrics(self, track_id: str, title: str, artist: str, duration: int) -> LyricsPayload:
        # Tier 1: Yandex Music Supplement
        yandex_res = self.query_yandex_supplement(track_id, self.user_session_cookies)
        if yandex_res:
            lrc_content = yandex_res["lyrics"]
            lines = parse_lrc_timestamps(lrc_content)
            return LyricsPayload(
                success=True,
                provider="yandex",
                is_lrc=len(lines) > 0,
                lyrics=lrc_content,
                sync_lyrics=lines,
            )

        # Tier 2: Musixmatch
        mxm_res = self.query_musixmatch(title, artist, duration)
        if mxm_res:
            cleaned = clean_lrc_metadata_tags(mxm_res)
            lines = parse_lrc_timestamps(cleaned)
            return LyricsPayload(
                success=True,
                provider="musixmatch",
                is_lrc=len(lines) > 0,
                lyrics=cleaned,
                sync_lyrics=lines,
            )

        # Tier 3: LRCLib
        lrclib_res = self.query_lrclib(title, artist)
        if lrclib_res:
            cleaned = clean_lrc_metadata_tags(lrclib_res)
            lines = parse_lrc_timestamps(cleaned)
            return LyricsPayload(
                success=True,
                provider="lrclib",
                is_lrc=len(lines) > 0,
                lyrics=cleaned,
                sync_lyrics=lines,
            )

        return LyricsPayload(
            success=False,
            provider="none",
            is_lrc=False,
            lyrics="",
            sync_lyrics=[],
        )


def re_strip_parentheses(text: str) -> str:
    """Helper to strip feat / remix annotations from track title for fallback search."""
    import re
    cleaned = re.sub(r"\s*[\(\[].*?[\)\]]", "", text)
    return cleaned.strip()

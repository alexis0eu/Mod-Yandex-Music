"""
Contract specifications and data structures for Yandex Music Mod.
Derived authoritatively from PROJECT.md and ORIGINAL_REQUEST.md.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

# === Feature 1-4: Font Pack Contracts ===
EMBEDDED_FONTS = [
    "JetBrains Mono",
    "Minecraft",
    "Andy Bold",
    "Terraria",  # Dual-alias pointing to Andy Bold
    "Press Start 2P",
    "VT323",
    "Uncut Sans",
]

FONT_SCALE_BOUNDS = {"min": 0.8, "max": 1.3, "default": 1.0}
INTERFACE_SCALE_BOUNDS = {"min": 0.8, "max": 1.3, "default": 1.0}

FONT_SIZE_ADJUST_PRESETS = {
    "Terraria": 0.66,
    "Minecraft": 0.55,
}

# === Feature 5-9: Discord RPC Contracts ===
DISCORD_CLIENT_ID = "120300000000000000"  # Format: 18-digit snowflake
DISCORD_PIPE_NAMES = [f"\\\\.\\pipe\\discord-ipc-{i}" for i in range(10)]
DISCORD_HANDSHAKE_TIMEOUT_MS = 5000
DISCORD_WATCHDOG_INTERVAL_MS = 15000
RENDERER_POLLER_SILENCE_THRESHOLD_MS = 3500
INSTANT_DISPATCH_THROTTLE_MS = 0  # 0ms on track switch

# === Feature 10-14: Gaming HUD Overlay Contracts ===
OVERLAY_IPC_HANDLERS = [
    "yandexMusicMod.getLastPlayerState",
    "yandexMusicMod.getLastLyrics",
]

OVERLAY_INTERPOLATION_TARGET_FPS = 60
OVERLAY_INTERPOLATION_INTERVAL_MS = 1000 // OVERLAY_INTERPOLATION_TARGET_FPS  # ~16ms, or 50ms fallback

# === Feature 15-20: Cascading Lyrics Contracts ===
LYRICS_PROVIDERS_CASCADE = ["yandex", "musixmatch", "lrclib"]
MUSIXMATCH_SECRET_KEY = "967Pn4)N3&R_GBg5$b('"
MUSIXMATCH_USER_AGENT = "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_I005DA Build/PI)"
MUSIXMATCH_APP_ID = "android-player-v1.0"
YANDEX_SUPPLEMENT_URL_TEMPLATE = "https://api.music.yandex.net/tracks/{track_id}/supplement"
LRCLIB_GET_URL = "https://lrclib.net/api/get"
LRCLIB_SEARCH_URL = "https://lrclib.net/api/search"

# === Feature 21-24: Anti-Slop Settings UI Contracts ===
MODAL_STYLE_SPECS = {
    "background": "rgba(20, 20, 24, 0.88)",
    "backdrop_filter": "blur(30px) saturate(170%)",
    "border": "1px solid rgba(255, 255, 255, 0.08)",
    "border_radius": "18px",
    "box_shadow_presence": True,
}

SIDEBAR_TABS = [
    {"id": "tab-appearance", "title": "Внешний вид"},
    {"id": "tab-fonts", "title": "Шрифты"},
    {"id": "tab-discord", "title": "Discord"},
    {"id": "tab-overlay", "title": "Оверлей"},
    {"id": "tab-lyrics", "title": "Тексты"},
    {"id": "tab-cleaner", "title": "Очистка интерфейса"},
]

SWITCH_SPECS = {
    "width_px": 36,
    "height_px": 20,
    "thumb_px": 16,
    "accent_color": "#fed42b",
}


@dataclass
class TrackMetadata:
    id: str
    title: str
    artists: List[str]
    albums: List[str] = field(default_factory=list)
    duration_ms: int = 0
    cover_url: str = ""

    def formatted_artist(self) -> str:
        return ", ".join(self.artists) if self.artists else "Unknown Artist"


@dataclass
class PlayerProgress:
    position_seconds: float
    duration_seconds: float
    speed: float = 1.0


@dataclass
class PlayerState:
    track: TrackMetadata
    progress: PlayerProgress
    is_playing: bool
    timestamp_ms: int


@dataclass
class LyricsLine:
    time_seconds: float
    text: str


@dataclass
class LyricsPayload:
    success: bool
    provider: str  # "yandex" | "musixmatch" | "lrclib"
    is_lrc: bool
    lyrics: str
    sync_lyrics: List[LyricsLine] = field(default_factory=list)

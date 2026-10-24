"""
Authoritative calculation engines and oracles for E2E tests.
Directly implements reference algorithms specified in:
- reference_sources/features_ui_external-apis_musixmatch_utils.ts
- PROJECT.md interface contracts
- ORIGINAL_REQUEST.md
"""

import hmac
import hashlib
import base64
import urllib.parse
import re
import struct
from datetime import datetime
from typing import Tuple, List, Dict, Optional, Any
from .contracts import (
    MUSIXMATCH_SECRET_KEY,
    LyricsLine,
    PlayerProgress,
)


def compute_musixmatch_signature(
    original_url: str,
    dt: Optional[datetime] = None,
    secret_key: str = MUSIXMATCH_SECRET_KEY,
) -> str:
    """
    Computes Musixmatch HMAC-SHA1 signature according to Android signature specification:
    urlWithDate = originalUrl + yMMdd (where y is single last digit of year)
    signed with HMAC-SHA1 and base64/url-encoded.
    Reference: reference_sources/features_ui_external-apis_musixmatch_utils.ts:8-30
    """
    if dt is None:
        dt = datetime.now()

    y = str(dt.year)[-1]  # single last digit of year, e.g. '6' for 2026
    m = f"{dt.month:02d}"
    d = f"{dt.day:02d}"
    y_m_m_d_d = y + m + d

    url_with_date = original_url + y_m_m_d_d

    # HMAC-SHA1
    mac = hmac.new(secret_key.encode("utf-8"), url_with_date.encode("utf-8"), hashlib.sha1)
    raw_signature = mac.digest()
    b64_signature = base64.b64encode(raw_signature).decode("ascii")
    encoded_signature = urllib.parse.quote(b64_signature, safe="")

    separator = "&" if "?" in original_url else "?"
    return f"{original_url}{separator}signature={encoded_signature}&signature_protocol=sha1"


def clean_lrc_metadata_tags(raw_lrc: str) -> str:
    """
    Strips standard and extended LRC metadata tags:
    [ar:...], [ti:...], [al:...], [by:...], [offset:...], [length:...], [re:...], [ve:...], [tool:...]
    Leaves lyric lines (e.g. [01:23.45] Hello world) intact.
    Reference: PROJECT.md Feature 19 & Survey Spec Miner 3
    """
    if not raw_lrc:
        return ""

    lines = raw_lrc.splitlines()
    cleaned = []
    # Header tag pattern: [tag_name: value] where tag_name starts with a letter
    metadata_pattern = re.compile(r"^\[([a-zA-Z][a-zA-Z0-9_-]*):\s*([^\]]*)\]")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if metadata_pattern.match(stripped):
            continue
        cleaned.append(stripped)

    return "\n".join(cleaned)


def parse_lrc_timestamps(lrc_text: str) -> List[LyricsLine]:
    """
    Parses synchronized LRC lines into sorted time/text tuples.
    Pattern: [mm:ss.xx] or [mm:ss:xx] or [mm:ss]
    """
    if not lrc_text:
        return []

    lines = lrc_text.splitlines()
    timestamp_pattern = re.compile(r"\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\](.*)")
    result = []

    for line in lines:
        m = timestamp_pattern.match(line.strip())
        if m:
            mins = int(m.group(1))
            secs = int(m.group(2))
            millis = 0
            if m.group(3):
                raw_m = m.group(3)
                if len(raw_m) == 2:
                    millis = int(raw_m) * 10
                elif len(raw_m) == 3:
                    millis = int(raw_m)
                elif len(raw_m) == 1:
                    millis = int(raw_m) * 100
            total_seconds = mins * 60 + secs + (millis / 1000.0)
            text = m.group(4).strip()
            result.append(LyricsLine(time_seconds=total_seconds, text=text))

    result.sort(key=lambda x: x.time_seconds)
    return result


def interpolate_playback_position(
    base_position: float,
    base_timestamp_ms: float,
    current_timestamp_ms: float,
    duration: float,
    speed: float = 1.0,
    is_playing: bool = True,
) -> float:
    """
    Calculates interpolated player position in seconds.
    pos(t) = basePosition + (now - baseTime) / 1000 * speed (clamped to [0, duration])
    Reference: PROJECT.md Feature 11 & Survey Explorer 2
    """
    if not is_playing or speed <= 0:
        return max(0.0, min(base_position, duration))

    elapsed_seconds = max(0.0, (current_timestamp_ms - base_timestamp_ms) / 1000.0)
    calculated = base_position + (elapsed_seconds * speed)
    return max(0.0, min(calculated, duration))


def encode_discord_ipc_packet(opcode: int, payload: str) -> bytes:
    """
    Encodes Discord IPC packet:
    [opcode: 32-bit LE int][length: 32-bit LE int][json string UTF-8]
    Reference: src/main/discord-rpc.js encode()
    """
    payload_bytes = payload.encode("utf-8")
    length = len(payload_bytes)
    return struct.pack("<II", opcode, length) + payload_bytes


def decode_discord_ipc_packet(data: bytes) -> Tuple[int, int, str, bytes]:
    """
    Decodes Discord IPC packet header and payload.
    Returns (opcode, length, payload_str, remaining_bytes)
    """
    if len(data) < 8:
        raise ValueError("Buffer too small for Discord IPC header")

    opcode, length = struct.unpack("<II", data[:8])
    if len(data) < 8 + length:
        raise ValueError(f"Incomplete packet: expected {8 + length} bytes, got {len(data)}")

    payload_str = data[8:8 + length].decode("utf-8")
    remaining = data[8 + length:]
    return opcode, length, payload_str, remaining


def validate_woff2_bytes(data: bytes) -> bool:
    """
    Validates WOFF2 binary signature (magic 0x774F4632 -> 'wOF2').
    """
    return len(data) >= 4 and data[:4] == b"wOF2"

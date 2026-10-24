import urllib.request
import json
import re
import hmac
import hashlib
import base64
from datetime import datetime

def sign_musixmatch_url(url_path):
    secret_key = b"967Pn4)N3&R_GBg5$b('"
    now = datetime.now()
    y = str(now.year)[3]
    m = f"{now.month:02d}"
    d = f"{now.day:02d}"
    ymmdd = f"{y}{m}{d}"
    url_with_date = (url_path + ymmdd).encode('utf-8')
    sig = base64.b64encode(hmac.new(secret_key, url_with_date, hashlib.sha1).digest()).decode('ascii')
    sep = '&' if '?' in url_path else '?'
    return f"{url_path}{sep}signature={urllib.parse.quote(sig)}&signature_protocol=sha1"

def test_musixmatch():
    base = "https://apic.musixmatch.com/ws/1.1/"
    params = urllib.parse.urlencode({
        "app_id": "android-player-v1.0",
        "usertoken": "250721b994519ea801e6582aeb61c797d5cecb501ed93b6c22e42d",
        "q_track": "In the End",
        "q_artist": "Linkin Park",
        "format": "json"
    })
    signed = sign_musixmatch_url(f"macro.subtitles.get?{params}")
    req = urllib.request.Request(base + signed, headers={
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_I005DA Build/PI)"
    })
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            body = data.get('message', {}).get('body', {})
            macro = body.get('macro_calls', {})
            track_sub = macro.get('track.subtitles.get', {}).get('message', {}).get('body', {}).get('subtitle', {})
            print("Musixmatch Subtitles Success:", bool(track_sub.get('subtitle_body')))
            if track_sub.get('subtitle_body'):
                print("Musixmatch snippet:", track_sub.get('subtitle_body')[:150])
    except Exception as e:
        print("Musixmatch test error:", e)

if __name__ == "__main__":
    test_musixmatch()

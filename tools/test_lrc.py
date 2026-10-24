import urllib.request
import urllib.parse
import json

def test_lrclib(title, artist):
    query = urllib.parse.urlencode({"track_name": title, "artist_name": artist})
    url = f"https://lrclib.net/api/get?{query}"
    print(f"Fetching: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "YandexMusicMod/5.124.1"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("Found via get:", "syncedLyrics" in data and bool(data["syncedLyrics"]))
            if data.get("syncedLyrics"):
                print("First 2 lines:\n", "\n".join(data["syncedLyrics"].splitlines()[:2]))
    except Exception as e:
        print("Get failed:", e)
        # Try search
        sq = urllib.parse.quote(f"{title} {artist}")
        surl = f"https://lrclib.net/api/search?q={sq}"
        print(f"Searching: {surl}")
        sreq = urllib.request.Request(surl, headers={"User-Agent": "YandexMusicMod/5.124.1"})
        try:
            with urllib.request.urlopen(sreq, timeout=5) as sresp:
                sdata = json.loads(sresp.read().decode("utf-8"))
                print(f"Search results count: {len(sdata)}")
                if sdata:
                    first = sdata[0]
                    print("Found synced:", bool(first.get("syncedLyrics")))
                    if first.get("syncedLyrics"):
                        print("First 2 lines:\n", "\n".join(first["syncedLyrics"].splitlines()[:2]))
        except Exception as se:
            print("Search failed:", se)

test_lrclib("Группа крови", "Кино")
test_lrclib("Shape of You", "Ed Sheeran")

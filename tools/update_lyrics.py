import os

file_path = os.path.join("src", "main", "mod-main.js")
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# Replace fetchLyrics
old_start = '  // Universal Lyrics Fetcher (LRCLib get + search fallback)'
old_end = '      return null;\n    } catch (err) {\n      return null;\n    }\n  });'

idx_start = text.find(old_start)
if idx_start == -1:
    old_start_crlf = old_start.replace('\n', '\r\n')
    idx_start = text.find(old_start_crlf)

print("idx_start:", idx_start)

new_code = '''  // Multi-Tier Cascading Lyrics Fetcher (Yandex Supplement -> LRCLib Direct -> LRCLib Search)
  ipcMain.handle("yandexMusicMod.fetchLyrics", async (_ev, trackTitle, trackArtist, trackId = null) => {
    if (!trackTitle && !trackId) return null;
    try {
      const cleanTitle = (trackTitle || "").trim();
      const cleanArtist = (trackArtist || "").trim();

      const fetchJson = (url, extraHeaders = {}) => {
        return new Promise((resolve) => {
          const req = https.get(
            url,
            {
              headers: {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                ...extraHeaders,
              },
              timeout: 4000,
            },
            (res) => {
              let data = "";
              res.on("data", (chunk) => (data += chunk));
              res.on("end", () => {
                try {
                  if (res.statusCode >= 200 && res.statusCode < 300) {
                    resolve(JSON.parse(data));
                  } else {
                    resolve(null);
                  }
                } catch (e) {
                  resolve(null);
                }
              });
            }
          );
          req.on("error", () => resolve(null));
          req.on("timeout", () => {
            req.destroy();
            resolve(null);
          });
        });
      };

      // 1. Tier 1: Official Yandex Music Track Supplement (Zero-latency native synced lyrics)
      if (trackId && String(trackId).match(/^\\d+$/)) {
        try {
          const yandexData = await fetchJson(`https://api.music.yandex.net/tracks/${trackId}/supplement`, {
            "X-Yandex-Music-Client": "YandexMusicDesktopAppWindows/5.124.1",
            "X-Yandex-Music-Frontend": "new",
          });

          if (yandexData && yandexData.result && yandexData.result.lyrics) {
            const lyricsObj = yandexData.result.lyrics;
            if (Array.isArray(lyricsObj.syncLyrics) && lyricsObj.syncLyrics.length > 0) {
              const lrcLines = lyricsObj.syncLyrics.map((item) => {
                const totalSec = (item.timestamp || item.offset || 0) / 1000;
                const m = Math.floor(totalSec / 60);
                const s = Math.floor(totalSec % 60);
                const cs = Math.floor((totalSec % 1) * 100);
                const timeTag = `[${m < 10 ? "0" : ""}${m}:${s < 10 ? "0" : ""}${s}.${cs < 10 ? "0" : ""}${cs}]`;
                return `${timeTag} ${item.line || item.text || ""}`;
              });
              return lrcLines.join("\\n");
            } else if (lyricsObj.fullLyrics) {
              return lyricsObj.fullLyrics;
            }
          }
        } catch (e) {}
      }

      // 2. Tier 2: LRCLib Direct Match with modern browser headers
      if (cleanTitle) {
        const query = new URLSearchParams({
          track_name: cleanTitle,
          artist_name: cleanArtist,
        }).toString();
        const direct = await fetchJson(`https://lrclib.net/api/get?${query}`);
        if (direct && (direct.syncedLyrics || direct.plainLyrics)) {
          return direct.syncedLyrics || direct.plainLyrics;
        }

        // 3. Tier 3: LRCLib Cleaned Search Fallback (strip feat., remix, remaster)
        const strippedTitle = cleanTitle
          .replace(/\\s*[\\(\\[][^\\)\\]]*(?:feat|ft|remix|edit|version|prod|remaster|soundtrack|live|official)[^\\)\\]]*[\\)\\]]/gi, "")
          .trim();
        const primaryArtist = cleanArtist.split(/[,&/]/)[0].trim();
        const searchQuery = encodeURIComponent(`${strippedTitle} ${primaryArtist}`.trim());
        const searchRes = await fetchJson(`https://lrclib.net/api/search?q=${searchQuery}`);
        if (Array.isArray(searchRes) && searchRes.length > 0) {
          const synced = searchRes.find((x) => x.syncedLyrics);
          if (synced && synced.syncedLyrics) return synced.syncedLyrics;
          const plain = searchRes.find((x) => x.plainLyrics);
          if (plain && plain.plainLyrics) return plain.plainLyrics;
        }
      }

      return null;
    } catch (err) {
      return null;
    }
  });'''

# Find end
idx_end = text.find('  // Directory pickers')
if idx_end == -1:
    idx_end = text.find('// Directory pickers')

if idx_start != -1 and idx_end != -1:
    updated = text[:idx_start] + new_code + "\n\n" + text[idx_end:]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(updated)
    print("Successfully updated mod-main.js with cascading lyrics engine!")
else:
    print("Could not find start or end index:", idx_start, idx_end)

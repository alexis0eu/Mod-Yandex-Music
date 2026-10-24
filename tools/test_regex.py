import re

with open('src/renderer/mod-renderer.js', 'r', encoding='utf-8') as f:
    code = f.read()

old_fetch_lyrics = r'async function fetchTrackLyrics\(title, artist, meta\) \{[\s\S]*?console\.error\("\[YandexMusicMod\] Error fetching track lyrics:", e\);\s*\}\s*\}'
m1 = re.search(old_fetch_lyrics, code)
print('Fetch lyrics match:', bool(m1))

old_modal_body = r'<!-- Tabs -->[\s\S]*?<!-- TAB 6: ABOUT -->'
m2 = re.search(old_modal_body, code)
print('Modal body match:', bool(m2))

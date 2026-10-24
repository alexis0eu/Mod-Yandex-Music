import urllib.request
import re
import os
import base64

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

fonts_to_download = [
    ("Russo One", "RussoOne"),
    ("Comfortaa", "Comfortaa"),
    ("Dela Gothic One", "DelaGothicOne"),
    ("Rubik Glitch Pop", "RubikGlitchPop"),
    ("Unbounded", "Unbounded"),
    ("Caveat", "Caveat"),
    ("Podkova", "Podkova")
]

os.makedirs('src/fonts', exist_ok=True)

for family, file_prefix in fonts_to_download:
    url = f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}&display=swap"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            css = resp.read().decode('utf-8')
        
        # Parse all font-face blocks
        blocks = css.split('@font-face')
        downloaded = 0
        for block in blocks:
            if not block.strip(): continue
            comment = ""
            # find comment like /* cyrillic */
            m_comm = re.search(r'/\*\s*([^*]+)\s*\*/', block)
            if m_comm:
                comment = m_comm.group(1).strip()
            
            m_url = re.search(r'url\((https://[^\)]+\.woff2)\)', block)
            m_range = re.search(r'unicode-range:\s*([^;]+);', block)
            
            if m_url and ('cyrillic' in comment.lower() or 'latin' in comment.lower() or not comment):
                w_url = m_url.group(1)
                sub_name = comment.replace(' ', '_') if comment else f"sub_{downloaded}"
                out_name = f"{file_prefix}_{sub_name}.woff2"
                out_path = os.path.join('src', 'fonts', out_name)
                
                req2 = urllib.request.Request(w_url, headers=headers)
                with urllib.request.urlopen(req2, timeout=10) as fresp:
                    data = fresp.read()
                with open(out_path, 'wb') as fp:
                    fp.write(data)
                downloaded += 1
                print(f"Downloaded {family} ({comment}): {len(data)} bytes -> {out_name}")
    except Exception as e:
        print(f"Error downloading {family}: {e}")

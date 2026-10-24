import os
import base64

def get_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

fonts_dir = os.path.join("src", "fonts")

# Read fonts
andy_woff = get_b64(os.path.join(fonts_dir, "Andy-Bold.woff"))
andy_woff2 = get_b64(os.path.join(fonts_dir, "Andy-Bold.woff2"))
mc_woff = get_b64(os.path.join(fonts_dir, "Minecraft.woff"))
mc_woff2 = get_b64(os.path.join(fonts_dir, "Minecraft.woff2"))
jb_woff2 = get_b64(os.path.join(fonts_dir, "JetBrainsMono-Regular.woff2"))

russo_cyr = get_b64(os.path.join(fonts_dir, "RussoOne_sub_2.woff2"))
russo_lat = get_b64(os.path.join(fonts_dir, "RussoOne_latin.woff2"))

comfortaa_cyr = get_b64(os.path.join(fonts_dir, "Comfortaa_cyrillic.woff2"))
comfortaa_lat = get_b64(os.path.join(fonts_dir, "Comfortaa_latin.woff2"))

unbounded_cyr = get_b64(os.path.join(fonts_dir, "Unbounded_cyrillic.woff2"))
unbounded_lat = get_b64(os.path.join(fonts_dir, "Unbounded_latin.woff2"))

caveat_cyr = get_b64(os.path.join(fonts_dir, "Caveat_cyrillic.woff2"))
caveat_lat = get_b64(os.path.join(fonts_dir, "Caveat_latin.woff2"))

podkova_cyr = get_b64(os.path.join(fonts_dir, "Podkova_cyrillic.woff2"))
podkova_lat = get_b64(os.path.join(fonts_dir, "Podkova_latin.woff2"))

cyrillic_range = "U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116"
latin_range = "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"

css_fonts = f"""/* === YANDEX MUSIC MOD - EMBEDDED BASE64 FONTS === */
@font-face {{
  font-family: "JetBrains Mono";
  src: url("data:font/woff2;base64,{jb_woff2}") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
}}

@font-face {{
  font-family: "Terraria";
  src: url("data:font/woff;base64,{andy_woff}") format("woff"),
       url("data:font/woff2;base64,{andy_woff2}") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
}}

@font-face {{
  font-family: "Andy Bold";
  src: url("data:font/woff;base64,{andy_woff}") format("woff"),
       url("data:font/woff2;base64,{andy_woff2}") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
}}

@font-face {{
  font-family: "Minecraft";
  src: url("data:font/woff;base64,{mc_woff}") format("woff"),
       url("data:font/woff2;base64,{mc_woff2}") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
}}

@font-face {{
  font-family: "Russo One";
  src: url("data:font/woff2;base64,{russo_cyr}") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
  unicode-range: {cyrillic_range};
}}
@font-face {{
  font-family: "Russo One";
  src: url("data:font/woff2;base64,{russo_lat}") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
  unicode-range: {latin_range};
}}

@font-face {{
  font-family: "Comfortaa";
  src: url("data:font/woff2;base64,{comfortaa_cyr}") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
  unicode-range: {cyrillic_range};
}}
@font-face {{
  font-family: "Comfortaa";
  src: url("data:font/woff2;base64,{comfortaa_lat}") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
  unicode-range: {latin_range};
}}

@font-face {{
  font-family: "Unbounded";
  src: url("data:font/woff2;base64,{unbounded_cyr}") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
  unicode-range: {cyrillic_range};
}}
@font-face {{
  font-family: "Unbounded";
  src: url("data:font/woff2;base64,{unbounded_lat}") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
  unicode-range: {latin_range};
}}

@font-face {{
  font-family: "Caveat";
  src: url("data:font/woff2;base64,{caveat_cyr}") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
  unicode-range: {cyrillic_range};
}}
@font-face {{
  font-family: "Caveat";
  src: url("data:font/woff2;base64,{caveat_lat}") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
  unicode-range: {latin_range};
}}

@font-face {{
  font-family: "Podkova";
  src: url("data:font/woff2;base64,{podkova_cyr}") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
  unicode-range: {cyrillic_range};
}}
@font-face {{
  font-family: "Podkova";
  src: url("data:font/woff2;base64,{podkova_lat}") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
  unicode-range: {latin_range};
}}

"""

# Now replace the font section in src/renderer/mod-renderer.css
css_file = os.path.join("src", "renderer", "mod-renderer.css")
with open(css_file, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

trigger_idx = content.find("/* === FLOATING MOD SETTINGS TRIGGER === */")
if trigger_idx == -1:
    raise ValueError("Could not find trigger comment in mod-renderer.css")

rest_of_css = content[trigger_idx:]
new_css = css_fonts + rest_of_css

with open(css_file, "w", encoding="utf-8") as f:
    f.write(new_css)

print(f"Updated mod-renderer.css! New total size: {len(new_css)} chars ({len(new_css) / 1024:.1f} KB)")

with open(r'd:\Яндекс Музыка мод\src\renderer\mod-renderer.js', 'r', encoding='utf-8') as f:
    c = f.read()

top_marker = 'console.log("[YandexMusicMod] Initializing mod renderer v5.124.1...");'
CONSTANTS = '''console.log("[YandexMusicMod] Initializing mod renderer v5.124.1...");

  const UI_CLEANER_STYLESHEET_ID = "ym-mod-ui-cleaner-style";
  const SCALE_STYLESHEET_ID = "ym-mod-scale-style";
  const THEME_STYLESHEET_ID = "ym-mod-custom-theme-style";
  const FONT_STYLESHEET_ID = "ym-mod-custom-font-style";'''

c = c.replace(top_marker, CONSTANTS)
with open(r'd:\Яндекс Музыка мод\src\renderer\mod-renderer.js', 'w', encoding='utf-8') as f:
    f.write(c)
print('Updated top constants')

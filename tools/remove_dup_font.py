with open(r'd:\Яндекс Музыка мод\src\renderer\mod-renderer.js', 'r', encoding='utf-8') as f:
    c = f.read()

# Replace the second declaration of FONT_STYLESHEET_ID
old_font = '''  const FONT_STYLESHEET_ID = "ym-mod-custom-font";

  function ensureBaseStylesheet() {'''

new_font = '''  function ensureBaseStylesheet() {'''

c = c.replace(old_font, new_font)

with open(r'd:\Яндекс Музыка мод\src\renderer\mod-renderer.js', 'w', encoding='utf-8') as f:
    f.write(c)

print('Successfully removed duplicate FONT_STYLESHEET_ID')

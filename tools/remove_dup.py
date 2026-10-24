with open(r'd:\Яндекс Музыка мод\src\renderer\mod-renderer.js', 'r', encoding='utf-8') as f:
    c = f.read()

# Replace the second declaration
old_block = '''  // ==========================================
  // 3.2 GRANULAR UI CLEANER
  // ==========================================
  const UI_CLEANER_STYLESHEET_ID = "ym-mod-ui-cleaner-style";

  function applyUiCleaner() {'''

new_block = '''  // ==========================================
  // 3.2 GRANULAR UI CLEANER
  // ==========================================
  function applyUiCleaner() {'''

c = c.replace(old_block, new_block)

with open(r'd:\Яндекс Музыка мод\src\renderer\mod-renderer.js', 'w', encoding='utf-8') as f:
    f.write(c)

print('Successfully removed duplicate UI_CLEANER_STYLESHEET_ID')

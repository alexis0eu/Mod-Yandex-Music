import os

target = r"src\renderer\mod-renderer.js"
with open(target, "r", encoding="utf-8") as f:
    c = f.read()

# 1. Add hideTrends to applyUiCleaner()
cleaner_marker = '    if (modSettings["cleaner/hideTrailers"]) {'
trends_rule = """    if (modSettings["cleaner/hideTrends"]) {
      css += `aside li:has([data-test-id="NAVBAR_NAVIGATION_ITEM_FOR_YOU_AND_TRENDS"]), aside a[href*="/landing"] { display: none !important; }\\n`;
    }
"""

if "cleaner/hideTrends" not in c and cleaner_marker in c:
    c = c.replace(cleaner_marker, trends_rule + cleaner_marker)
    print("Added hideTrends to applyUiCleaner")

# 2. Add hideTrends HTML row to Cleaner tab
html_marker = '                <div class="ym-row">\n                  <div class="ym-col-info">\n                    <span class="ym-label">Скрыть «Трейлеры»</span>'
trends_html = """                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть «Для вас и Тренды»</span>
                    <span class="ym-desc">Убирает вкладку трендов и новинок из бокового меню</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-clean-trends">
                    <span class="ym-slider"></span>
                  </label>
                </div>

"""
if "opt-clean-trends" not in c and html_marker in c:
    c = c.replace(html_marker, trends_html + html_marker)
    print("Added opt-clean-trends HTML row")

# 3. Add to cleanerKeys array
keys_marker = '["opt-clean-podcasts", "cleaner/hidePodcasts"],'
trends_key = '["opt-clean-podcasts", "cleaner/hidePodcasts"],\n      ["opt-clean-trends", "cleaner/hideTrends"],'
if '["opt-clean-trends", "cleaner/hideTrends"]' not in c and keys_marker in c:
    c = c.replace(keys_marker, trends_key)
    print("Added opt-clean-trends to cleanerKeys")

with open(target, "w", encoding="utf-8") as f:
    f.write(c)

print("Update complete for cleaner/hideTrends")

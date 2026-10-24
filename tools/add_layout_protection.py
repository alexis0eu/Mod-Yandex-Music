import os

css_file = r"src\renderer\mod-renderer.css"
with open(css_file, "r", encoding="utf-8") as f:
    c = f.read()

layout_protection = """
/* ========================================================
   ROOT LAYOUT PROTECTION: PREVENT ANY COLLAPSE OR HIDING
   ======================================================== */
.WithTopBanner_root__P__x3 {
  display: grid !important;
  grid-template: "banner" auto "content" 1fr !important;
  height: 100vh !important;
  min-height: 100vh !important;
  overflow: hidden !important;
  visibility: visible !important;
  opacity: 1 !important;
}

.WithTopBanner_content__6Vh7a {
  grid-area: content !important;
  height: 100% !important;
  min-height: 0 !important;
  overflow: hidden !important;
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
}

.DefaultLayout_root__7J0wo,
.DefaultLayout_rootNewVibe__MSDOn {
  visibility: visible !important;
  opacity: 1 !important;
}
"""

if ".WithTopBanner_root__P__x3" not in c:
    c = layout_protection + "\n" + c
    with open(css_file, "w", encoding="utf-8") as f:
        f.write(c)
    print("Added layout protection rules to mod-renderer.css")
else:
    print("Rules already in mod-renderer.css")

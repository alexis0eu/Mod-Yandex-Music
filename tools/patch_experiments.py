import os

RENDERER_JS = r"src\renderer\mod-renderer.js"

with open(RENDERER_JS, "r", encoding="utf-8") as f:
    text = f.read()

target = """    // 4. Experiments details for Classic vs Modern Design switch
    if (url.includes("/account/experiments/details")) {
      try {
        const res = await originalFetch.apply(this, args);
        const data = await res.json();
        const designMode = modSettings["design/mode"] || "classic";
        const customOverrides = modSettings["settings/accountExperimentsOverride"] || [];

        const modified = { ...data };

        // Apply Design Mode presets
        if (designMode === "classic") {
          const offValue = { group: "off", value: { title: "off", enabled: false } };
          modified["new_web_design"] = offValue;
          modified["redesign"] = offValue;
          modified["vibe_redesign"] = offValue;
          modified["multivibe"] = offValue;
          modified["words_in_wave"] = offValue;
        } else if (designMode === "modern") {
          const onValue = { group: "on", value: { title: "on", enabled: true } };
          modified["new_web_design"] = onValue;
          modified["redesign"] = onValue;
          modified["vibe_redesign"] = onValue;
          modified["multivibe"] = onValue;
          modified["words_in_wave"] = onValue;
        }

        // Apply any user custom overrides
        if (Array.isArray(customOverrides)) {
          for (const item of customOverrides) {
            if (item && item.id) {
              modified[item.id] = item.value;
            }
          }
        }

        return new Response(JSON.stringify(modified), {
          status: 200,
          headers: res.headers,
        });
      } catch (err) {
        console.error("[YandexMusicMod] Error in experiments interceptor:", err);
      }
    }"""

replacement = """    // 4. Experiments details (Pass-through with user overrides only, as in Stephanzion mod)
    if (url.includes("/account/experiments/details")) {
      try {
        const res = await originalFetch.apply(this, args);
        if (res.ok) {
          const data = await res.json();
          const customOverrides = modSettings["settings/accountExperimentsOverride"] || [];
          if (Array.isArray(customOverrides) && customOverrides.length > 0) {
            const modified = { ...data };
            for (const item of customOverrides) {
              if (item && item.id) {
                modified[item.id] = item.value;
              }
            }
            return new Response(JSON.stringify(modified), {
              status: res.status,
              headers: res.headers,
            });
          }
          return new Response(JSON.stringify(data), {
            status: res.status,
            headers: res.headers,
          });
        }
      } catch (err) {
        console.error("[YandexMusicMod] Error in experiments interceptor:", err);
      }
    }"""

norm_text = text.replace("\r\n", "\n")
norm_target = target.replace("\r\n", "\n")
norm_replacement = replacement.replace("\r\n", "\n")

if norm_target in norm_text:
    res = norm_text.replace(norm_target, norm_replacement, 1)
    with open(RENDERER_JS, "w", encoding="utf-8") as f:
        f.write(res)
    print("SUCCESSFULLY REPLACED EXPERIMENTS INTERCEPTOR")
else:
    print("ERROR: Target not found")

import sys
import os
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RENDERER_JS = r"d:\Яндекс Музыка мод\src\renderer\mod-renderer.js"

with open(RENDERER_JS, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update fetchTrackLyrics to pass auth header & handle directTrackId
old_fetch_lyrics = r'async function fetchTrackLyrics\(title, artist, meta\) \{[\s\S]*?console\.error\("\[YandexMusicMod\] Error fetching track lyrics:", e\);\n    \}\n  \}'

new_fetch_lyrics = '''async function fetchTrackLyrics(title, artist, meta, directTrackId = null) {
    try {
      let lrcFound = null;

      // 1. Try Yandex Music API supplement with authorization headers
      const trackId = directTrackId || (meta && meta.id ? meta.id : null);
      if (trackId) {
        try {
          let oauthToken = null;
          try {
            if (window.localStorage && window.localStorage.oauth) {
              const parsed = JSON.parse(window.localStorage.oauth);
              if (parsed && parsed.value) oauthToken = "OAuth " + parsed.value;
            }
          } catch (e) {}

          const headers = {
            "X-Yandex-Music-Client": "YandexMusicDesktopAppWindows/5.124.1",
            "X-Yandex-Music-Frontend": "new",
          };
          if (oauthToken) headers["Authorization"] = oauthToken;

          const resp = await originalFetch(`https://api.music.yandex.net/tracks/${trackId}/supplement`, { headers });
          if (resp.ok) {
            const data = await resp.json();
            const result = data.result || data;
            if (result && result.lyrics) {
              if (result.lyrics.syncLyrics && result.lyrics.syncLyrics.length > 0) {
                lrcFound = result.lyrics.syncLyrics.map((item) => ({
                  time: item.timestamp !== undefined ? item.timestamp / 1000 : (item.offset ? item.offset / 1000 : 0),
                  text: item.line || item.text || "",
                }));
              } else if (result.lyrics.fullLyrics) {
                lrcFound = result.lyrics.fullLyrics;
              }
            }
          }
        } catch (e) {}
      }

      // 2. Fallback to LRCLib via IPC bridge (with automatic search & title cleaning)
      if (!lrcFound && window.yandexMusicMod && window.yandexMusicMod.fetchLyrics && title) {
        try {
          lrcFound = await window.yandexMusicMod.fetchLyrics(title, artist);
        } catch (e) {}
      }

      // 3. Emit lyrics to Karaoke window and Overlay
      if (window.yandexMusicMod && window.yandexMusicMod.updateLyrics) {
        window.yandexMusicMod.updateLyrics({
          track: title,
          artist: artist,
          lrc: lrcFound || `[00:00.00] ${title} - ${artist}\\n[00:03.00] ♫ Текст песни не найден`,
        });
      }
    } catch (e) {
      console.error("[YandexMusicMod] Error fetching track lyrics:", e);
    }
  }'''

code = re.sub(old_fetch_lyrics, new_fetch_lyrics, code, count=1)
print("[+] Updated fetchTrackLyrics with OAuth headers and directTrackId")

# 2. Update Modal HTML Tabs and Panes
old_modal_body = r'<!-- Tabs -->[\s\S]*?<!-- TAB 6: ABOUT -->'

new_modal_body = '''<!-- Tabs -->
          <div class="ym-modal-tabs">
            <button class="ym-tab-btn active" data-tab="tab-plus">💎 Яндекс Плюс</button>
            <button class="ym-tab-btn" data-tab="tab-appearance">🎨 Дизайн и Тема</button>
            <button class="ym-tab-btn" data-tab="tab-fonts">🔤 Шрифты и Текст</button>
            <button class="ym-tab-btn" data-tab="tab-cleaner">🧹 Очистка UI</button>
            <button class="ym-tab-btn" data-tab="tab-equalizer">🎛️ Эквалайзер</button>
            <button class="ym-tab-btn" data-tab="tab-overlay">🎮 Игровой Оверлей</button>
            <button class="ym-tab-btn" data-tab="tab-karaoke">🎤 Караоке</button>
            <button class="ym-tab-btn" data-tab="tab-tweaks">⚡ Киллер-фичи</button>
            <button class="ym-tab-btn" data-tab="tab-about">ℹ️ О моде</button>
          </div>

          <!-- Content Panels -->
          <div class="ym-modal-content">
            <!-- TAB 0: PLUS UNLOCKER -->
            <div class="ym-tab-pane active" id="tab-plus">
              <div class="ym-card">
                <div class="ym-card-title">💎 Яндекс Плюс Анлокер</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Статус Яндекс Плюс</span>
                    <span class="ym-desc" style="color:#10b981;font-weight:600;">✅ Активен (hasPlus: true)</span>
                  </div>
                  <button class="ym-btn-action ym-btn-primary" id="btn-reload-plus">
                    🔄 Применить и перезагрузить
                  </button>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Снятие 30-секундного ограничения</span>
                    <span class="ym-desc">Воспроизведение полных аудиотреков без подписки и ограничений</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-plus-enabled" checked disabled>
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Бесконечные пропуски (скипы)</span>
                    <span class="ym-desc">Разблокировать неограниченный пропуск треков в рекомендациях</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-plus-skips" checked disabled>
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Блокировка аудиорекламы в Моей Волне</span>
                    <span class="ym-desc">Вырезает треки «Промокод Upgrade» и рекламные аудиовставки</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-plus-ads" checked disabled>
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрытие баннеров подписки</span>
                    <span class="ym-desc">Прячет плашки «Подключите Плюс», кнопки донатов и промо-акции</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-plus-prompts" checked disabled>
                    <span class="ym-slider"></span>
                  </label>
                </div>
              </div>
            </div>

            <!-- TAB 1: APPEARANCE -->
            <div class="ym-tab-pane" id="tab-appearance">
              <div class="ym-card">
                <div class="ym-card-title">🎨 Режим дизайна интерфейса</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Стиль интерфейса</span>
                    <span class="ym-desc">Классический проверенный дизайн или новый редизайн Моя Волна</span>
                  </div>
                  <div style="display:flex;gap:8px;align-items:center;">
                    <select class="ym-select" id="opt-design-mode">
                      <option value="classic">Классический (Старый дизайн)</option>
                      <option value="modern">Новый дизайн (Моя Волна Redesign)</option>
                    </select>
                    <button class="ym-btn-action" id="btn-reload-design" title="Применить изменения стиля">
                      🔄 Применить
                    </button>
                  </div>
                </div>
              </div>

              <div class="ym-card">
                <div class="ym-card-title">✨ Акцентная цветовая палитра</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Основной цвет оформления</span>
                    <span class="ym-desc">Меняет цвет кнопок, плеера, ползунков и подсветки</span>
                  </div>
                  <div class="ym-color-palette" id="ym-palette-container">
                    <div class="ym-color-swatch" style="background:#fed42b;color:#fed42b;" data-color="#fed42b" title="Yandex Gold"></div>
                    <div class="ym-color-swatch" style="background:#007acc;color:#007acc;" data-color="#007acc" title="Neon Blue"></div>
                    <div class="ym-color-swatch" style="background:#10b981;color:#10b981;" data-color="#10b981" title="Emerald Green"></div>
                    <div class="ym-color-swatch" style="background:#ef4444;color:#ef4444;" data-color="#ef4444" title="Crimson Red"></div>
                    <div class="ym-color-swatch" style="background:#8b5cf6;color:#8b5cf6;" data-color="#8b5cf6" title="Purple Dream"></div>
                    <div class="ym-color-swatch" style="background:#ec4899;color:#ec4899;" data-color="#ec4899" title="Vapor Pink"></div>
                    <input type="color" id="opt-custom-color" class="ym-custom-color-input" title="Свой цвет" />
                  </div>
                </div>
              </div>

              <div class="ym-card">
                <div class="ym-card-title">⚙️ Оптимизация фона</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Отключить анимацию Моя Волна</span>
                    <span class="ym-desc">Экономит ресурсы процессора и видеокарты во время игр</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-disable-vibe">
                    <span class="ym-slider"></span>
                  </label>
                </div>
              </div>
            </div>

            <!-- TAB 2: FONTS & TYPOGRAPHY -->
            <div class="ym-tab-pane" id="tab-fonts">
              <div class="ym-card">
                <div class="ym-card-title">🔤 Шрифты и Типографика</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Включить замену шрифта</span>
                    <span class="ym-desc">Применять выбранный шрифт ко всему приложению</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-font-enabled">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Семейство шрифтов</span>
                    <span class="ym-desc">Встроенные base64 шрифты применяются мгновенно</span>
                  </div>
                  <select class="ym-select" id="opt-font-family">
                    <option value="JetBrains Mono">JetBrains Mono (Стиль кода)</option>
                    <option value="Minecraft">Minecraft (Пиксельный ретро)</option>
                    <option value="Terraria">Terraria / Andy Bold (Мультяшный)</option>
                    <option value="Inter">Inter (Современный гротеск)</option>
                    <option value="Segoe UI">Segoe UI (Системный Windows)</option>
                    <option value="Roboto">Roboto</option>
                    <option value="Yandex Sans (Original)">Оригинальный (Yandex Sans)</option>
                  </select>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Размер текста (Масштаб шрифта)</span>
                    <span class="ym-desc" id="lbl-font-size">100%</span>
                  </div>
                  <input type="range" class="ym-range-slider" id="opt-font-size-slider" min="0.8" max="1.4" step="0.05" value="1.0" />
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Насыщенность шрифта (Font Weight)</span>
                    <span class="ym-desc">Регулировка толщины символов</span>
                  </div>
                  <select class="ym-select" id="opt-font-weight">
                    <option value="normal">Обычный (400)</option>
                    <option value="500">Средний (500)</option>
                    <option value="600">Полужирный (600)</option>
                    <option value="bold">Жирный (700)</option>
                  </select>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Межбуквенный интервал (Tracking)</span>
                    <span class="ym-desc">Расстояние между буквами</span>
                  </div>
                  <select class="ym-select" id="opt-letter-spacing">
                    <option value="normal">Стандартный (0px)</option>
                    <option value="-0.4px">Компактный (-0.4px)</option>
                    <option value="0.5px">Свободный (+0.5px)</option>
                    <option value="1px">Широкий (+1.0px)</option>
                  </select>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Пользовательский шрифт</span>
                    <span class="ym-desc">Имя любого шрифта, установленного в Windows (Arial, Comic Sans...)</span>
                  </div>
                  <input type="text" class="ym-input" id="opt-font-custom" placeholder="Например: Comic Sans MS" />
                </div>
              </div>
            </div>

            <!-- TAB 3: UI CLEANER -->
            <div class="ym-tab-pane" id="tab-cleaner">
              <div class="ym-card">
                <div class="ym-card-title">🧹 Очистка панели плеера</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть кнопку Дизлайка</span>
                    <span class="ym-desc">Убирает значок перечёркнутого сердца на плеере</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-clean-dislike">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть кнопку Очереди треков</span>
                    <span class="ym-desc">Убирает список воспроизведения</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-clean-queue">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть кнопку Текста песен на плеере</span>
                    <span class="ym-desc">Убирает иконку микрофона/текста в правом блоке</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-clean-lyrics">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть кнопку Предыдущего трека</span>
                    <span class="ym-desc">Убирает кнопку назад на панели управления</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-clean-prev">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть бейдж Качества звука (HQ / FLAC)</span>
                    <span class="ym-desc">Убирает значок битрейта</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-clean-quality">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть ползунок Громкости</span>
                    <span class="ym-desc">Для тех, кто управляет звуком клавишами клавиатуры</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-clean-volume">
                    <span class="ym-slider"></span>
                  </label>
                </div>
              </div>

              <div class="ym-card">
                <div class="ym-card-title">🧹 Очистка бокового меню и главной</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть блок «Моя Волна» на главной</span>
                    <span class="ym-desc">Оставляет только списки треков и плейлистов</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-clean-vibe">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть «Подкасты и книги»</span>
                    <span class="ym-desc">Убирает раздел из навигации</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-clean-podcasts">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть «Трейлеры»</span>
                    <span class="ym-desc">Убирает раздел из навигации</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-clean-trailers">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Скрыть «Радио»</span>
                    <span class="ym-desc">Убирает раздел из навигации</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-clean-radio">
                    <span class="ym-slider"></span>
                  </label>
                </div>
              </div>
            </div>

            <!-- TAB 4: EQUALIZER -->
            <div class="ym-tab-pane" id="tab-equalizer">
              <div class="ym-card">
                <div class="ym-card-title">🎛️ WebAudio 10-полосный Эквалайзер</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Включить программный эквалайзер</span>
                    <span class="ym-desc">Аппаратное обогащение звука и усиление частот</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-eq-enabled">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row" style="flex-direction:column;align-items:flex-start;gap:6px;">
                  <span class="ym-label">Пресеты звучания</span>
                  <div class="ym-eq-grid" id="eq-preset-grid">
                    <button class="ym-eq-preset-btn active" data-preset="flat">🎵 Обычный (Flat)</button>
                    <button class="ym-eq-preset-btn" data-preset="bassBoost">💥 Bass Boost</button>
                    <button class="ym-eq-preset-btn" data-preset="vocal">🎙️ Чистый вокал</button>
                    <button class="ym-eq-preset-btn" data-preset="club">🎧 Club / EDM</button>
                    <button class="ym-eq-preset-btn" data-preset="rock">🎸 Rock / Metal</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- TAB 5: OVERLAY -->
            <div class="ym-tab-pane" id="tab-overlay">
              <div class="ym-card">
                <div class="ym-card-title">🎮 Steam / Discord стиль Игровой Оверлей</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Включить оверлей</span>
                    <span class="ym-desc">Плавающий прозрачный HUD плеер поверх всех окон и игр</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-overlay-enabled">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Горячая клавиша вызова</span>
                    <span class="ym-desc">По умолчанию: <b>Ctrl+Shift+O</b> (Сквозной клик: <b>Ctrl+Shift+G</b>)</span>
                  </div>
                  <button class="ym-btn-action ym-btn-primary" id="btn-open-overlay">
                    🚀 Открыть оверлей сейчас
                  </button>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Сквозной клик (Ghost mode)</span>
                    <span class="ym-desc">Клики мыши проходят сквозь оверлей в игру, при наведении элементы активны</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-overlay-ghost">
                    <span class="ym-slider"></span>
                  </label>
                </div>
              </div>
            </div>

            <!-- TAB 6: KARAOKE -->
            <div class="ym-tab-pane" id="tab-karaoke">
              <div class="ym-card">
                <div class="ym-card-title">🎤 Плавающее Караоке (Текст песен на экране)</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Синхронный караоке-текст поверх окон</span>
                    <span class="ym-desc">Красивая плавающая капсула с подсветкой активной строки и авто-прокруткой</span>
                  </div>
                  <button class="ym-btn-action ym-btn-primary" id="btn-open-karaoke">
                    🎤 Открыть караоке сейчас (Ctrl+Shift+L)
                  </button>
                </div>
              </div>
            </div>

            <!-- TAB 7: TWEAKS & KILLER FEATURES -->
            <div class="ym-tab-pane" id="tab-tweaks">
              <div class="ym-card">
                <div class="ym-card-title">⚡ Авторские Киллер-фичи</div>
                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">1-Click Скачивание треков</span>
                    <span class="ym-desc">Скачать текущую песню в наилучшем качестве прямо сейчас</span>
                  </div>
                  <button class="ym-btn-action ym-btn-primary" id="btn-download-now">
                    ⬇️ Скачать трек
                  </button>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">❤️ Умный авто-лайкер (Smart Auto-Liker)</span>
                    <span class="ym-desc">Ставит лайк треку, если вы дослушали его более чем на 80%</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-autoliker-enabled">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">🔔 OSD экранные тосты при смене трека</span>
                    <span class="ym-desc">Всплывающая плашка с обложкой и названием поверх любых игр</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-osd-enabled">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Discord RPC в стиле Spotify</span>
                    <span class="ym-desc">Статус «Слушает Яндекс Музыку» с живым таймлайном и обложкой</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-discord-rpc">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Авто-выбор максимального качества (Lossless / HQ)</span>
                    <span class="ym-desc">Автоматически выставляет максимальный битрейт 320 kbps / FLAC</span>
                  </div>
                  <label class="ym-switch">
                    <input type="checkbox" id="opt-auto-quality">
                    <span class="ym-slider"></span>
                  </label>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Масштаб интерфейса (UI Zoom)</span>
                    <span class="ym-desc">Настройка размера элементов под мониторы высокого разрешения</span>
                  </div>
                  <select class="ym-select" id="opt-ui-scale">
                    <option value="0.85">85% (Компактный)</option>
                    <option value="0.9">90%</option>
                    <option value="1.0">100% (По умолчанию)</option>
                    <option value="1.1">110%</option>
                    <option value="1.2">120% (Крупный)</option>
                  </select>
                </div>

                <div class="ym-row">
                  <div class="ym-col-info">
                    <span class="ym-label">Режим разработчика (DevTools F12)</span>
                    <span class="ym-desc">Включает хоткеи F12 и Ctrl+Shift+I для исследования интерфейса</span>
                  </div>
                  <button class="ym-btn-action" id="btn-open-devtools">
                    🛠️ Открыть DevTools
                  </button>
                </div>
              </div>
            </div>

            <!-- TAB 8: ABOUT -->'''

code = re.sub(old_modal_body, new_modal_body, code, count=1)
print("[+] Replaced Modal body with all 9 comprehensive tabs")

with open(RENDERER_JS, "w", encoding="utf-8") as f:
    f.write(code)

print("[+] Successfully saved updated mod-renderer.js")

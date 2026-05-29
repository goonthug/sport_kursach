/**
 * geo.js — определение местоположения пользователя для СпортРент.
 *
 * Пайплайн:
 *   1. Проверяем кэш localStorage (1 час) — если свежий, берём оттуда
 *   2. IP-геолокация (ip-api.com, быстро, до города)
 *   3. Fallback: Browser Geolocation API (показываем баннер-разрешение)
 *   4. Сохраняем в Django-сессию через POST /geo/save/
 *   5. Обновляем навбар динамически
 *
 * Экспортирует:
 *   window.GEO.init()   — запуск (вызывается автоматически)
 *   window.GEO.refresh() — принудительный сброс и переопределение
 */
(function () {
    'use strict';

    const LS_TS   = 'sportrent_geo_ts';
    const LS_CITY = 'sportrent_geo_city';
    const LS_ADDR = 'sportrent_geo_addr';
    const ONE_HOUR_MS = 3600 * 1000;

    /* ── Утилиты ─────────────────────────────────────────────────── */

    function isCacheValid() {
        const ts = parseInt(localStorage.getItem(LS_TS) || '0', 10);
        return (Date.now() - ts) < ONE_HOUR_MS;
    }

    function getCsrf() {
        const m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? m[1] : '';
    }

    /* ── Навбар ──────────────────────────────────────────────────── */

    function updateNavbar(city, address) {
        const item = document.getElementById('geo-nav-item');
        const label = document.getElementById('geo-nav-label');
        if (!label || !item) return;

        if (city) {
            label.textContent = address ? `${city}, ${address}` : city;
            item.classList.remove('d-none');
        }
    }

    /* ── Сохранение в Django-сессию ──────────────────────────────── */

    async function saveToSession(lat, lon, city, source, address) {
        try {
            const resp = await fetch('/geo/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrf(),
                },
                body: JSON.stringify({ lat, lon, city, source, address: address || '' }),
            });
            if (!resp.ok) return;
            const data = await resp.json();
            if (!data.ok) return;

            const finalCity = data.city || city || '';
            const finalAddr = data.address || address || '';

            localStorage.setItem(LS_TS,   Date.now().toString());
            localStorage.setItem(LS_CITY, finalCity);
            localStorage.setItem(LS_ADDR, finalAddr);

            updateNavbar(finalCity, finalAddr);

            /* Сообщаем каталогу о найденном городе */
            document.dispatchEvent(new CustomEvent('geo:detected', {
                detail: { city: finalCity, address: finalAddr, source },
            }));
        } catch (_) { /* сеть упала — не страшно */ }
    }

    /* ── IP-геолокация ───────────────────────────────────────────── */

    async function detectByIP() {
        try {
            const r = await fetch('/api/geo/detect-city/', {
                headers: { 'Accept': 'application/json' },
                signal: AbortSignal.timeout(5000),
            });
            const d = await r.json();
            if (d.city) {
                await saveToSession(d.lat || 0, d.lon || 0, d.city, 'ip', '');
                return true;
            }
        } catch (_) {}
        return false;
    }

    /* ── Browser Geolocation с баннером ──────────────────────────── */

    async function detectByBrowser() {
        if (!navigator.geolocation) return false;

        const banner = document.getElementById('geo-permission-banner');
        if (banner) banner.classList.remove('d-none');

        return new Promise((resolve) => {
            function hideBanner() {
                if (banner) banner.classList.add('d-none');
            }

            const denyBtn  = document.getElementById('geo-deny-btn');
            const allowBtn = document.getElementById('geo-allow-btn');

            function onDeny() {
                hideBanner();
                resolve(false);
            }

            function onAllow() {
                hideBanner();
                navigator.geolocation.getCurrentPosition(
                    async (pos) => {
                        const { latitude: lat, longitude: lng } = pos.coords;
                        await saveToSession(lat, lng, '', 'browser', '');
                        resolve(true);
                    },
                    () => resolve(false),
                    { timeout: 8000 }
                );
            }

            if (denyBtn)  denyBtn.addEventListener('click',  onDeny,  { once: true });
            if (allowBtn) allowBtn.addEventListener('click', onAllow, { once: true });

            /* Если баннера нет в разметке — запрашиваем напрямую */
            if (!banner) onAllow();
        });
    }

    /* ── Главная функция ─────────────────────────────────────────── */

    async function init() {
        if (isCacheValid()) {
            const city = localStorage.getItem(LS_CITY) || '';
            const addr = localStorage.getItem(LS_ADDR) || '';
            if (city) {
                updateNavbar(city, addr);
                document.dispatchEvent(new CustomEvent('geo:detected', {
                    detail: { city, address: addr, source: 'cache' },
                }));
            }
            return;
        }

        const detected = await detectByIP();
        if (!detected) await detectByBrowser();
    }

    /* ── Сброс и повторное определение ──────────────────────────── */

    async function refresh() {
        localStorage.removeItem(LS_TS);
        localStorage.removeItem(LS_CITY);
        localStorage.removeItem(LS_ADDR);
        try {
            await fetch('/geo/clear/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrf() },
            });
        } catch (_) {}
        await init();
    }

    /* ── Публичный API ───────────────────────────────────────────── */

    window.GEO = { init, refresh };

    /* Запуск после загрузки DOM */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

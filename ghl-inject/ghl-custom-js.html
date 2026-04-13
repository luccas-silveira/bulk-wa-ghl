// ghl-inject/inject.js
// Colar em: GHL > Settings > Custom Code (como HTML com <script>)
// Ou hospedar e carregar via loader de uma linha
(function () {
  'use strict';

  const WPP_MANAGER_URL = 'https://appzoi.com/disparador';
  const BUTTON_ID = 'wpp-manager-fab';
  const OVERLAY_ID = 'wpp-manager-overlay';

  // ---------- Overlay com iframe ----------
  function openManager() {
    if (document.getElementById(OVERLAY_ID)) return;

    Promise.all([
      AppUtils.Utilities.getCurrentLocation(),
      AppUtils.Utilities.getCurrentUser(),
    ]).then(([location, user]) => {
      const locationId = location?.id || '';
      const userId = user?.id || '';

      const overlay = document.createElement('div');
      overlay.id = OVERLAY_ID;
      overlay.style.cssText = 'position:fixed;inset:0;z-index:999999;background:#fff;display:flex;flex-direction:column';

      const iframe = document.createElement('iframe');
      iframe.src = `${WPP_MANAGER_URL}/embedded?embedded=true&ghl_location_id=${encodeURIComponent(locationId)}&ghl_user_id=${encodeURIComponent(userId)}`;
      iframe.style.cssText = 'flex:1;border:none;width:100%;height:100%';
      iframe.allow = 'clipboard-write';

      overlay.appendChild(iframe);
      document.body.appendChild(overlay);
    }).catch(err => console.error('[WPP Manager]', err));
  }

  function closeManager() {
    const el = document.getElementById(OVERLAY_ID);
    if (el) el.remove();
  }

  window.addEventListener('message', function (e) {
    if (e.origin !== WPP_MANAGER_URL) return;
    if (e.data === 'wpp:close') closeManager();
  });

  // ---------- Botão no nav, ao lado de "Empresas" ----------
  function injectButton() {
    if (document.getElementById(BUTTON_ID)) return;

    const empresas = Array.from(document.querySelectorAll('a, button'))
      .find(el => el.textContent.trim() === 'Empresas');

    if (!empresas) {
      setTimeout(injectButton, 400);
      return;
    }

    const btn = document.createElement('a');
    btn.id = BUTTON_ID;
    btn.textContent = '📤 Disparos';
    btn.className = empresas.className;
    btn.style.cursor = 'pointer';
    btn.addEventListener('click', openManager);

    empresas.parentElement.insertBefore(btn, empresas.nextSibling);
  }

  function removeButton() {
    const el = document.getElementById(BUTTON_ID);
    if (el) el.remove();
  }

  // ---------- Detecção de rota ----------
  function isContactsRoute(path) {
    return /\/contacts(\/|$)/i.test(path);
  }

  function handleRoute() {
    const route = AppUtils.RouteHelper.getCurrentRoute();
    const path = route?.path || route?.fullPath || '';
    if (isContactsRoute(path)) {
      injectButton();
    } else {
      removeButton();
      closeManager();
    }
  }

  function init() {
    if (typeof AppUtils === 'undefined') {
      setTimeout(init, 300);
      return;
    }
    window.addEventListener('routeLoaded', handleRoute);
    window.addEventListener('routeChangeEvent', handleRoute);
    handleRoute();
  }

  init();
})();

// ghl-inject/inject.js
// Colar em: GHL > Settings > Integrations > Custom JS
// Substitua WPP_MANAGER_URL pela URL real do seu deploy
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
      overlay.style.cssText = [
        'position:fixed', 'inset:0', 'z-index:999999',
        'background:#fff', 'display:flex', 'flex-direction:column',
      ].join(';');

      const iframe = document.createElement('iframe');
      iframe.src = `${WPP_MANAGER_URL}/embedded?embedded=true&ghl_location_id=${encodeURIComponent(locationId)}&ghl_user_id=${encodeURIComponent(userId)}`;
      iframe.style.cssText = 'flex:1;border:none;width:100%;height:100%';
      iframe.allow = 'clipboard-write';

      overlay.appendChild(iframe);
      document.body.appendChild(overlay);
    }).catch(function (err) {
      console.error('[WPP Manager] Failed to get GHL context:', err);
    });
  }

  function closeManager() {
    const overlay = document.getElementById(OVERLAY_ID);
    if (overlay) overlay.remove();
  }

  // Fechar quando o app enviar postMessage 'wpp:close'
  // Nota: para testes locais, defina WPP_MANAGER_URL como 'http://localhost:3001' (ou URL do ngrok)
  window.addEventListener('message', function (e) {
    if (e.origin !== WPP_MANAGER_URL) return;
    if (e.data === 'wpp:close') closeManager();
  });

  // ---------- Botão FAB ----------
  function injectButton() {
    if (document.getElementById(BUTTON_ID)) return;

    const btn = document.createElement('button');
    btn.id = BUTTON_ID;
    btn.textContent = '📤 Disparos';
    btn.title = 'Abrir WPP Manager';
    btn.style.cssText = [
      'position:fixed', 'bottom:24px', 'right:24px', 'z-index:99999',
      'background:#1a56db', 'color:#fff', 'border:none', 'border-radius:8px',
      'padding:10px 18px', 'font-size:14px', 'font-weight:600',
      'cursor:pointer', 'box-shadow:0 4px 12px rgba(0,0,0,0.25)',
      'transition:background 0.2s',
    ].join(';');
    btn.addEventListener('mouseenter', () => { btn.style.background = '#1e40af'; });
    btn.addEventListener('mouseleave', () => { btn.style.background = '#1a56db'; });
    btn.addEventListener('click', openManager);

    document.body.appendChild(btn);
  }

  function removeButton() {
    const btn = document.getElementById(BUTTON_ID);
    if (btn) btn.remove();
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

  // Aguarda AppUtils estar disponível
  function init() {
    if (typeof AppUtils === 'undefined') {
      setTimeout(init, 300);
      return;
    }
    window.addEventListener('routeLoaded', handleRoute);
    window.addEventListener('routeChangeEvent', handleRoute);
    handleRoute(); // checar rota atual na carga inicial
  }

  init();
})();

# GHL Embed Inject — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Injetar um botão flutuante na tela de Contatos do GHL que abre o WPP Manager em fullscreen (iframe overlay), contextualizado pela location e usuário do GHL — sem sair da plataforma.

**Architecture:** Um snippet de Custom JS colado no GHL detecta a rota `/contacts` via `routeChangeEvent`, injeta um botão FAB, e ao clique cria um overlay `position:fixed` com um `<iframe>` apontando para `/embedded?ghl_location_id=xxx&ghl_user_id=yyy`. O React lê esses params via hook `useEmbeddedMode`, renderiza a tela de campanhas sem header, e ao fechar envia `postMessage('close')` ao parent GHL.

**Tech Stack:** React 18.2 + TypeScript 5.2 (frontend embedded mode), Vanilla JS (GHL snippet), `AppUtils.Utilities.getCurrentLocation()` + `getCurrentUser()` (GHL APIs), Jest + Testing Library (testes frontend)

---

## File Map

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `frontend/src/hooks/useEmbeddedMode.ts` | Criar | Lê `ghl_location_id`, `ghl_user_id`, `embedded` da URL |
| `frontend/src/hooks/__tests__/useEmbeddedMode.test.ts` | Criar | Testes do hook |
| `frontend/src/components/layout/EmbeddedLayout.tsx` | Criar | Layout sem header, com botão de fechar (postMessage) |
| `frontend/src/components/layout/__tests__/EmbeddedLayout.test.tsx` | Criar | Testes do layout |
| `frontend/src/main.tsx` | Modificar | Adicionar rota `/embedded` |
| `ghl-inject/inject.js` | Criar | Snippet Custom JS para colar no GHL |

---

## Task 1: Hook `useEmbeddedMode`

**Files:**
- Create: `frontend/src/hooks/useEmbeddedMode.ts`
- Create: `frontend/src/hooks/__tests__/useEmbeddedMode.test.ts`

- [ ] **Step 1: Escrever o teste que falha**

```typescript
// frontend/src/hooks/__tests__/useEmbeddedMode.test.ts
import { renderHook } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { useEmbeddedMode } from '../useEmbeddedMode';

const wrap = (search: string) => ({
  wrapper: ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter initialEntries={[`/embedded${search}`]}>{children}</MemoryRouter>
  ),
});

describe('useEmbeddedMode', () => {
  it('returns embedded=false when param is missing', () => {
    const { result } = renderHook(() => useEmbeddedMode(), wrap(''));
    expect(result.current.isEmbedded).toBe(false);
    expect(result.current.ghlLocationId).toBeNull();
    expect(result.current.ghlUserId).toBeNull();
  });

  it('returns embedded=true with location and user when params present', () => {
    const { result } = renderHook(
      () => useEmbeddedMode(),
      wrap('?embedded=true&ghl_location_id=loc123&ghl_user_id=usr456')
    );
    expect(result.current.isEmbedded).toBe(true);
    expect(result.current.ghlLocationId).toBe('loc123');
    expect(result.current.ghlUserId).toBe('usr456');
  });

  it('returns isEmbedded=false if embedded param is not "true"', () => {
    const { result } = renderHook(
      () => useEmbeddedMode(),
      wrap('?embedded=1&ghl_location_id=loc123')
    );
    expect(result.current.isEmbedded).toBe(false);
  });
});
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

```bash
cd frontend && npm test -- --testPathPattern=useEmbeddedMode --watchAll=false
```
Esperado: FAIL — `Cannot find module '../useEmbeddedMode'`

- [ ] **Step 3: Implementar o hook**

```typescript
// frontend/src/hooks/useEmbeddedMode.ts
import { useSearchParams } from 'react-router-dom';

export interface EmbeddedMode {
  isEmbedded: boolean;
  ghlLocationId: string | null;
  ghlUserId: string | null;
}

export function useEmbeddedMode(): EmbeddedMode {
  const [params] = useSearchParams();
  const isEmbedded = params.get('embedded') === 'true';
  return {
    isEmbedded,
    ghlLocationId: isEmbedded ? params.get('ghl_location_id') : null,
    ghlUserId: isEmbedded ? params.get('ghl_user_id') : null,
  };
}
```

- [ ] **Step 4: Rodar o teste para confirmar que passa**

```bash
cd frontend && npm test -- --testPathPattern=useEmbeddedMode --watchAll=false
```
Esperado: PASS (3 testes)

- [ ] **Step 5: Commit**

```bash
cd frontend && git add src/hooks/useEmbeddedMode.ts src/hooks/__tests__/useEmbeddedMode.test.ts
git commit -m "feat: add useEmbeddedMode hook for GHL iframe context"
```

---

## Task 2: Componente `EmbeddedLayout`

**Files:**
- Create: `frontend/src/components/layout/EmbeddedLayout.tsx`
- Create: `frontend/src/components/layout/__tests__/EmbeddedLayout.test.tsx`

- [ ] **Step 1: Escrever o teste que falha**

```typescript
// frontend/src/components/layout/__tests__/EmbeddedLayout.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import EmbeddedLayout from '../EmbeddedLayout';

describe('EmbeddedLayout', () => {
  it('renders children', () => {
    render(<EmbeddedLayout><p>conteúdo</p></EmbeddedLayout>);
    expect(screen.getByText('conteúdo')).toBeInTheDocument();
  });

  it('renders close button', () => {
    render(<EmbeddedLayout><p>x</p></EmbeddedLayout>);
    expect(screen.getByRole('button', { name: /fechar/i })).toBeInTheDocument();
  });

  it('sends postMessage close when button is clicked', () => {
    const postMessageSpy = jest.spyOn(window.parent, 'postMessage');
    render(<EmbeddedLayout><p>x</p></EmbeddedLayout>);
    fireEvent.click(screen.getByRole('button', { name: /fechar/i }));
    expect(postMessageSpy).toHaveBeenCalledWith('wpp:close', '*');
    postMessageSpy.mockRestore();
  });
});
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

```bash
cd frontend && npm test -- --testPathPattern=EmbeddedLayout --watchAll=false
```
Esperado: FAIL — `Cannot find module '../EmbeddedLayout'`

- [ ] **Step 3: Implementar o componente**

```typescript
// frontend/src/components/layout/EmbeddedLayout.tsx
import React from 'react';
import { X } from 'lucide-react';

interface EmbeddedLayoutProps {
  children: React.ReactNode;
}

const EmbeddedLayout: React.FC<EmbeddedLayoutProps> = ({ children }) => {
  const handleClose = () => {
    window.parent.postMessage('wpp:close', '*');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <div className="bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between">
        <span className="text-sm font-semibold uppercase tracking-wide text-primary-600">
          WPP Manager
        </span>
        <button
          onClick={handleClose}
          aria-label="Fechar"
          className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors"
        >
          <X size={18} />
        </button>
      </div>
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>
    </div>
  );
};

export default EmbeddedLayout;
```

- [ ] **Step 4: Rodar o teste para confirmar que passa**

```bash
cd frontend && npm test -- --testPathPattern=EmbeddedLayout --watchAll=false
```
Esperado: PASS (3 testes)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/EmbeddedLayout.tsx \
        frontend/src/components/layout/__tests__/EmbeddedLayout.test.tsx
git commit -m "feat: add EmbeddedLayout with GHL postMessage close"
```

---

## Task 3: Rota `/embedded` no `main.tsx`

**Files:**
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Adicionar import e rota `/embedded`**

Abrir `frontend/src/main.tsx`. Adicionar o import de `EmbeddedLayout` e `useEmbeddedMode` e inserir a nova rota logo antes de `<Route path="*" element={<NotFound />} />`:

```typescript
// Adicionar aos imports existentes
import EmbeddedLayout from './components/layout/EmbeddedLayout'
import { useEmbeddedMode } from './hooks/useEmbeddedMode'
```

Dentro do componente `AppRoutes`, adicionar antes do `<Route path="*"`:

```typescript
<Route
  path="/embedded"
  element={
    <EmbeddedRoute
      onCreateCampaign={() => navigate('/embedded/new')}
    />
  }
/>
<Route
  path="/embedded/new"
  element={
    <EmbeddedNewRoute onCancel={() => navigate('/embedded')} />
  }
/>
```

Adicionar os dois componentes auxiliares **antes** da função `AppRoutes`:

```typescript
// Componente auxiliar para a rota /embedded
const EmbeddedRoute: React.FC<{ onCreateCampaign: () => void }> = ({ onCreateCampaign }) => {
  const { ghlLocationId } = useEmbeddedMode();
  return (
    <EmbeddedLayout>
      <CampaignsPage
        onCreateCampaign={onCreateCampaign}
        defaultLocationId={ghlLocationId ?? undefined}
      />
    </EmbeddedLayout>
  );
};

const EmbeddedNewRoute: React.FC<{ onCancel: () => void }> = ({ onCancel }) => {
  const { ghlLocationId } = useEmbeddedMode();
  return (
    <EmbeddedLayout>
      <CampaignWizard
        onSubmit={async (data) => {
          const response = await fetch(`${API_BASE_URL}/api/v1/campaigns`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
          });
          if (!response.ok) {
            const body = await response.json().catch(() => ({}));
            throw new Error(body?.detail?.message || 'Falha ao criar campanha');
          }
          onCancel(); // volta para /embedded
        }}
        onCancel={onCancel}
        defaultLocationId={ghlLocationId ?? undefined}
      />
    </EmbeddedLayout>
  );
};
```

- [ ] **Step 2: Adicionar `defaultLocationId` prop em `CampaignsPage`**

Abrir `frontend/src/pages/CampaignsPage.tsx`. Adicionar prop e passá-la como `defaultFilters`:

```typescript
// Atualizar interface
export interface CampaignsPageProps {
  onCreateCampaign?: () => void;
  defaultLocationId?: string;        // ← adicionar
}

// Atualizar assinatura
const CampaignsPage: React.FC<CampaignsPageProps> = ({ onCreateCampaign, defaultLocationId }) => {

// Passar para CampaignList (localizar onde CampaignList é renderizado e adicionar defaultFilters)
<CampaignList
  defaultFilters={defaultLocationId ? { ghl_location_id: defaultLocationId } : undefined}
  onCreateCampaign={onCreateCampaign}
  ...
/>
```

- [ ] **Step 3: Verificar TypeScript sem erros**

```bash
cd frontend && npx tsc --noEmit
```
Esperado: sem erros

- [ ] **Step 4: Rodar todos os testes**

```bash
cd frontend && npm test -- --watchAll=false
```
Esperado: todos passando (nenhum teste existente quebrado)

- [ ] **Step 5: Testar manualmente no browser**

Abrir `http://localhost:3001/embedded?embedded=true&ghl_location_id=test_loc&ghl_user_id=test_user`

Verificar:
- ✅ Sem header de navegação principal
- ✅ Barra superior com "WPP Manager" e botão X
- ✅ Lista de campanhas visível
- ✅ Console sem erros

- [ ] **Step 6: Commit**

```bash
git add frontend/src/main.tsx frontend/src/pages/CampaignsPage.tsx
git commit -m "feat: add /embedded route for GHL iframe integration"
```

---

## Task 4: Custom JS Snippet para o GHL

**Files:**
- Create: `ghl-inject/inject.js`

> ⚠️ Este arquivo não é servido pelo app — é um snippet para colar manualmente em **GHL → Settings → Integrations → Custom JS** da location. Não tem testes automatizados; a validação é manual.

- [ ] **Step 1: Criar o diretório e o arquivo**

```bash
mkdir -p ghl-inject
```

- [ ] **Step 2: Escrever o snippet**

```javascript
// ghl-inject/inject.js
// Colar em: GHL > Settings > Integrations > Custom JS
// Substitua WPP_MANAGER_URL pela URL real do seu deploy
(function () {
  'use strict';

  const WPP_MANAGER_URL = 'https://SEU-DOMINIO.com'; // ← alterar antes de usar
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
    });
  }

  function closeManager() {
    const overlay = document.getElementById(OVERLAY_ID);
    if (overlay) overlay.remove();
  }

  // Fechar quando o app enviar postMessage 'wpp:close'
  window.addEventListener('message', function (e) {
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
    return /\/contacts/i.test(path);
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
```

- [ ] **Step 3: Commit**

```bash
git add ghl-inject/inject.js
git commit -m "feat: add GHL custom JS snippet for WPP Manager FAB inject"
```

---

## Task 5: Teste de Integração Manual

> Validação end-to-end antes de declarar o feature completo.

- [ ] **Step 1: Garantir que o WPP Manager está deployado em HTTPS**

O GHL só carrega iframes de origens HTTPS. Para testar localmente, usar um túnel:

```bash
# Instalar ngrok se não tiver
brew install ngrok

# Expor o frontend local
ngrok http 3001
```
Anotar a URL HTTPS gerada (ex: `https://abc123.ngrok.io`).

- [ ] **Step 2: Atualizar `WPP_MANAGER_URL` no snippet**

Em `ghl-inject/inject.js`, substituir:
```javascript
const WPP_MANAGER_URL = 'https://SEU-DOMINIO.com';
```
por:
```javascript
const WPP_MANAGER_URL = 'https://abc123.ngrok.io'; // sua URL ngrok
```

- [ ] **Step 3: Colar o snippet no GHL**

1. GHL → Settings (da location) → Integrations → Custom JS
2. Colar o conteúdo de `ghl-inject/inject.js`
3. Salvar

- [ ] **Step 4: Verificar o botão aparece**

1. Navegar para a aba **Contacts** no GHL
2. Verificar que o botão **"📤 Disparos"** aparece no canto inferior direito
3. Navegar para outra aba (Conversations, etc.) e verificar que o botão desaparece

- [ ] **Step 5: Verificar a abertura do app**

1. Clicar em **"📤 Disparos"** na aba Contacts
2. Verificar que o overlay fullscreen abre com o WPP Manager
3. Verificar no console do browser que `ghl_location_id` e `ghl_user_id` vieram preenchidos (inspecionar URL do iframe via DevTools → Elements)
4. Verificar que a lista de campanhas carrega sem erros

- [ ] **Step 6: Verificar o fechamento**

1. Clicar no botão **X** dentro do WPP Manager
2. Verificar que o overlay fecha e a tela do GHL volta normalmente
3. Verificar que o botão FAB ainda está visível na tela de Contacts

---

## Self-Review

**Cobertura da spec:**
- ✅ Botão FAB injetado na aba Contacts
- ✅ Detecção de rota via `routeChangeEvent` + `routeLoaded`
- ✅ Abertura fullscreen com iframe
- ✅ Contexto de location e user passados via query params
- ✅ Fechamento via postMessage `wpp:close`
- ✅ Rota `/embedded` no React filtrada por `ghl_location_id`
- ✅ Layout sem header de navegação no modo embedded

**Consistência de tipos:**
- `useEmbeddedMode` retorna `ghlLocationId: string | null` — usado como `ghlLocationId ?? undefined` ao passar para props que aceitam `string | undefined` ✅
- `postMessage('wpp:close', '*')` no EmbeddedLayout — `inject.js` escuta exatamente `e.data === 'wpp:close'` ✅
- `defaultFilters={{ ghl_location_id: locationId }}` — campo `ghl_location_id` existe em `CampaignFilters` ✅

**Sem placeholders:** todos os steps têm código completo ✅

import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './components/dashboard/Dashboard'
import CampaignWizard from './components/campaign/CampaignWizard'
import CampaignsPage from './pages/CampaignsPage'
import Layout from './components/layout/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import { ToastProvider, useToast } from './components/ui/Toast'
import { useNavigation, usePageTitle } from './hooks/useNavigation'
import { CampaignCreateRequest } from './types/api'
import { API_BASE_URL } from './config/env'
import './index.css'

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000, // 30 seconds
    },
  },
})

const App: React.FC = () => {
  // Use the new navigation system
  const {
    activeRoute,
    setActiveRoute,
    breadcrumbs
  } = useNavigation('/')

  // Set page title based on current route
  usePageTitle(activeRoute)

  const { addToast } = useToast()

  // Listen for navigation events from dashboard components
  React.useEffect(() => {
    const handleNavigateEvent = (event: CustomEvent<{ route: string }>) => {
      const { route } = event.detail;
      setActiveRoute(route);
    };

    window.addEventListener('navigate', handleNavigateEvent as EventListener);
    return () => window.removeEventListener('navigate', handleNavigateEvent as EventListener);
  }, [setActiveRoute]);

  const handleCreateCampaign = async (campaignData: CampaignCreateRequest) => {
    try {
      const response = await fetch(`${API_BASE_URL}/campaigns`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(campaignData),
      })

      if (!response.ok) {
        throw new Error('Failed to create campaign')
      }

      const result = await response.json()
      // Return to dashboard after successful creation
      setActiveRoute('/')
      addToast({ type: 'success', title: 'Campanha criada com sucesso!' })
    } catch (error) {
      addToast({ type: 'error', title: 'Erro ao criar campanha', message: 'Tente novamente.' })
    }
  }

  const renderContent = () => {
    switch (activeRoute) {
      case '/':
        return (
          <Dashboard
            onNavigateToCampaign={() => setActiveRoute('/campaigns/new')}
            onNavigateToManagement={() => setActiveRoute('/campaigns')}
          />
        )
      case '/campaigns/new':
        return (
          <CampaignWizard
            onSubmit={handleCreateCampaign}
            onCancel={() => setActiveRoute('/')}
          />
        )
      case '/campaigns':
        return (
          <CampaignsPage
            onCreateCampaign={() => setActiveRoute('/campaigns/new')}
          />
        )
      case '/analytics':
        return (
          <div className="p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Analytics</h2>
            <p className="text-gray-600">Analytics dashboard coming soon...</p>
          </div>
        )
      case '/contacts':
        return (
          <div className="p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Contatos</h2>
            <p className="text-gray-600">Contact management coming soon...</p>
          </div>
        )
      case '/settings':
        return (
          <div className="p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Configurações</h2>
            <p className="text-gray-600">Settings panel coming soon...</p>
          </div>
        )
      default:
        return <Dashboard />
    }
  }

  return (
    <Layout currentRoute={activeRoute} onNavigate={setActiveRoute}>
      {renderContent()}
    </Layout>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <App />
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)

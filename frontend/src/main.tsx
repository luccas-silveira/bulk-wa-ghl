import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './components/dashboard/Dashboard'
import CampaignWizard from './components/campaign/CampaignWizard'
import CampaignsPage from './pages/CampaignsPage'
import Layout from './components/layout/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import NotFound from './components/NotFound'
import { ToastProvider, useToast } from './components/ui/Toast'
import { CampaignCreateRequest } from './types/api'
import { API_BASE_URL } from './config/env'
import './index.css'

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000,
    },
  },
})

// ProtectedRoute stub — passes children through; ready for future auth logic
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <>{children}</>
}

const AppRoutes: React.FC = () => {
  const navigate = useNavigate()
  const { addToast } = useToast()

  const handleCreateCampaign = async (campaignData: CampaignCreateRequest) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/campaigns`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(campaignData),
    })

    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      throw new Error(body?.detail?.message || body?.message || 'Falha ao criar campanha')
    }

    navigate('/')
    addToast({ type: 'success', title: 'Campanha criada com sucesso!' })
  }

  return (
    <Routes>
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout>
              <Dashboard
                onNavigateToCampaign={() => navigate('/campaigns/new')}
                onNavigateToManagement={() => navigate('/campaigns')}
              />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/campaigns/new"
        element={
          <ProtectedRoute>
            <Layout>
              <CampaignWizard
                onSubmit={handleCreateCampaign}
                onCancel={() => navigate('/')}
              />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/campaigns"
        element={
          <ProtectedRoute>
            <Layout>
              <CampaignsPage
                onCreateCampaign={() => navigate('/campaigns/new')}
              />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/analytics"
        element={
          <ProtectedRoute>
            <Layout>
              <div className="p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">Analytics</h2>
                <p className="text-gray-600">Analytics dashboard coming soon...</p>
              </div>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Layout>
              <div className="p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">Configurações</h2>
                <p className="text-gray-600">Settings panel coming soon...</p>
              </div>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ToastProvider>
            <AppRoutes />
          </ToastProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)

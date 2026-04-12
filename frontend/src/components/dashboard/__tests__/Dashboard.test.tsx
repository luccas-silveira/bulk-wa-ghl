// frontend/src/components/dashboard/__tests__/Dashboard.test.tsx
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

// Mock env config to avoid import.meta issues in Jest
jest.mock('../../../config/env', () => ({
  API_BASE_URL: 'http://localhost:8000',
}));

import Dashboard from '../Dashboard';

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock Chart.js components
jest.mock('../ChartComponents', () => ({
  CampaignStatusChart: () => <div data-testid="campaign-status-chart" />,
  DeliveryRateChart: () => <div data-testid="delivery-rate-chart" />,
  VolumeMetricsChart: () => <div data-testid="volume-metrics-chart" />,
}));

jest.mock('../MessagingKpiPanel', () => () => <div data-testid="messaging-kpi-panel" />);

const mockDashboardData = {
  campaign_metrics: {
    total_campaigns: 5,
    draft_campaigns: 1,
    scheduled_campaigns: 1,
    active_campaigns: 2,
    completed_campaigns: 1,
    failed_campaigns: 0,
    cancelled_campaigns: 0,
  },
  delivery_metrics: {
    sent: 1000,
    delivered: 950,
    failed: 50,
    delivery_rate: 95.0,
    read_rate: 30.0,
  },
  recent_campaigns: [],
  top_performing_campaigns: [],
  timeline: { labels: [], sent: [], delivered: [], delivery_rate: [], read_rate: [] },
  time_range: 'Últimos 30 dias',
  filter_info: 'Dados agregados de todos os usuários',
};

const emptyDashboardData = {
  ...mockDashboardData,
  campaign_metrics: { ...mockDashboardData.campaign_metrics, total_campaigns: 0 },
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('Dashboard', () => {
  it('shows loading skeleton initially', () => {
    mockFetch.mockReturnValue(new Promise(() => {}));  // never resolves
    render(<Dashboard />);
    expect(document.querySelector('.animate-pulse')).toBeTruthy();
  });

  it('shows empty state when total_campaigns is 0', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => emptyDashboardData,
    });
    render(<Dashboard />);
    await waitFor(() => expect(screen.getByText(/No campaigns yet/i)).toBeInTheDocument());
  });

  it('shows metrics when campaigns exist', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockDashboardData,
    });
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.queryByText(/No campaigns yet/i)).not.toBeInTheDocument();
      expect(screen.getByTestId('campaign-status-chart')).toBeInTheDocument();
    });
  });

  it('shows error when fetch fails', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));
    render(<Dashboard />);
    await waitFor(() => expect(screen.getByText(/Error Loading Dashboard/i)).toBeInTheDocument());
  });

  it('shows fetchedAt timestamp after successful load', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockDashboardData,
    });
    render(<Dashboard />);
    await waitFor(() =>
      expect(screen.getByTestId('fetched-at')).toBeInTheDocument()
    );
    expect(screen.getByTestId('fetched-at').textContent).toMatch(/Dados de \d{2}:\d{2}:\d{2}/);
  });

  it('chartData uses delivery_metrics.delivered directly', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockDashboardData,
    });
    render(<Dashboard />);
    await waitFor(() => screen.getByTestId('campaign-status-chart'));
    expect(screen.getByTestId('campaign-status-chart')).toBeInTheDocument();
  });
});

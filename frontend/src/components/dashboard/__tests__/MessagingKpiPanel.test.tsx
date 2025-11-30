import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MessagingKpiPanel from '../MessagingKpiPanel';
import { analyticsService } from '../../../services/analytics-service';
import type { MessagingKpiResponse } from '../../../types/analytics';

jest.mock('../../../services/analytics-service');

jest.mock('react-chartjs-2', () => ({
  Line: (props: any) => <div data-testid="mock-line-chart" {...props} />,
  Bar: (props: any) => <div data-testid="mock-bar-chart" {...props} />,
}));

const mockKpiData: MessagingKpiResponse = {
  totals: {
    sent: 12500,
    delivered: 11800,
    responses: 720,
    deliveryRate: 94.4,
    responseRate: 12.5,
  },
  timeline: {
    labels: ['Seg', 'Ter', 'Qua'],
    sent: [4000, 4500, 4000],
    delivered: [3800, 4300, 3700],
    responses: [180, 260, 280],
  },
  breakdown: [
    { label: 'Campanhas', sent: 6000, delivered: 5600, responses: 350 },
    { label: 'Fluxos', sent: 6500, delivered: 6200, responses: 370 },
  ],
};

const renderWithClient = () => {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MessagingKpiPanel />
    </QueryClientProvider>
  );
};

describe('MessagingKpiPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('exibe KPIs e gráficos após carregar', async () => {
    (analyticsService.fetchKpis as jest.Mock).mockResolvedValue(mockKpiData);

    renderWithClient();

    expect(screen.getByTestId('kpi-loading')).toBeInTheDocument();

    await waitFor(() => expect(screen.getByTestId('kpi-sent-card-value')).toHaveTextContent('12.500'));
    expect(screen.getByTestId('kpi-delivered-card-value')).toHaveTextContent('11.800');
    expect(screen.getByTestId('kpi-response-card-value')).toHaveTextContent('720');
    expect(screen.getByTestId('kpi-rate-card-value')).toHaveTextContent('12.5%');

    expect(screen.getByTestId('mock-line-chart')).toBeInTheDocument();
    expect(screen.getByTestId('mock-bar-chart')).toBeInTheDocument();
  });

  it('permite selecionar diferentes ranges sem quebrar layout', async () => {
    (analyticsService.fetchKpis as jest.Mock).mockResolvedValue(mockKpiData);

    renderWithClient();

    const rangeSelector = screen.getByTestId('kpi-range-selector');
    expect(rangeSelector.querySelectorAll('button')).toHaveLength(4);

    await waitFor(() => expect(screen.getByTestId('kpi-sent-card-value')).toBeInTheDocument());
  });

  it('mostra estado de erro e ação de retry', async () => {
    (analyticsService.fetchKpis as jest.Mock).mockRejectedValueOnce(new Error('Server offline'));

    renderWithClient();

    await waitFor(() => expect(screen.getByTestId('kpi-error')).toBeInTheDocument());
    expect(screen.getByText(/Server offline/i)).toBeInTheDocument();
  });
});

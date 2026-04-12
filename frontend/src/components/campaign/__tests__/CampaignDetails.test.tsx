// frontend/src/components/campaign/__tests__/CampaignDetails.test.tsx
import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CampaignDetails from '../CampaignDetails';
import { campaignService } from '../../../services/campaign-service';
import type { CampaignDetailsResponse } from '../../../types/campaign';

jest.mock('../../../config/env', () => ({ API_BASE_URL: 'http://localhost:8000' }));
jest.mock('../../../services/campaign-service');

const mockStats = {
  total_messages: 100,
  sent: 50,
  delivered: 45,
  read: 30,
  failed: 5,
  pending: 50,
  delivery_rate: 45,
  read_rate: 30,
};

const baseCampaign = {
  id: 1,
  name: 'Test Campaign',
  ghl_location_id: null,
  ghl_location_name: null,
  ghl_user_id: null,
  ghl_user_name: null,
  sending_speed: 'medium' as const,
  schedule_type: 'immediate' as const,
  scheduled_time: null,
  paused_at: null,
  created_at: '2026-04-01T00:00:00Z',
  updated_at: '2026-04-01T00:00:00Z',
};

function makeDetails(status: string): CampaignDetailsResponse {
  return {
    campaign: { ...baseCampaign, status: status as any },
    statistics: mockStats,
    timeline: [],
    recent_messages: [],
  };
}

function renderDetails(queryClient?: QueryClient) {
  const client = queryClient ?? new QueryClient({
    defaultOptions: { queries: { retry: false, networkMode: 'always' } },
  });
  return render(
    <QueryClientProvider client={client}>
      <CampaignDetails campaignId={1} />
    </QueryClientProvider>
  );
}

describe('CampaignDetails — FRONT-33: refetchInterval', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  it('refaz consulta a cada 5s quando campanha está em execução', async () => {
    (campaignService.getCampaignDetails as jest.Mock).mockResolvedValue(
      makeDetails('executing')
    );

    renderDetails();

    // Resolve initial fetch
    await act(async () => {
      jest.runAllTimers();
    });
    await waitFor(() => screen.getByText('Test Campaign'));
    expect(campaignService.getCampaignDetails).toHaveBeenCalledTimes(1);

    // Advance past the 5s refetch interval
    await act(async () => {
      jest.advanceTimersByTime(5001);
    });

    await waitFor(() =>
      expect(campaignService.getCampaignDetails).toHaveBeenCalledTimes(2)
    );
  });

  it('não refaz consulta automaticamente quando campanha está concluída', async () => {
    (campaignService.getCampaignDetails as jest.Mock).mockResolvedValue(
      makeDetails('completed')
    );

    renderDetails();

    await act(async () => { jest.runAllTimers(); });
    await waitFor(() => screen.getByText('Test Campaign'));
    expect(campaignService.getCampaignDetails).toHaveBeenCalledTimes(1);

    await act(async () => { jest.advanceTimersByTime(10000); });

    // Should still be only 1 call — no auto-refetch
    expect(campaignService.getCampaignDetails).toHaveBeenCalledTimes(1);
  });
});

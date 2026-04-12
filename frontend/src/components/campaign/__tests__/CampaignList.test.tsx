// frontend/src/components/campaign/__tests__/CampaignList.test.tsx
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CampaignList from '../CampaignList';
import { campaignService } from '../../../services/campaign-service';
import type { CampaignWithStats, CampaignsListResponse } from '../../../types/campaign';

jest.mock('../../../config/env', () => ({ API_BASE_URL: 'http://localhost:8000' }));
jest.mock('../../../services/campaign-service');

const makeClient = () =>
  new QueryClient({ defaultOptions: { queries: { retry: false, networkMode: 'always' }, mutations: { networkMode: 'always' } } });

const executingCampaign: CampaignWithStats = {
  id: 1,
  name: 'Campanha Alpha',
  status: 'executing',
  ghl_location_id: 'loc-1',
  ghl_location_name: 'Location 1',
  ghl_user_id: 'u1',
  ghl_user_name: 'User 1',
  sending_speed: 'medium',
  schedule_type: 'immediate',
  scheduled_time: null,
  paused_at: null,
  created_at: '2026-04-01T00:00:00Z',
  updated_at: '2026-04-01T00:00:00Z',
  message_stats: { total: 100, sent: 50, delivered: 45, read: 30, failed: 5, pending: 50 },
  progress_percent: 50,
};

const listResponse: CampaignsListResponse = {
  campaigns: [executingCampaign],
  count: 1,
  limit: 20,
  offset: 0,
};

function renderList(client = makeClient()) {
  return render(
    <QueryClientProvider client={client}>
      <CampaignList />
    </QueryClientProvider>
  );
}

describe('CampaignList — FRONT-30: optimistic updates', () => {
  it('muda status para "Paused" imediatamente ao pausar, sem esperar a API', async () => {
    (campaignService.listCampaigns as jest.Mock).mockResolvedValue(listResponse);

    let resolvePause!: (v: any) => void;
    (campaignService.pauseCampaign as jest.Mock).mockImplementation(
      () => new Promise((res) => { resolvePause = res; })
    );

    renderList();

    // Wait for campaign to appear with "Executing" status
    await waitFor(() => screen.getByText('Campanha Alpha'));
    expect(screen.getByText('Executing')).toBeInTheDocument();

    // Click Pause button
    await userEvent.click(screen.getByTitle('Pause campaign execution'));

    // Badge should optimistically show "Paused" before API resolves
    await waitFor(() => expect(screen.getByText('Paused')).toBeInTheDocument());

    // Resolve the hanging promise
    resolvePause({ message: 'ok', campaign: { ...executingCampaign, status: 'paused' } });
  });

  it('reverte status ao erro de pause', async () => {
    (campaignService.listCampaigns as jest.Mock).mockResolvedValue(listResponse);
    (campaignService.pauseCampaign as jest.Mock).mockRejectedValue(new Error('Falha'));

    renderList();
    await waitFor(() => screen.getByText('Campanha Alpha'));

    await userEvent.click(screen.getByTitle('Pause campaign execution'));

    // After error, status should revert to "Executing"
    await waitFor(() => expect(screen.getByText('Executing')).toBeInTheDocument());
  });

  it('remove campanha otimisticamente ao deletar', async () => {
    const deletableCampaign: CampaignWithStats = {
      ...executingCampaign,
      id: 2,
      name: 'Campanha Beta',
      status: 'completed',
    };
    (campaignService.listCampaigns as jest.Mock).mockResolvedValue({
      ...listResponse,
      campaigns: [deletableCampaign],
    });

    let resolveDelete!: (v: any) => void;
    (campaignService.deleteCampaign as jest.Mock).mockImplementation(
      () => new Promise((res) => { resolveDelete = res; })
    );

    renderList();
    await waitFor(() => screen.getByText('Campanha Beta'));

    // Click Delete → confirm dialog → click Confirm
    await userEvent.click(screen.getByTitle('Delete campaign'));
    await userEvent.click(screen.getByText('Confirm'));

    // Campaign disappears immediately (optimistic)
    await waitFor(() =>
      expect(screen.queryByText('Campanha Beta')).not.toBeInTheDocument()
    );

    resolveDelete({ message: 'ok', campaign_id: 2 });
  });
});

describe('CampaignList — CAMP-27: filter antes de map na paginação', () => {
  it('não gera itens null quando há menos de 5 páginas', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    const campaigns: CampaignWithStats[] = [
      { ...executingCampaign, id: 1, name: 'C1' },
      { ...executingCampaign, id: 2, name: 'C2' },
    ];
    (campaignService.listCampaigns as jest.Mock).mockResolvedValue({
      campaigns,
      count: 3,
      limit: 2,
      offset: 0,
    });

    renderList();
    await waitFor(() => screen.getByText('C1'));

    // React emits console.error for null keys. If fix is correct, no such error.
    const keyErrors = consoleSpy.mock.calls.filter(
      args => typeof args[0] === 'string' && args[0].includes('key')
    );
    expect(keyErrors).toHaveLength(0);

    consoleSpy.mockRestore();
  });
});

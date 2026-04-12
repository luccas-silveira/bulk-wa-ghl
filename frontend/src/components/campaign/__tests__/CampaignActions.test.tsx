// frontend/src/components/campaign/__tests__/CampaignActions.test.tsx
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CampaignActions from '../CampaignActions';
import type { Campaign } from '../../../types/campaign';

jest.mock('../../../config/env', () => ({ API_BASE_URL: 'http://localhost:8000' }));

const baseCampaign: Campaign = {
  id: 1,
  name: 'Campanha Importante',
  status: 'completed',
  ghl_location_id: null,
  ghl_location_name: null,
  ghl_user_id: null,
  ghl_user_name: null,
  sending_speed: 'medium',
  schedule_type: 'immediate',
  scheduled_time: null,
  paused_at: null,
  created_at: '2026-04-01T00:00:00Z',
  updated_at: '2026-04-01T00:00:00Z',
};

describe('CampaignActions — FRONT-34: confirmação de delete com nome', () => {
  it('mostra input de nome ao clicar Delete', async () => {
    const user = userEvent.setup();
    render(
      <CampaignActions
        campaign={baseCampaign}
        onDelete={jest.fn()}
      />
    );

    await user.click(screen.getByTitle('Delete campaign'));

    expect(screen.getByTestId('delete-name-input')).toBeInTheDocument();
    expect(screen.getByTestId('delete-confirm-btn')).toBeDisabled();
  });

  it('botão confirm fica desabilitado com nome incorreto', async () => {
    const user = userEvent.setup();
    render(
      <CampaignActions campaign={baseCampaign} onDelete={jest.fn()} />
    );

    await user.click(screen.getByTitle('Delete campaign'));
    await user.type(screen.getByTestId('delete-name-input'), 'Nome Errado');

    expect(screen.getByTestId('delete-confirm-btn')).toBeDisabled();
  });

  it('botão confirm fica habilitado quando nome está correto', async () => {
    const user = userEvent.setup();
    render(
      <CampaignActions campaign={baseCampaign} onDelete={jest.fn()} />
    );

    await user.click(screen.getByTitle('Delete campaign'));
    await user.type(
      screen.getByTestId('delete-name-input'),
      'Campanha Importante'
    );

    expect(screen.getByTestId('delete-confirm-btn')).not.toBeDisabled();
  });

  it('chama onDelete ao confirmar com nome correto', async () => {
    const onDelete = jest.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(
      <CampaignActions campaign={baseCampaign} onDelete={onDelete} />
    );

    await user.click(screen.getByTitle('Delete campaign'));
    await user.type(
      screen.getByTestId('delete-name-input'),
      'Campanha Importante'
    );
    await user.click(screen.getByTestId('delete-confirm-btn'));

    await waitFor(() => expect(onDelete).toHaveBeenCalledWith(1));
  });

  it('limpa o input ao cancelar e fecha o modal', async () => {
    const user = userEvent.setup();
    render(
      <CampaignActions campaign={baseCampaign} onDelete={jest.fn()} />
    );

    await user.click(screen.getByTitle('Delete campaign'));
    await user.type(screen.getByTestId('delete-name-input'), 'algo');
    await user.click(screen.getByText('Cancelar'));

    expect(screen.queryByTestId('delete-name-input')).not.toBeInTheDocument();
    expect(screen.getByTitle('Delete campaign')).toBeInTheDocument();
  });
});

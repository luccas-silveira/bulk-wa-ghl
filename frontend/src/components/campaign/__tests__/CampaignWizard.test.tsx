// frontend/src/components/campaign/__tests__/CampaignWizard.test.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CampaignWizard from '../CampaignWizard';

jest.mock('../../../config/env', () => ({ API_BASE_URL: 'http://localhost:8000' }));

jest.mock('../../../hooks/useGHLUsers', () => ({
  useGHLUsers: jest.fn(() => ({
    users: [{ ghl_user_id: 'u1', name: 'User One', email: 'u1@test.com' }],
    loading: false,
    error: null,
  })),
}));

jest.mock('../../ui/Toast', () => ({
  useToast: () => ({ addToast: jest.fn() }),
  ToastProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const defaultProps = {
  onSubmit: jest.fn(),
  onCancel: jest.fn(),
};

// Avança até o step 2 preenchendo o step 1 válido
async function advanceToStep2() {
  const user = userEvent.setup();
  await user.type(
    screen.getByPlaceholderText('Digite o nome da campanha'),
    'Minha Campanha'
  );
  // O checkbox de usuário fica dentro de <details>; está no DOM mesmo fechado
  const checkbox = screen.getByRole('checkbox', { name: /User One/i });
  await user.click(checkbox);
  await user.click(screen.getByText('Próximo'));
  return user;
}

describe('CampaignWizard — FRONT-26: limpar erros ao voltar', () => {
  it('erros do step 2 somem ao clicar Anterior', async () => {
    render(<CampaignWizard {...defaultProps} />);
    const user = await advanceToStep2();

    // Agora no step 2 — clicar Próximo sem mensagem exibe erro
    await user.click(screen.getByText('Próximo'));
    expect(
      screen.getByText(/Pelo menos uma mensagem/i)
    ).toBeInTheDocument();

    // Clicar Anterior — erro deve sumir
    await user.click(screen.getByText('Anterior'));
    expect(
      screen.queryByText(/Pelo menos uma mensagem/i)
    ).not.toBeInTheDocument();
  });
});

describe('CampaignWizard — FRONT-27: foco no heading ao mudar step', () => {
  it('heading do step 1 recebe foco após renderização inicial', () => {
    render(<CampaignWizard {...defaultProps} />);
    expect(screen.getByText('Detalhes da Campanha')).toHaveFocus();
  });

  it('heading do step 2 recebe foco após avançar', async () => {
    render(<CampaignWizard {...defaultProps} />);
    await advanceToStep2();
    expect(screen.getByText('Mensagens da Campanha')).toHaveFocus();
  });
});

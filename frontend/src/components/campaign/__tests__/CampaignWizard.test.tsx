// frontend/src/components/campaign/__tests__/CampaignWizard.test.tsx
import React from 'react';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CampaignWizard from '../CampaignWizard';
import Papa from 'papaparse';

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

jest.mock('papaparse', () => ({
  parse: jest.fn(),
}));

jest.mock('libphonenumber-js', () => ({
  parsePhoneNumber: jest.fn((phone: string) => ({
    isValid: () => true,
    format: () => phone,
  })),
  isValidPhoneNumber: jest.fn(() => true),
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

describe('CampaignWizard — FRONT-28: localStorage column mapping', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('salva no localStorage quando columnMapping muda', () => {
    const setSpy = jest.spyOn(Storage.prototype, 'setItem');
    render(<CampaignWizard {...defaultProps} />);
    // useEffect com [columnMapping] dispara na montagem
    expect(setSpy).toHaveBeenCalledWith(
      'campaign-wizard-column-mapping',
      JSON.stringify({ phone: '', name: '', email: '' })
    );
    setSpy.mockRestore();
  });

  it('lê do localStorage na inicialização', () => {
    const getSpy = jest.spyOn(Storage.prototype, 'getItem');
    render(<CampaignWizard {...defaultProps} />);
    expect(getSpy).toHaveBeenCalledWith('campaign-wizard-column-mapping');
    getSpy.mockRestore();
  });
});

async function advanceToStep4() {
  const user = userEvent.setup();

  // Step 1: fill name + select user
  await user.type(screen.getByPlaceholderText('Digite o nome da campanha'), 'Camp');
  const checkbox = screen.getByRole('checkbox', { name: /User One/i });
  await user.click(checkbox);
  await user.click(screen.getByText('Próximo'));

  // Step 2: add a message text
  await user.type(screen.getByPlaceholderText(/texto da mensagem/i), 'Olá mundo');
  await user.click(screen.getByText('Próximo'));

  // Step 3: set up Papa.parse mock to fire synchronously, then trigger upload
  (Papa.parse as jest.Mock).mockImplementation((_file: File, opts: any) => {
    act(() => {
      opts.complete({
        data: [{ telefone: '+5511999999999', nome: 'Contato Teste' }],
        meta: {
          fields: ['telefone', 'nome'],
          delimiter: ',',
          linebreak: '\n',
          abortCSV: false,
          cursor: 0,
          truncated: false,
        },
        errors: [],
      });
    });
  });

  const fileInput = document.querySelector('input[accept=".csv"]') as HTMLInputElement;
  const mockFile = new File(['telefone,nome\n+5511999999999,Contato Teste'], 'contacts.csv', {
    type: 'text/csv',
  });
  await user.upload(fileInput, mockFile);

  // Mapping UI appears after parse; 'telefone' auto-detected as phone column
  await user.click(screen.getByText('Aplicar Mapeamento'));

  // Advance to step 4
  await user.click(screen.getByText('Próximo'));

  return user;
}

describe('CampaignWizard — CAMP-26: spinner no botão submit', () => {
  it('exibe botão submit com data-testid correto no step 4', async () => {
    render(<CampaignWizard {...defaultProps} />);
    await advanceToStep4();

    const submitBtn = screen.getByTestId('wizard-submit-btn');
    expect(submitBtn).toBeInTheDocument();
    // Spinner não aparece quando loading=false
    expect(screen.queryByTestId('submit-spinner')).not.toBeInTheDocument();
    // Texto correto no botão
    expect(submitBtn).toHaveTextContent('Criar Campanha');
  });
});

// frontend/src/components/ui/__tests__/Input.test.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Input from '../Input';

describe('Input — accessibility fix (FRONT-11)', () => {
  it('label htmlFor aponta para o id do input', () => {
    render(<Input label="Nome completo" />);

    const label = screen.getByText('Nome completo');
    const input = screen.getByRole('textbox');

    // htmlFor no label deve coincidir com id do input
    expect(label).toHaveAttribute('for');
    expect(input).toHaveAttribute('id');
    expect(label.getAttribute('for')).toBe(input.getAttribute('id'));
  });

  it('clicar no label foca o input', async () => {
    render(<Input label="Email" />);

    const label = screen.getByText('Email');
    await userEvent.click(label);

    const input = screen.getByRole('textbox');
    expect(input).toHaveFocus();
  });

  it('id gerado é estável entre re-renders', () => {
    const { rerender } = render(<Input label="Estável" />);
    const idBefore = screen.getByRole('textbox').getAttribute('id');

    rerender(<Input label="Estável" />);
    const idAfter = screen.getByRole('textbox').getAttribute('id');

    expect(idBefore).toBe(idAfter);
    expect(idBefore).not.toBeNull();
  });

  it('id externo passado via props tem precedência sobre o gerado', () => {
    render(<Input label="Com ID" id="meu-input-customizado" />);

    const input = screen.getByRole('textbox');
    const label = screen.getByText('Com ID');

    expect(input).toHaveAttribute('id', 'meu-input-customizado');
    expect(label).toHaveAttribute('for', 'meu-input-customizado');
  });

  it('funciona sem label — não renderiza label element', () => {
    render(<Input placeholder="Sem label" />);
    expect(screen.queryByRole('label')).not.toBeInTheDocument();
  });
});

describe('Input — password toggle ARIA (FRONT-15)', () => {
  it('password toggle has aria-label "Mostrar senha" by default', () => {
    render(<Input type="password" />);
    const btn = screen.getByRole('button', { name: 'Mostrar senha' });
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveAttribute('aria-pressed', 'false');
  });

  it('password toggle aria-label changes to "Ocultar senha" when active', async () => {
    render(<Input type="password" />);
    const btn = screen.getByRole('button', { name: 'Mostrar senha' });
    await userEvent.click(btn);
    expect(screen.getByRole('button', { name: 'Ocultar senha' })).toHaveAttribute('aria-pressed', 'true');
  });
});

describe('Input — controlled/uncontrolled guard (FRONT-19)', () => {
  const originalEnv = process.env.NODE_ENV;

  beforeEach(() => {
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    (process.env as any).NODE_ENV = 'development';
  });

  afterEach(() => {
    (console.warn as jest.Mock).mockRestore();
    (process.env as any).NODE_ENV = originalEnv;
  });

  it('warns when both value and defaultValue are provided', () => {
    render(<Input value="a" defaultValue="b" onChange={() => {}} />);
    expect(console.warn).toHaveBeenCalledWith(
      expect.stringContaining('[Input]')
    );
  });

  it('does not warn with only value', () => {
    render(<Input value="a" onChange={() => {}} />);
    expect(console.warn).not.toHaveBeenCalled();
  });
});

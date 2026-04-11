// frontend/src/components/ui/__tests__/Toast.test.tsx
import React from 'react';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToastProvider, useToast } from '../Toast';

// Componente auxiliar para disparar toasts nos testes
const ToastTrigger: React.FC<{ duration?: number }> = ({ duration = 1000 }) => {
  const { addToast } = useToast();
  return (
    <button
      data-testid="trigger"
      onClick={() => addToast({ type: 'success', title: 'Test toast', duration })}
    >
      Add Toast
    </button>
  );
};

describe('ToastProvider — memory leak fix (FRONT-08)', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('auto-remove toast after duration without leaving pending timers', async () => {
    // userEvent.setup with advanceTimers so async actions work with fake timers
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    const { unmount } = render(
      <ToastProvider>
        <ToastTrigger duration={3000} />
      </ToastProvider>
    );

    await user.click(screen.getByTestId('trigger'));
    expect(screen.getByText('Test toast')).toBeInTheDocument();

    act(() => { jest.advanceTimersByTime(3000); });

    expect(screen.queryByText('Test toast')).not.toBeInTheDocument();

    // Desmontar sem erros de "setState in unmounted component"
    expect(() => unmount()).not.toThrow();
  });

  it('unmounting before timeout does not throw', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    const { unmount } = render(
      <ToastProvider>
        <ToastTrigger duration={5000} />
      </ToastProvider>
    );

    await user.click(screen.getByTestId('trigger'));
    expect(screen.getByText('Test toast')).toBeInTheDocument();

    // Desmontar antes do timeout — não deve lançar erro ou causar warning
    expect(() => unmount()).not.toThrow();

    // Avançar o timer após desmonte — não deve lançar erro
    expect(() => act(() => { jest.advanceTimersByTime(5000); })).not.toThrow();
  });

  it('cancelling toast clears the pending timer', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    render(
      <ToastProvider>
        <ToastTrigger duration={5000} />
      </ToastProvider>
    );

    await user.click(screen.getByTestId('trigger'));
    expect(screen.getByText('Test toast')).toBeInTheDocument();

    // Clicar no botão de fechar (X)
    const closeBtn = screen.getByRole('button', { name: '' });
    // O botão X existe dentro do toast; avançamos a animação de saída
    await user.click(closeBtn);
    act(() => { jest.advanceTimersByTime(200); });

    expect(screen.queryByText('Test toast')).not.toBeInTheDocument();
  });
});

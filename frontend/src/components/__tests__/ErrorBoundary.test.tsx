import React from 'react';
import { render, screen, act } from '@testing-library/react';
import ErrorBoundary from '../ErrorBoundary';

// Polyfill PromiseRejectionEvent for JSDOM environments that don't have it
if (typeof PromiseRejectionEvent === 'undefined') {
  class PromiseRejectionEventPolyfill extends Event {
    promise: Promise<unknown>;
    reason: unknown;
    constructor(type: string, init: { promise: Promise<unknown>; reason: unknown }) {
      super(type, { cancelable: true });
      this.promise = init.promise;
      this.reason = init.reason;
    }
  }
  (global as Record<string, unknown>).PromiseRejectionEvent = PromiseRejectionEventPolyfill;
}

// Mock Sentry so import.meta.env doesn't blow up in Jest
jest.mock('../../config/sentry', () => ({
  Sentry: { captureException: jest.fn() },
  initSentry: jest.fn(),
}));

// Retrieve the mock after jest.mock hoisting
const mockCaptureException = (jest.requireMock('../../config/sentry') as {
  Sentry: { captureException: jest.Mock };
}).Sentry.captureException;

// Suppress console.error for expected error throws
beforeEach(() => {
  jest.spyOn(console, 'error').mockImplementation(() => {});
  mockCaptureException.mockClear();
});
afterEach(() => {
  (console.error as jest.Mock).mockRestore();
});

const Bomb: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow }) => {
  if (shouldThrow) throw new Error('test explosion');
  return <div>Safe</div>;
};

describe('ErrorBoundary (FRONT-16, FRONT-17, FRONT-40)', () => {
  it('renders children when no error', () => {
    render(<ErrorBoundary><Bomb /></ErrorBoundary>);
    expect(screen.getByText('Safe')).toBeInTheDocument();
  });

  it('shows fallback UI when child throws', () => {
    render(<ErrorBoundary><Bomb shouldThrow /></ErrorBoundary>);
    expect(screen.getByText('Algo deu errado')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Recarregar' })).toBeInTheDocument();
  });

  it('calls Sentry.captureException when child throws', () => {
    render(<ErrorBoundary><Bomb shouldThrow /></ErrorBoundary>);
    expect(mockCaptureException).toHaveBeenCalledTimes(1);
    expect(mockCaptureException).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({ extra: expect.objectContaining({ componentStack: expect.anything() }) })
    );
  });

  it('captures unhandledrejection events via Sentry', () => {
    render(<ErrorBoundary><div>OK</div></ErrorBoundary>);
    // Create a rejected promise and immediately suppress the unhandled rejection
    // so Node doesn't crash — the test only cares that the event listener fires.
    const rejectedPromise = Promise.reject(new Error('async boom'));
    rejectedPromise.catch(() => { /* suppress */ });
    act(() => {
      window.dispatchEvent(
        new PromiseRejectionEvent('unhandledrejection', {
          promise: rejectedPromise,
          reason: new Error('async boom'),
        })
      );
    });
    expect(mockCaptureException).toHaveBeenCalledWith(
      expect.any(Error)
    );
  });

  it('fallback UI uses shadow-ghl-lg not shadow-lg', () => {
    render(<ErrorBoundary><Bomb shouldThrow /></ErrorBoundary>);
    const card = screen.getByText('Algo deu errado').closest('div');
    expect(card?.className).toContain('shadow-ghl-lg');
    expect(card?.className).not.toMatch(/\bshadow-lg\b/);
  });
});

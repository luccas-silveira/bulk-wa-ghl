import React from 'react';
import { render, screen } from '@testing-library/react';
import Button from '../Button';

jest.mock('../../../config/env', () => ({ API_BASE_URL: 'http://localhost:8000' }));

describe('Button — dev warning for inaccessible buttons (FRONT-13)', () => {
  const originalEnv = process.env.NODE_ENV;

  beforeEach(() => {
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    (process.env as any).NODE_ENV = 'development';
  });

  afterEach(() => {
    (console.warn as jest.Mock).mockRestore();
    (process.env as any).NODE_ENV = originalEnv;
  });

  it('warns when button has no children and no aria-label', () => {
    render(<Button />);
    expect(console.warn).toHaveBeenCalledWith(
      expect.stringContaining('[Button]')
    );
  });

  it('does not warn when aria-label is provided', () => {
    render(<Button aria-label="Fechar modal" />);
    expect(console.warn).not.toHaveBeenCalled();
  });

  it('does not warn when children are provided', () => {
    render(<Button>Salvar</Button>);
    expect(console.warn).not.toHaveBeenCalled();
  });
});

describe('Button — isValidElement guard (FRONT-18)', () => {
  it('does not crash when icon is a plain string', () => {
    expect(() =>
      render(<Button icon={'not-an-element' as any}>Click</Button>)
    ).not.toThrow();
  });

  it('renders icon when a valid React element is passed', () => {
    const icon = <span data-testid="btn-icon">★</span>;
    render(<Button icon={icon}>Click</Button>);
    expect(screen.getByTestId('btn-icon')).toBeInTheDocument();
  });
});

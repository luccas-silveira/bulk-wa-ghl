import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Card, { MetricCard } from '../Card';

// Mock env config to avoid import.meta issues in Jest
jest.mock('../../../config/env', () => ({ API_BASE_URL: 'http://localhost:8000' }));

describe('Card — keyboard navigation (FRONT-12)', () => {
  it('clickable card fires onClick on Enter', async () => {
    const onClick = jest.fn();
    render(<Card clickable onClick={onClick} data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    card.focus();
    await userEvent.keyboard('{Enter}');
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('clickable card fires onClick on Space', async () => {
    const onClick = jest.fn();
    render(<Card clickable onClick={onClick} data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    card.focus();
    await userEvent.keyboard(' ');
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('non-clickable card does not fire onClick on Enter', async () => {
    const onClick = jest.fn();
    render(<Card onClick={onClick} data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    card.focus();
    await userEvent.keyboard('{Enter}');
    expect(onClick).not.toHaveBeenCalled();
  });

  it('clickable card still calls external onKeyDown in addition to built-in handler', async () => {
    const onKeyDown = jest.fn();
    render(<Card clickable onKeyDown={onKeyDown} data-testid="card">Content</Card>);
    const card = screen.getByTestId('card');
    card.focus();
    await userEvent.keyboard('{Enter}');
    expect(onKeyDown).toHaveBeenCalledTimes(1);
  });
});

describe('Card — elevated shadow token (FRONT-40)', () => {
  it('elevated variant includes shadow-ghl-lg class', () => {
    render(<Card variant="elevated" data-testid="card">Content</Card>);
    expect(screen.getByTestId('card').className).toContain('shadow-ghl-lg');
  });

  it('elevated variant does not include bare shadow-lg class', () => {
    render(<Card variant="elevated" data-testid="card">Content</Card>);
    expect(screen.getByTestId('card').className).not.toMatch(/\bshadow-lg\b/);
  });
});

describe('MetricCard — isValidElement guard (FRONT-18)', () => {
  it('renders normally with a valid React element icon', () => {
    const icon = <span data-testid="icon">★</span>;
    render(<MetricCard title="Total" value={42} icon={icon} />);
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('does not crash when icon is a plain string', () => {
    expect(() =>
      render(<MetricCard title="Total" value={42} icon={'not-an-element' as any} />)
    ).not.toThrow();
  });
});

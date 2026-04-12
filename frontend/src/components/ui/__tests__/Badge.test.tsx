import React from 'react';
import { render, screen } from '@testing-library/react';
import Badge from '../Badge';

jest.mock('../../../config/env', () => ({ API_BASE_URL: 'http://localhost:8000' }));

describe('Badge — remove button accessibility (FRONT-14)', () => {
  it('remove button has aria-label="Remover"', () => {
    render(<Badge removable onRemove={() => {}}>Tag</Badge>);
    const btn = screen.getByRole('button', { name: 'Remover' });
    expect(btn).toBeInTheDocument();
  });

  it('remove button does not contain sr-only span', () => {
    render(<Badge removable onRemove={() => {}}>Tag</Badge>);
    const btn = screen.getByRole('button', { name: 'Remover' });
    expect(btn.querySelector('.sr-only')).toBeNull();
  });

  it('SVG inside remove button has aria-hidden="true"', () => {
    render(<Badge removable onRemove={() => {}}>Tag</Badge>);
    const btn = screen.getByRole('button', { name: 'Remover' });
    const svg = btn.querySelector('svg');
    expect(svg).toHaveAttribute('aria-hidden', 'true');
  });
});

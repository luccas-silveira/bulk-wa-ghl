import React from 'react';
import { render, screen } from '@testing-library/react';
import MetricCard from '../MetricCard';

describe('MetricCard', () => {
  it('shows default period "Últimos 30 dias" when period prop not provided', () => {
    render(<MetricCard title="Test" value={42} />);
    expect(screen.getByText('Últimos 30 dias')).toBeInTheDocument();
  });

  it('shows custom period when period prop is provided', () => {
    render(<MetricCard title="Test" value={42} period="Últimos 7 dias" />);
    expect(screen.getByText('Últimos 7 dias')).toBeInTheDocument();
    expect(screen.queryByText('Últimos 30 dias')).not.toBeInTheDocument();
  });
});

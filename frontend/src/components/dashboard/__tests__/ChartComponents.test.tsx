import React from 'react';
import { render } from '@testing-library/react';
import { CampaignStatusChart, DeliveryRateChart, VolumeMetricsChart } from '../ChartComponents';

jest.mock('react-chartjs-2', () => ({
  Doughnut: () => <canvas data-testid="doughnut" />,
  Line: () => <canvas data-testid="line" />,
  Bar: () => <canvas data-testid="bar" />,
}));

describe('Chart accessibility', () => {
  it('CampaignStatusChart wrapper has role=img and aria-label', () => {
    const { container } = render(
      <CampaignStatusChart data={{ sent: 10, delivered: 8, read: 5, failed: 2 }} />
    );
    const wrapper = container.querySelector('[role="img"]');
    expect(wrapper).not.toBeNull();
    expect(wrapper?.getAttribute('aria-label')).toBeTruthy();
  });

  it('DeliveryRateChart wrapper has role=img and aria-label', () => {
    const { container } = render(
      <DeliveryRateChart data={{ labels: [], deliveryRate: [], readRate: [] }} />
    );
    const wrapper = container.querySelector('[role="img"]');
    expect(wrapper).not.toBeNull();
    expect(wrapper?.getAttribute('aria-label')).toBeTruthy();
  });

  it('VolumeMetricsChart wrapper has role=img and aria-label', () => {
    const { container } = render(
      <VolumeMetricsChart data={{ labels: [], sent: [], delivered: [] }} />
    );
    const wrapper = container.querySelector('[role="img"]');
    expect(wrapper).not.toBeNull();
    expect(wrapper?.getAttribute('aria-label')).toBeTruthy();
  });
});

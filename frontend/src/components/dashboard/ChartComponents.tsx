import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  ArcElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Bar, Line, Doughnut } from 'react-chartjs-2';
import Card from '../ui/Card';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  ArcElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// Chart color palette
const chartColors = {
  primary: '#3b82f6',
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  secondary: '#6b7280',
  accent: '#8b5cf6',
};

// Base chart options
const baseOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'bottom' as const,
      labels: {
        usePointStyle: true,
        padding: 20,
        font: {
          size: 12,
          family: 'Inter, system-ui, sans-serif',
        },
      },
    },
    tooltip: {
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      titleColor: '#fff',
      bodyColor: '#fff',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      borderWidth: 1,
      cornerRadius: 8,
      displayColors: true,
      usePointStyle: true,
    },
  },
};

// Campaign Status Donut Chart
export interface CampaignStatusChartProps {
  data: {
    sent: number;
    delivered: number;
    read: number;
    failed: number;
  };
  loading?: boolean;
}

export const CampaignStatusChart: React.FC<CampaignStatusChartProps> = ({
  data,
  loading = false,
}) => {
  const chartData = {
    labels: ['Enviadas', 'Entregues', 'Lidas', 'Falharam'],
    datasets: [
      {
        data: [data.sent, data.delivered, data.read, data.failed],
        backgroundColor: [
          chartColors.primary,
          chartColors.success,
          chartColors.warning,
          chartColors.error,
        ],
        borderWidth: 0,
        cutout: '60%',
      },
    ],
  };

  const options = {
    ...baseOptions,
    plugins: {
      ...baseOptions.plugins,
      legend: {
        ...baseOptions.plugins.legend,
        position: 'right' as const,
      },
    },
  };

  if (loading) {
    return (
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Status das Campanhas
          </h3>
          <div className="h-64 flex items-center justify-center">
            <div className="animate-pulse">
              <div className="w-32 h-32 bg-gray-200 rounded-full"></div>
            </div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Status das Campanhas
        </h3>
        <div className="h-64">
          <Doughnut data={chartData} options={options} />
        </div>
      </div>
    </Card>
  );
};

// Delivery Rate Line Chart
export interface DeliveryRateChartProps {
  data: {
    labels: string[];
    deliveryRate: number[];
    readRate: number[];
  };
  loading?: boolean;
}

export const DeliveryRateChart: React.FC<DeliveryRateChartProps> = ({
  data,
  loading = false,
}) => {
  const chartData = {
    labels: data.labels,
    datasets: [
      {
        label: 'Taxa de Entrega',
        data: data.deliveryRate,
        borderColor: chartColors.success,
        backgroundColor: `${chartColors.success}20`,
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointBackgroundColor: chartColors.success,
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 4,
      },
      {
        label: 'Taxa de Leitura',
        data: data.readRate,
        borderColor: chartColors.primary,
        backgroundColor: `${chartColors.primary}20`,
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointBackgroundColor: chartColors.primary,
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 4,
      },
    ],
  };

  const options = {
    ...baseOptions,
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        },
        ticks: {
          callback: function(value: any) {
            return value + '%';
          },
          font: {
            size: 11,
          },
        },
      },
      x: {
        grid: {
          display: false,
        },
        ticks: {
          font: {
            size: 11,
          },
        },
      },
    },
  };

  if (loading) {
    return (
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Taxa de Entrega e Leitura
          </h3>
          <div className="h-64 flex items-center justify-center">
            <div className="animate-pulse">
              <div className="w-full h-32 bg-gray-200 rounded"></div>
            </div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Taxa de Entrega e Leitura
        </h3>
        <div className="h-64">
          <Line data={chartData} options={options} />
        </div>
      </div>
    </Card>
  );
};

// Volume Metrics Bar Chart
export interface VolumeMetricsChartProps {
  data: {
    labels: string[];
    sent: number[];
    delivered: number[];
  };
  loading?: boolean;
}

export const VolumeMetricsChart: React.FC<VolumeMetricsChartProps> = ({
  data,
  loading = false,
}) => {
  const chartData = {
    labels: data.labels,
    datasets: [
      {
        label: 'Mensagens Enviadas',
        data: data.sent,
        backgroundColor: chartColors.primary,
        borderRadius: 4,
        borderSkipped: false,
      },
      {
        label: 'Mensagens Entregues',
        data: data.delivered,
        backgroundColor: chartColors.success,
        borderRadius: 4,
        borderSkipped: false,
      },
    ],
  };

  const options = {
    ...baseOptions,
    scales: {
      y: {
        beginAtZero: true,
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        },
        ticks: {
          font: {
            size: 11,
          },
        },
      },
      x: {
        grid: {
          display: false,
        },
        ticks: {
          font: {
            size: 11,
          },
        },
      },
    },
    elements: {
      bar: {
        borderRadius: 4,
      },
    },
  };

  if (loading) {
    return (
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Volume de Mensagens
          </h3>
          <div className="h-64 flex items-center justify-center">
            <div className="animate-pulse">
              <div className="w-full h-32 bg-gray-200 rounded"></div>
            </div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Volume de Mensagens
        </h3>
        <div className="h-64">
          <Bar data={chartData} options={options} />
        </div>
      </div>
    </Card>
  );
};

// Combined chart container for responsive layouts
export interface ChartContainerProps {
  children: React.ReactNode;
  title?: string;
  className?: string;
}

export const ChartContainer: React.FC<ChartContainerProps> = ({
  children,
  title,
  className = '',
}) => {
  return (
    <Card className={`${className}`}>
      {title && (
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        </div>
      )}
      <div className="p-6">
        {children}
      </div>
    </Card>
  );
};
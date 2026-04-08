import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Bar, Line } from 'react-chartjs-2';
import { CheckCircle2, RefreshCcw, Reply, Send, TrendingUp } from 'lucide-react';
import Card, { CardBody, CardHeader } from '../ui/Card';
import Button from '../ui/Button';
import { analyticsService } from '../../services/analytics-service';
import type { MessagingKpiResponse } from '../../types/analytics';

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Tooltip, Legend, Filler);

const chartColors = {
  sent: '#3b82f6',
  delivered: '#10b981',
  responses: '#8b5cf6',
};

const formatNumber = (value: number) => new Intl.NumberFormat('pt-BR').format(value);

const formatPercentage = (value: number) => `${value.toFixed(1)}%`;

const skeletonBlock = 'bg-gray-200 rounded animate-pulse';

const buildFallbackData = (): MessagingKpiResponse => ({
  totals: {
    sent: 0,
    delivered: 0,
    responses: 0,
    deliveryRate: 0,
    responseRate: 0,
  },
  timeline: {
    labels: [],
    sent: [],
    delivered: [],
    responses: [],
  },
  breakdown: [],
});

const MessagingKpiPanel: React.FC = () => {
  const [range, setRange] = useState<number>(30);

  const { data, isLoading, isError, error, isFetching, refetch } = useQuery({
    queryKey: ['messaging-kpis', range],
    queryFn: () => analyticsService.fetchKpis({ days: range }),
    staleTime: 60_000,
  });

  const payload = data ?? buildFallbackData();

  const lineChartData = useMemo(() => ({
    labels: payload.timeline.labels,
    datasets: [
      {
        label: 'Enviadas',
        data: payload.timeline.sent,
        borderColor: chartColors.sent,
        backgroundColor: `${chartColors.sent}25`,
        pointBackgroundColor: chartColors.sent,
        tension: 0.35,
        fill: true,
      },
      {
        label: 'Entregues',
        data: payload.timeline.delivered,
        borderColor: chartColors.delivered,
        backgroundColor: `${chartColors.delivered}25`,
        pointBackgroundColor: chartColors.delivered,
        tension: 0.35,
        fill: true,
      },
      {
        label: 'Respostas',
        data: payload.timeline.responses,
        borderColor: chartColors.responses,
        backgroundColor: `${chartColors.responses}20`,
        pointBackgroundColor: chartColors.responses,
        tension: 0.35,
        fill: true,
      },
    ],
  }), [payload.timeline]);

  const barChartData = useMemo(() => ({
    labels: payload.breakdown.map((item) => item.label),
    datasets: [
      {
        label: 'Enviadas',
        backgroundColor: chartColors.sent,
        data: payload.breakdown.map((item) => item.sent),
        stack: 'messages',
      },
      {
        label: 'Entregues',
        backgroundColor: chartColors.delivered,
        data: payload.breakdown.map((item) => item.delivered),
        stack: 'messages',
      },
      {
        label: 'Respostas',
        backgroundColor: chartColors.responses,
        data: payload.breakdown.map((item) => item.responses),
        stack: 'messages',
      },
    ],
  }), [payload.breakdown]);

  const lineChartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index' as const, intersect: false },
    plugins: {
      legend: { position: 'bottom' as const },
      tooltip: { mode: 'index' as const, intersect: false },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { stepSize: 10 },
        grid: { color: 'rgba(0,0,0,0.04)' },
      },
      x: {
        grid: { display: false },
      },
    },
  }), []);

  const barChartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom' as const },
      tooltip: { mode: 'index' as const, intersect: false },
    },
    scales: {
      x: {
        stacked: true,
        grid: { display: false },
      },
      y: {
        stacked: true,
        beginAtZero: true,
        grid: { color: 'rgba(0,0,0,0.04)' },
      },
    },
  }), []);

  const kpiCards = (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
      {[{
        label: 'Mensagens enviadas',
        value: payload.totals.sent,
        icon: <Send className="w-5 h-5 text-blue-600" />,
        testId: 'kpi-sent-card',
      }, {
        label: 'Mensagens entregues',
        value: payload.totals.delivered,
        icon: <CheckCircle2 className="w-5 h-5 text-emerald-600" />,
        testId: 'kpi-delivered-card',
      }, {
        label: 'Respostas recebidas',
        value: payload.totals.responses,
        icon: <Reply className="w-5 h-5 text-purple-600" />,
        testId: 'kpi-response-card',
      }, {
        label: 'Taxas de sucesso',
        value: payload.totals.responseRate,
        subtitle: `Entrega: ${formatPercentage(payload.totals.deliveryRate)}`,
        icon: <TrendingUp className="w-5 h-5 text-amber-600" />,
        format: formatPercentage,
        testId: 'kpi-rate-card',
      }].map((item) => (
        <Card key={item.label} className="h-full" data-testid={item.testId}>
          <CardBody className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm text-gray-500">{item.label}</p>
              <p className="text-2xl font-semibold text-gray-900" data-testid={`${item.testId}-value`}>
                {isLoading ? <span className={`${skeletonBlock} inline-block w-20 h-7`} /> :
                  item.format ? item.format(item.value) : formatNumber(item.value)}
              </p>
              {item.subtitle && (
                <p className="text-xs text-gray-500 mt-1">
                  {isLoading ? <span className={`${skeletonBlock} inline-block w-24 h-4`} /> : item.subtitle}
                </p>
              )}
            </div>
            <div className="p-3 rounded-full bg-gray-50 border border-gray-200">
              {item.icon}
            </div>
          </CardBody>
        </Card>
      ))}
    </div>
  );

  if (isError) {
    return (
      <Card className="border-red-200 bg-red-50" data-testid="kpi-error">
        <CardBody className="flex flex-col gap-3">
          <div className="flex items-center gap-2 text-red-700">
            <TrendingUp className="w-5 h-5" />
            <div>
              <p className="font-semibold">Não foi possível carregar os KPIs</p>
              <p className="text-sm text-red-600">{error instanceof Error ? error.message : 'Erro desconhecido'}</p>
            </div>
          </div>
          <Button onClick={() => refetch()} size="sm" variant="primary" className="self-start">
            Tentar novamente
          </Button>
        </CardBody>
      </Card>
    );
  }

  return (
    <div className="space-y-4" data-testid="messaging-kpi-panel">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">KPIs de Mensagens</h3>
          <p className="text-sm text-gray-500">Monitoramento de envios, entregas e respostas com atualização automática.</p>
        </div>
        <div className="flex items-center gap-2" data-testid="kpi-range-selector">
          {[7, 30, 90].map((days) => (
            <Button
              key={days}
              size="sm"
              variant={range === days ? 'primary' : 'ghost'}
              onClick={() => setRange(days)}
            >
              {days}d
            </Button>
          ))}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => refetch()}
            disabled={isFetching}
            icon={<RefreshCcw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />}
            aria-label="Atualizar KPIs"
          >
            Atualizar
          </Button>
        </div>
      </div>

      {kpiCards}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Card className="min-h-[320px]" data-testid="kpi-line-chart">
          <CardHeader border>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Tendência de mensagens</p>
                <p className="text-lg font-semibold text-gray-900">Linha do tempo</p>
              </div>
            </div>
          </CardHeader>
          <CardBody className="h-72">
            {isLoading ? (
              <div className="h-full flex items-center justify-center" data-testid="kpi-loading">
                <div className={`${skeletonBlock} w-3/4 h-40`} />
              </div>
            ) : lineChartData.labels.length > 0 ? (
              <Line data={lineChartData} options={lineChartOptions} />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500 text-sm">Sem dados para exibir</div>
            )}
          </CardBody>
        </Card>

        <Card className="min-h-[320px]" data-testid="kpi-bar-chart">
          <CardHeader border>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Comparativo por canal</p>
                <p className="text-lg font-semibold text-gray-900">Envios x Entregas x Respostas</p>
              </div>
            </div>
          </CardHeader>
          <CardBody className="h-72">
            {isLoading ? (
              <div className="h-full flex items-center justify-center">
                <div className={`${skeletonBlock} w-3/4 h-40`} />
              </div>
            ) : barChartData.labels.length > 0 ? (
              <Bar data={barChartData} options={barChartOptions} />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500 text-sm">Sem dados para exibir</div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
};

export default MessagingKpiPanel;

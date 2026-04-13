/**
 * Dashboard Component - WhatsApp Campaign Interface Improvements
 * GoHighLevel-style modern dashboard with comprehensive components
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { MessageSquare, TrendingUp, CheckCircle } from 'lucide-react';
import MetricCard from './MetricCard';
import { CampaignStatusChart, DeliveryRateChart, VolumeMetricsChart } from './ChartComponents';
import MessagingKpiPanel from './MessagingKpiPanel';
import { DashboardMetrics, DashboardParams } from '../../types/api';
import { API_BASE_URL } from '../../config/env';

interface DashboardProps {
  defaultUserId?: string; // Optional user ID for filtering
  onNavigateToCampaign?: () => void; // Callback para navegar para criação de campanha
  onNavigateToManagement?: () => void; // Callback para navegar para gerenciamento de campanhas
}

const computeChange = (current: number, previous: number): number =>
  previous > 0 ? ((current - previous) / previous) * 100 : 0;

function isDashboardMetrics(data: unknown): data is DashboardMetrics {
  if (typeof data !== 'object' || data === null) return false;
  const d = data as Record<string, unknown>;
  const cm = d.campaign_metrics;
  const dm = d.delivery_metrics;
  return (
    typeof cm === 'object' && cm !== null &&
    typeof (cm as Record<string, unknown>).total_campaigns === 'number' &&
    typeof (cm as Record<string, unknown>).active_campaigns === 'number' &&
    typeof dm === 'object' && dm !== null &&
    typeof (dm as Record<string, unknown>).sent === 'number' &&
    typeof (dm as Record<string, unknown>).delivery_rate === 'number' &&
    typeof (dm as Record<string, unknown>).read_rate === 'number'
  );
}

const Dashboard: React.FC<DashboardProps> = ({ defaultUserId, onNavigateToCampaign, onNavigateToManagement }) => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userFilter, setUserFilter] = useState<string>(defaultUserId || '');
  const [timeRange, setTimeRange] = useState<number>(30);
  const [fetchedAt, setFetchedAt] = useState<Date | null>(null);
  const [changes, setChanges] = useState<{
    activeCampaigns: number;
    sent: number;
    deliveryRate: number;
  } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Fetch dashboard data
  const fetchDashboardData = useCallback(async (params: DashboardParams = {}) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setFetchedAt(null);
    setChanges(null);
    setLoading(true);
    setError(null);

    try {
      const queryParams = new URLSearchParams();

      // Add optional user filter only if provided
      if (params.ghl_user_id) {
        queryParams.append('ghl_user_id', params.ghl_user_id);
      }

      // Add time range
      if (params.days) {
        queryParams.append('days', params.days.toString());
      }

      const prevDays = Math.min((params.days || 30) * 2, 365);
      const prevQueryParams = new URLSearchParams(queryParams);
      prevQueryParams.set('days', prevDays.toString());

      // Add timeout to prevent hanging
      const timeoutId = setTimeout(() => controller.abort(), 7000);

      const [response, prevResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/analytics/dashboard?${queryParams}`, { signal: controller.signal }),
        fetch(`${API_BASE_URL}/api/v1/analytics/dashboard?${prevQueryParams}`, { signal: controller.signal }),
      ]);

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Failed to fetch dashboard data: ${response.status} ${response.statusText}`);
      }

      const data: unknown = await response.json();

      if (!isDashboardMetrics(data)) {
        throw new Error('Resposta da API com formato inválido');
      }

      if (prevResponse.ok) {
        const prevData: unknown = await prevResponse.json();
        // previous period = 2×period total − current period
        if (isDashboardMetrics(prevData)) {
          const prevActiveCampaigns =
            (prevData.campaign_metrics.active_campaigns || 0) -
            (data.campaign_metrics.active_campaigns || 0);
          const prevSent =
            (prevData.delivery_metrics.sent || 0) - (data.delivery_metrics.sent || 0);
          const prevDeliveryRate = prevData.delivery_metrics.delivery_rate || 0;

          setChanges({
            activeCampaigns: computeChange(data.campaign_metrics.active_campaigns || 0, prevActiveCampaigns),
            sent: computeChange(data.delivery_metrics.sent || 0, prevSent),
            deliveryRate: computeChange(data.delivery_metrics.delivery_rate || 0, prevDeliveryRate),
          });
        }
      }

      // Set the metrics directly from the API response
      setMetrics(data);
      setFetchedAt(new Date());
    } catch (err) {
      // Show error state when API call fails
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  // Generate chart data from metrics (must be above early returns — Rules of Hooks)
  const chartData = useMemo(() => {
    if (!metrics) return null;
    return {
      campaignStatus: {
        sent: metrics.delivery_metrics.sent,
        delivered: metrics.delivery_metrics.delivered,  // direct field — ANA-11
        read: Math.floor(metrics.delivery_metrics.sent * (metrics.delivery_metrics.read_rate / 100)),
        failed: metrics.delivery_metrics.failed,  // direct field — ANA-11
      },
      deliveryRate: {
        labels: metrics.timeline?.labels ?? [],
        deliveryRate: metrics.timeline?.delivery_rate ?? [],
        readRate: metrics.timeline?.read_rate ?? [],
      },
      volume: {
        labels: metrics.timeline?.labels ?? [],
        sent: metrics.timeline?.sent ?? [],
        delivered: metrics.timeline?.delivered ?? [],
      },
    };
  }, [metrics]);

  // Load dashboard data on component mount
  useEffect(() => {
    fetchDashboardData({
      ghl_user_id: userFilter || undefined,
      days: timeRange,
    });
    return () => {
      abortRef.current?.abort();
    };
  }, [userFilter, timeRange, fetchDashboardData]);

  // Handle user filter change
  const handleUserFilterChange = (userId: string) => {
    setUserFilter(userId);
  };

  // Handle time range change
  const handleTimeRangeChange = (days: number) => {
    setTimeRange(days);
  };

  // Render loading state
  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-white rounded-lg shadow p-6">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-8 bg-gray-200 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="text-red-800 font-semibold">Error Loading Dashboard</h3>
          <p className="text-red-700 mt-1">{error}</p>
          <button
            onClick={() => fetchDashboardData({ ghl_user_id: userFilter || undefined, days: timeRange })}
            className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Guard: metrics not yet loaded
  if (!metrics) {
    return null;
  }

  // Empty state: metrics loaded but no campaigns exist
  if (metrics.campaign_metrics.total_campaigns === 0) {
    return (
      <div className="p-6">
        <div className="flex flex-col items-center justify-center min-h-[400px] bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
          <MessageSquare className="w-16 h-16 text-gray-400 mb-4" />
          <h3 className="text-xl font-semibold text-gray-700 mb-2">No campaigns yet</h3>
          <p className="text-gray-600 text-center max-w-md mb-6">
            Create your first campaign to see metrics and analytics here!
          </p>
          {onNavigateToCampaign && (
            <button
              onClick={onNavigateToCampaign}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Create First Campaign
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-6">
      <MessagingKpiPanel days={timeRange} onDaysChange={handleTimeRangeChange} />

      {fetchedAt && (
        <p
          className="text-xs text-gray-400 text-right"
          data-testid="fetched-at"
        >
          Dados de {fetchedAt.toLocaleTimeString('pt-BR')}
        </p>
      )}

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <MetricCard
          title="Campanhas Ativas"
          value={metrics.campaign_metrics.active_campaigns}
          change={changes ? Math.abs(changes.activeCampaigns) : undefined}
          changeType={
            changes
              ? changes.activeCampaigns >= 0 ? 'increase' : 'decrease'
              : 'neutral'
          }
          format="number"
          icon={<MessageSquare />}
          loading={loading}
          period={`Últimos ${timeRange} dias`}
        />
        <MetricCard
          title="Mensagens Enviadas"
          value={metrics.delivery_metrics.sent}
          change={changes ? Math.abs(changes.sent) : undefined}
          changeType={
            changes
              ? changes.sent >= 0 ? 'increase' : 'decrease'
              : 'neutral'
          }
          format="number"
          icon={<TrendingUp />}
          loading={loading}
          period={`Últimos ${timeRange} dias`}
        />
        <MetricCard
          title="Taxa de Entrega"
          value={metrics.delivery_metrics.delivery_rate}
          change={changes ? Math.abs(changes.deliveryRate) : undefined}
          changeType={
            changes
              ? changes.deliveryRate >= 0 ? 'increase' : 'decrease'
              : 'neutral'
          }
          format="percentage"
          icon={<CheckCircle />}
          loading={loading}
          period={`Últimos ${timeRange} dias`}
        />
      </div>

      {/* Charts Section - Full Width */}
      <div className="space-y-6">
        {/* Top Row Charts */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <CampaignStatusChart
            data={chartData!.campaignStatus}
            loading={loading}
          />
          <DeliveryRateChart
            data={chartData!.deliveryRate}
            loading={loading}
          />
        </div>

        {/* Volume Chart - Full Width */}
        <VolumeMetricsChart
          data={chartData!.volume}
          loading={loading}
        />
      </div>
    </div>
  );
};

export default Dashboard;

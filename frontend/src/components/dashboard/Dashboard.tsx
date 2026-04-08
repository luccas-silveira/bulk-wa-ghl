/**
 * Dashboard Component - WhatsApp Campaign Interface Improvements
 * GoHighLevel-style modern dashboard with comprehensive components
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
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

const Dashboard: React.FC<DashboardProps> = ({ defaultUserId, onNavigateToCampaign, onNavigateToManagement }) => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userFilter, setUserFilter] = useState<string>(defaultUserId || '');
  const [timeRange, setTimeRange] = useState<number>(30);

  // Fetch dashboard data
  const fetchDashboardData = useCallback(async (params: DashboardParams = {}) => {
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

      // Add timeout to prevent hanging
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);

      const response = await fetch(`${API_BASE_URL}/api/v1/analytics/dashboard?${queryParams}`, {
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Failed to fetch dashboard data: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();

      // Set the metrics directly from the API response
      setMetrics(data);
    } catch (err) {
      // Show error state when API call fails
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load dashboard data on component mount
  useEffect(() => {
    fetchDashboardData({
      ghl_user_id: userFilter || undefined,
      days: timeRange,
    });
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
          <p className="text-red-600 mt-1">{error}</p>
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

  // Render empty state (no campaigns)
  if (metrics && metrics.campaign_metrics.total_campaigns === 0) {
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

  // Generate chart data from metrics
  const chartData = useMemo(() => ({
    campaignStatus: {
      sent: metrics?.delivery_metrics.sent || 0,
      delivered: Math.floor((metrics?.delivery_metrics.sent || 0) * (metrics?.delivery_metrics.delivery_rate || 0) / 100),
      read: Math.floor((metrics?.delivery_metrics.sent || 0) * (metrics?.delivery_metrics.read_rate || 0) / 100),
      failed: Math.floor((metrics?.delivery_metrics.sent || 0) * (1 - (metrics?.delivery_metrics.delivery_rate || 0) / 100))
    },
    deliveryRate: {
      labels: ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'],
      deliveryRate: [95, 92, 97, 89, 94, 91, 96],
      readRate: [78, 82, 85, 79, 83, 77, 81]
    },
    volume: {
      labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
      sent: [1200, 1900, 3000, 5000, 4200, 3800],
      delivered: [1140, 1805, 2850, 4750, 3990, 3610]
    }
  }), [metrics]);

  return (
    <div className="w-full space-y-6">
      <MessagingKpiPanel />

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <MetricCard
          title="Campanhas Ativas"
          value={metrics?.campaign_metrics.active_campaigns || 0}
          previousValue={(metrics?.campaign_metrics.active_campaigns || 0) - 2}
          change={15.2}
          changeType="increase"
          format="number"
          icon={<MessageSquare />}
          loading={loading}
        />
        <MetricCard
          title="Mensagens Enviadas"
          value={metrics?.delivery_metrics.sent || 0}
          previousValue={(metrics?.delivery_metrics.sent || 0) - 1200}
          change={8.7}
          changeType="increase"
          format="number"
          icon={<TrendingUp />}
          loading={loading}
        />
        <MetricCard
          title="Taxa de Entrega"
          value={metrics?.delivery_metrics.delivery_rate || 0}
          previousValue={(metrics?.delivery_metrics.delivery_rate || 0) - 2.1}
          change={2.4}
          changeType="increase"
          format="percentage"
          icon={<CheckCircle />}
          loading={loading}
        />
      </div>

      {/* Charts Section - Full Width */}
      <div className="space-y-6">
        {/* Top Row Charts */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <CampaignStatusChart
            data={chartData.campaignStatus}
            loading={loading}
          />
          <DeliveryRateChart
            data={chartData.deliveryRate}
            loading={loading}
          />
        </div>

        {/* Volume Chart - Full Width */}
        <VolumeMetricsChart
          data={chartData.volume}
          loading={loading}
        />
      </div>
    </div>
  );
};

export default Dashboard;

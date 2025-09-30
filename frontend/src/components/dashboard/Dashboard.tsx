/**
 * Dashboard Component - WhatsApp Campaign Interface Improvements
 * GoHighLevel-style modern dashboard with comprehensive components
 */

import React, { useState, useEffect } from 'react';
import { MessageSquare, Users, TrendingUp, CheckCircle } from 'lucide-react';
import MetricCard from './MetricCard';
import { CampaignStatusChart, DeliveryRateChart, VolumeMetricsChart } from './ChartComponents';
import ActivityFeed, { ActivityItem } from './ActivityFeed';
import QuickActions from './QuickActions';
import { DashboardMetrics, DashboardParams } from '../../types/api';

interface DashboardProps {
  defaultUserId?: string; // Optional user ID for filtering
}

const Dashboard: React.FC<DashboardProps> = ({ defaultUserId }) => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userFilter, setUserFilter] = useState<string>(defaultUserId || '');
  const [timeRange, setTimeRange] = useState<number>(30);
  const [activities, setActivities] = useState<ActivityItem[]>([]);

  // Handle navigation for quick actions
  const handleNavigate = (route: string) => {
    // This would typically use React Router or similar
    // For now, we'll emit a custom event that the parent can handle
    window.dispatchEvent(new CustomEvent('navigate', { detail: { route } }));
  };

  // Fetch dashboard data
  const fetchDashboardData = async (params: DashboardParams = {}) => {
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

      const response = await fetch(`http://localhost:8000/api/v1/analytics/dashboard?${queryParams}`);

      if (!response.ok) {
        throw new Error('Failed to fetch dashboard data');
      }

      const data = await response.json();

      // Transform to expected format - data is already in the correct format from simplified backend
      const transformedMetrics: DashboardMetrics = {
        campaign_metrics: data.campaign_metrics || {
          total_campaigns: 0,
          active_campaigns: 0,
          completed_campaigns: 0,
          failed_campaigns: 0,
        },
        delivery_metrics: data.delivery_metrics || {
          sent: 0,
          delivery_rate: 0,
          read_rate: 0,
        },
        recent_campaigns: data.recent_campaigns || [],
        top_performing_campaigns: data.top_performing_campaigns || [],
      };

      setMetrics(transformedMetrics);

      // Generate mock activity data based on campaigns
      const mockActivities: ActivityItem[] = [
        {
          id: '1',
          type: 'campaign_created',
          title: 'Nova campanha criada',
          description: 'Campanha "Promoção Black Friday" foi configurada',
          timestamp: new Date(Date.now() - 2 * 60 * 1000),
          user: { name: 'João Silva', initials: 'JS' },
          metadata: { campaignName: 'Promoção Black Friday' }
        },
        {
          id: '2',
          type: 'session_connected',
          title: 'Sessão WAHA conectada',
          description: 'WhatsApp Principal está agora online',
          timestamp: new Date(Date.now() - 5 * 60 * 1000),
          metadata: { sessionName: 'WhatsApp Principal' }
        },
        {
          id: '3',
          type: 'campaign_sent',
          title: 'Campanha enviada',
          description: 'Mensagens enviadas para 150 contatos',
          timestamp: new Date(Date.now() - 30 * 60 * 1000),
          user: { name: 'Maria Santos', initials: 'MS' },
          metadata: { campaignName: 'Newsletter Semanal', count: 150 }
        },
        {
          id: '4',
          type: 'campaign_delivered',
          title: 'Alta taxa de entrega',
          description: '98% das mensagens foram entregues',
          timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
          metadata: { campaignName: 'Newsletter Semanal' }
        }
      ];

      setActivities(mockActivities);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Load dashboard data on component mount
  useEffect(() => {
    fetchDashboardData({
      ghl_user_id: userFilter || undefined,
      days: timeRange,
    });
  }, [userFilter, timeRange]);

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

  // Generate chart data from metrics
  const chartData = {
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
  };

  return (
    <div className="space-y-6">
      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
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
        <MetricCard
          title="Contatos Ativos"
          value={5847}
          previousValue={5392}
          change={8.4}
          changeType="increase"
          format="number"
          icon={<Users />}
          loading={loading}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Charts Section - Takes 2 columns */}
        <div className="lg:col-span-2 space-y-6">
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

        {/* Sidebar - Takes 1 column */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <QuickActions onNavigate={handleNavigate} />

          {/* Activity Feed */}
          <ActivityFeed
            activities={activities}
            loading={loading}
            showLoadMore={activities.length > 0}
            onLoadMore={() => console.log('Load more activities')}
          />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
/**
 * CampaignList Component
 * Displays a list of campaigns with filtering, pagination, and actions
 */
import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Filter, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Input from '../ui/Input';
import CampaignStatusBadge from './CampaignStatusBadge';
import CampaignActions from './CampaignActions';
import { campaignService } from '../../services/campaign-service';
import type { CampaignFilters, CampaignStatus } from '../../types/campaign';

export interface CampaignListProps {
  defaultFilters?: CampaignFilters;
  onCampaignClick?: (campaignId: number) => void;
}

const CampaignList: React.FC<CampaignListProps> = ({
  defaultFilters,
  onCampaignClick,
}) => {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<CampaignFilters>(defaultFilters || {});
  const [debouncedFilters, setDebouncedFilters] = useState<CampaignFilters>(filters);
  const [page, setPage] = useState(0);
  const [limit, setLimit] = useState(20);

  // Debounce filters (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedFilters(filters);
      setPage(0); // Reset to first page on filter change
    }, 300);

    return () => clearTimeout(timer);
  }, [filters]);

  // Fetch campaigns
  const { data, isLoading, error } = useQuery({
    queryKey: ['campaigns', debouncedFilters, limit, page],
    queryFn: () => campaignService.listCampaigns(debouncedFilters, limit, page * limit),
    retry: 2,
    staleTime: 30000,
  });

  // Pause mutation
  const pauseMutation = useMutation({
    mutationFn: (campaignId: number) => campaignService.pauseCampaign(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  // Resume mutation
  const resumeMutation = useMutation({
    mutationFn: (campaignId: number) => campaignService.resumeCampaign(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (campaignId: number) => campaignService.deleteCampaign(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const handleStatusFilter = (status: string) => {
    setFilters(prev => ({ ...prev, status: status as CampaignStatus }));
  };

  const handleSearch = (value: string) => {
    // For now, we'll use ghl_user_id for search (can be extended)
    setFilters(prev => ({ ...prev, ghl_user_id: value || undefined }));
  };

  const totalPages = data ? Math.ceil(data.count / limit) : 0;

  // Loading skeleton
  if (isLoading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
          <span className="ml-2 text-gray-600">Carregando campanhas...</span>
        </div>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card>
        <div className="text-center py-12">
          <div className="text-error-600 font-medium mb-2">Erro ao carregar campanhas</div>
          <div className="text-gray-600 text-sm">{error.message}</div>
        </div>
      </Card>
    );
  }

  // Empty state
  if (!data || data.campaigns.length === 0) {
    return (
      <Card>
        <div className="text-center py-12">
          <div className="text-gray-400 text-lg font-medium mb-2">Nenhuma campanha encontrada</div>
          <div className="text-gray-600 text-sm">
            {Object.keys(debouncedFilters).length > 0
              ? 'Tente ajustar os filtros'
              : 'Crie sua primeira campanha para começar'}
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card>
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <Input
              placeholder="Buscar por usuário..."
              leftIcon={<Search className="h-4 w-4" />}
              onChange={(e) => handleSearch(e.target.value)}
              value={filters.ghl_user_id || ''}
            />
          </div>

          {/* Status filter */}
          <div className="flex gap-2 flex-wrap">
            <Button
              variant={!filters.status ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => setFilters(prev => ({ ...prev, status: undefined }))}
            >
              Todos
            </Button>
            <Button
              variant={filters.status === 'executing' ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => handleStatusFilter('executing')}
            >
              Em execução
            </Button>
            <Button
              variant={filters.status === 'paused' ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => handleStatusFilter('paused')}
            >
              Pausados
            </Button>
            <Button
              variant={filters.status === 'completed' ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => handleStatusFilter('completed')}
            >
              Concluídos
            </Button>
          </div>
        </div>
      </Card>

      {/* Campaign list */}
      <Card padding="none">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Campanha
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Criado em
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Mensagens
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Taxa de entrega
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.campaigns.map((campaign) => {
                const deliveryRate =
                  campaign.message_stats.total > 0
                    ? ((campaign.message_stats.delivered / campaign.message_stats.total) * 100).toFixed(1)
                    : '0.0';

                return (
                  <tr
                    key={campaign.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => onCampaignClick?.(campaign.id)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{campaign.name}</div>
                      {campaign.ghl_location_name && (
                        <div className="text-sm text-gray-500">{campaign.ghl_location_name}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <CampaignStatusBadge status={campaign.status} showDot />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(campaign.created_at).toLocaleDateString('pt-BR')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {campaign.message_stats.sent} / {campaign.message_stats.total}
                      </div>
                      <div className="text-xs text-gray-500">
                        {campaign.message_stats.failed > 0 && (
                          <span className="text-error-600">{campaign.message_stats.failed} falhas</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="text-sm text-gray-900">{deliveryRate}%</div>
                        {campaign.progress_percent !== undefined && (
                          <div className="ml-2 text-xs text-gray-500">({campaign.progress_percent.toFixed(0)}% concluído)</div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium" onClick={(e) => e.stopPropagation()}>
                      <CampaignActions
                        campaign={campaign}
                        onPause={async (id) => await pauseMutation.mutateAsync(id)}
                        onResume={async (id) => await resumeMutation.mutateAsync(id)}
                        onDelete={async (id) => await deleteMutation.mutateAsync(id)}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-700">
              Mostrando {page * limit + 1} até {Math.min((page + 1) * limit, data.count)} de {data.count} campanhas
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              icon={<ChevronLeft />}
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              aria-label="Previous page"
            >
              Anterior
            </Button>

            <div className="flex gap-1">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const pageNum = page < 3 ? i : page - 2 + i;
                if (pageNum >= totalPages) return null;

                return (
                  <Button
                    key={pageNum}
                    variant={page === pageNum ? 'primary' : 'ghost'}
                    size="sm"
                    onClick={() => setPage(pageNum)}
                  >
                    {pageNum + 1}
                  </Button>
                );
              })}
            </div>

            <Button
              variant="secondary"
              size="sm"
              icon={<ChevronRight />}
              iconPosition="right"
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              aria-label="Next page"
            >
              Próxima
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default CampaignList;

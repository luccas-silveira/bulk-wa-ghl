/**
 * CampaignDetails Component
 * Displays detailed campaign information with statistics, timeline, and recent messages
 */
import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Loader2,
  X,
  TrendingUp,
  MessageSquare,
  CheckCircle,
  AlertCircle,
  Clock,
} from 'lucide-react';
import Card, { CardHeader, CardBody } from '../ui/Card';
import Button from '../ui/Button';
import CampaignStatusBadge from './CampaignStatusBadge';
import CampaignActions from './CampaignActions';
import { campaignService } from '../../services/campaign-service';

export interface CampaignDetailsProps {
  campaignId: number;
  onClose?: () => void;
}

const CampaignDetails: React.FC<CampaignDetailsProps> = ({ campaignId, onClose }) => {
  const queryClient = useQueryClient();

  // Fetch campaign details
  const { data, isLoading, error } = useQuery({
    queryKey: ['campaign', campaignId],
    queryFn: () => campaignService.getCampaignDetails(campaignId),
  });

  // Pause mutation
  const pauseMutation = useMutation({
    mutationFn: () => campaignService.pauseCampaign(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', campaignId], exact: true });
      queryClient.invalidateQueries({ queryKey: ['campaigns'], exact: false });
    },
  });

  // Resume mutation
  const resumeMutation = useMutation({
    mutationFn: () => campaignService.resumeCampaign(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', campaignId], exact: true });
      queryClient.invalidateQueries({ queryKey: ['campaigns'], exact: false });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => campaignService.deleteCampaign(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'], exact: false });
      onClose?.();
    },
  });

  // Loading state
  if (isLoading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
          <span className="ml-2 text-gray-600">Carregando detalhes...</span>
        </div>
      </Card>
    );
  }

  // Error state
  if (error || !data) {
    return (
      <Card>
        <div className="text-center py-12">
          <div className="text-error-600 font-medium mb-2">Erro ao carregar campanha</div>
          <div className="text-gray-600 text-sm">{error?.message || 'Campanha não encontrada'}</div>
          {onClose && (
            <Button variant="secondary" size="sm" onClick={onClose} className="mt-4">
              Fechar
            </Button>
          )}
        </div>
      </Card>
    );
  }

  const { campaign, statistics, timeline, recent_messages } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-2xl font-bold text-gray-900">{campaign.name}</h2>
              <CampaignStatusBadge status={campaign.status} showDot />
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-600">
              <span>Criado em {new Date(campaign.created_at).toLocaleDateString('pt-BR')}</span>
              {campaign.ghl_location_name && <span>• {campaign.ghl_location_name}</span>}
              {campaign.ghl_user_name && <span>• {campaign.ghl_user_name}</span>}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <CampaignActions
              campaign={campaign}
              onPause={async () => await pauseMutation.mutateAsync()}
              onResume={async () => await resumeMutation.mutateAsync()}
              onDelete={async () => await deleteMutation.mutateAsync()}
            />
            {onClose && (
              <Button variant="ghost" size="sm" icon={<X />} onClick={onClose} aria-label="Close campaign details" />
            )}
          </div>
        </div>
      </Card>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-100 rounded-lg">
              <MessageSquare className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <div className="text-sm text-gray-600">Total de Mensagens</div>
              <div className="text-2xl font-bold text-gray-900">{statistics.total_messages}</div>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-success-100 rounded-lg">
              <CheckCircle className="h-6 w-6 text-success-600" />
            </div>
            <div>
              <div className="text-sm text-gray-600">Entregues</div>
              <div className="text-2xl font-bold text-gray-900">{statistics.delivered}</div>
              <div className="text-xs text-gray-500">{statistics.delivery_rate.toFixed(1)}% taxa</div>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-primary-100 rounded-lg">
              <TrendingUp className="h-6 w-6 text-primary-600" />
            </div>
            <div>
              <div className="text-sm text-gray-600">Lidas</div>
              <div className="text-2xl font-bold text-gray-900">{statistics.read}</div>
              <div className="text-xs text-gray-500">{statistics.read_rate.toFixed(1)}% taxa</div>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-error-100 rounded-lg">
              <AlertCircle className="h-6 w-6 text-error-600" />
            </div>
            <div>
              <div className="text-sm text-gray-600">Falhas</div>
              <div className="text-2xl font-bold text-gray-900">{statistics.failed}</div>
              {statistics.pending > 0 && (
                <div className="text-xs text-gray-500">{statistics.pending} pendentes</div>
              )}
            </div>
          </div>
        </Card>
      </div>

      {/* Progress Bar (for executing/paused campaigns) */}
      {(campaign.status === 'executing' || campaign.status === 'paused') && statistics.total_messages > 0 && (
        <Card>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Progresso da Campanha</span>
            <span className="text-sm text-gray-600">
              {((statistics.sent / statistics.total_messages) * 100).toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-primary-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(statistics.sent / statistics.total_messages) * 100}%` }}
            />
          </div>
          <div className="mt-2 text-xs text-gray-600">
            {statistics.sent} de {statistics.total_messages} mensagens enviadas
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Timeline */}
        <Card>
          <CardHeader border>
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-gray-600" />
              <h3 className="text-lg font-semibold text-gray-900">Linha do Tempo</h3>
            </div>
          </CardHeader>
          <CardBody>
            {timeline.length === 0 ? (
              <div className="text-center py-8 text-gray-500 text-sm">
                Nenhum evento registrado
              </div>
            ) : (
              <div className="space-y-4">
                {timeline.map((event, index) => (
                  <div key={index} className="flex gap-3">
                    <div className="flex-shrink-0 w-2 h-2 mt-2 bg-primary-500 rounded-full" />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-gray-900">{event.event}</div>
                      <div className="text-xs text-gray-500">
                        {new Date(event.timestamp).toLocaleString('pt-BR')}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>

        {/* Recent Messages */}
        <Card>
          <CardHeader border>
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-gray-600" />
              <h3 className="text-lg font-semibold text-gray-900">Mensagens Recentes</h3>
            </div>
          </CardHeader>
          <CardBody padding="none">
            {recent_messages.length === 0 ? (
              <div className="text-center py-8 text-gray-500 text-sm">
                Nenhuma mensagem ainda
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {recent_messages.slice(0, 10).map((message) => (
                  <div key={message.id} className="px-6 py-3 hover:bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {message.recipient_phone}
                        </div>
                        <div className="text-xs text-gray-500">
                          {message.sent_at
                            ? new Date(message.sent_at).toLocaleString('pt-BR')
                            : 'Não enviada'}
                        </div>
                      </div>
                      <div className="ml-4">
                        <CampaignStatusBadge
                          status={message.status as any}
                          showDot
                        />
                      </div>
                    </div>
                    {message.error_message && (
                      <div className="mt-1 text-xs text-error-600">{message.error_message}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
};

export default CampaignDetails;

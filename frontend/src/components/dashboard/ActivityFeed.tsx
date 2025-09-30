import React, { useState } from 'react';
import { MessageSquare, CheckCircle, XCircle, Clock, User, MoreHorizontal } from 'lucide-react';
import Card from '../ui/Card';
import Avatar from '../ui/Avatar';
import Badge from '../ui/Badge';
import Button from '../ui/Button';

export interface ActivityItem {
  id: string;
  type: 'campaign_created' | 'campaign_sent' | 'campaign_delivered' | 'campaign_failed' | 'session_connected' | 'session_disconnected';
  title: string;
  description: string;
  timestamp: Date;
  user?: {
    name: string;
    avatar?: string;
    initials?: string;
  };
  metadata?: {
    campaignName?: string;
    sessionName?: string;
    count?: number;
    status?: string;
  };
}

export interface ActivityFeedProps {
  activities: ActivityItem[];
  loading?: boolean;
  showLoadMore?: boolean;
  onLoadMore?: () => void;
  className?: string;
}

const ActivityFeed: React.FC<ActivityFeedProps> = ({
  activities,
  loading = false,
  showLoadMore = false,
  onLoadMore,
  className,
}) => {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedItems(newExpanded);
  };

  const getActivityIcon = (type: ActivityItem['type']) => {
    switch (type) {
      case 'campaign_created':
        return <MessageSquare className="w-4 h-4 text-primary-600" />;
      case 'campaign_sent':
        return <CheckCircle className="w-4 h-4 text-success-600" />;
      case 'campaign_delivered':
        return <CheckCircle className="w-4 h-4 text-success-600" />;
      case 'campaign_failed':
        return <XCircle className="w-4 h-4 text-error-600" />;
      case 'session_connected':
        return <CheckCircle className="w-4 h-4 text-success-600" />;
      case 'session_disconnected':
        return <XCircle className="w-4 h-4 text-error-600" />;
      default:
        return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  const getActivityBadge = (type: ActivityItem['type']) => {
    switch (type) {
      case 'campaign_created':
        return <Badge variant="primary" size="sm">Nova Campanha</Badge>;
      case 'campaign_sent':
        return <Badge variant="success" size="sm">Enviada</Badge>;
      case 'campaign_delivered':
        return <Badge variant="success" size="sm">Entregue</Badge>;
      case 'campaign_failed':
        return <Badge variant="error" size="sm">Falhou</Badge>;
      case 'session_connected':
        return <Badge variant="success" size="sm">Conectado</Badge>;
      case 'session_disconnected':
        return <Badge variant="error" size="sm">Desconectado</Badge>;
      default:
        return <Badge variant="secondary" size="sm">Atividade</Badge>;
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Agora mesmo';
    if (minutes < 60) return `${minutes}m atrás`;
    if (hours < 24) return `${hours}h atrás`;
    if (days < 7) return `${days}d atrás`;

    return timestamp.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  };

  if (loading) {
    return (
      <Card className={className}>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Atividades Recentes
          </h3>
          <div className="space-y-4">
            {[...Array(5)].map((_, index) => (
              <div key={index} className="animate-pulse">
                <div className="flex items-start space-x-3">
                  <div className="w-8 h-8 bg-gray-200 rounded-full"></div>
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/4"></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">
            Atividades Recentes
          </h3>
          <Button variant="ghost" size="sm">
            <MoreHorizontal className="w-4 h-4" />
          </Button>
        </div>

        <div className="space-y-4">
          {activities.length === 0 ? (
            <div className="text-center py-8">
              <Clock className="w-8 h-8 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-500">
                Nenhuma atividade recente
              </p>
            </div>
          ) : (
            activities.map((activity) => (
              <div
                key={activity.id}
                className="flex items-start space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors duration-150"
              >
                {/* Activity Icon */}
                <div className="flex-shrink-0 w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                  {getActivityIcon(activity.type)}
                </div>

                {/* Activity Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="text-sm font-medium text-gray-900 truncate">
                      {activity.title}
                    </h4>
                    {getActivityBadge(activity.type)}
                  </div>

                  <p className="text-sm text-gray-600 mb-2">
                    {activity.description}
                  </p>

                  {/* Metadata */}
                  {activity.metadata && (
                    <div className="flex items-center space-x-4 text-xs text-gray-500 mb-2">
                      {activity.metadata.campaignName && (
                        <span>Campanha: {activity.metadata.campaignName}</span>
                      )}
                      {activity.metadata.sessionName && (
                        <span>Sessão: {activity.metadata.sessionName}</span>
                      )}
                      {activity.metadata.count && (
                        <span>{activity.metadata.count} mensagens</span>
                      )}
                    </div>
                  )}

                  {/* User and Timestamp */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {activity.user ? (
                        <>
                          <Avatar
                            size="xs"
                            src={activity.user.avatar}
                            fallback={activity.user.initials || activity.user.name.charAt(0)}
                          />
                          <span className="text-xs text-gray-500">
                            {activity.user.name}
                          </span>
                        </>
                      ) : (
                        <div className="flex items-center space-x-1">
                          <User className="w-3 h-3 text-gray-400" />
                          <span className="text-xs text-gray-500">Sistema</span>
                        </div>
                      )}
                    </div>
                    <span className="text-xs text-gray-500">
                      {formatTimestamp(activity.timestamp)}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Load More Button */}
        {showLoadMore && (
          <div className="mt-6 text-center">
            <Button
              variant="ghost"
              size="sm"
              onClick={onLoadMore}
              className="text-primary-600 hover:text-primary-700"
            >
              Carregar mais atividades
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
};

export default ActivityFeed;
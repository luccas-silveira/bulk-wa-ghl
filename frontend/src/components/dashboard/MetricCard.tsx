import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import Card from '../ui/Card';

export interface MetricCardProps {
  title: string;
  value: string | number;
  previousValue?: string | number;
  change?: number;
  changeType?: 'increase' | 'decrease' | 'neutral';
  format?: 'number' | 'percentage' | 'currency';
  icon?: React.ReactNode;
  loading?: boolean;
  className?: string;
  period?: string;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  previousValue,
  change,
  changeType,
  format = 'number',
  icon,
  loading = false,
  className,
  period,
}) => {
  const formatValue = (val: string | number): string => {
    if (typeof val === 'string') return val;

    switch (format) {
      case 'percentage':
        return `${val.toFixed(1)}%`;
      case 'currency':
        return new Intl.NumberFormat('pt-BR', {
          style: 'currency',
          currency: 'BRL',
        }).format(val);
      case 'number':
      default:
        return new Intl.NumberFormat('pt-BR').format(val);
    }
  };

  const getTrendIcon = () => {
    if (!change || changeType === 'neutral') {
      return <Minus className="w-4 h-4" />;
    }
    return changeType === 'increase' ? (
      <TrendingUp className="w-4 h-4" />
    ) : (
      <TrendingDown className="w-4 h-4" />
    );
  };

  const getTrendColor = () => {
    if (!change || changeType === 'neutral') return 'text-gray-500';
    return changeType === 'increase' ? 'text-success-600' : 'text-error-600';
  };

  const getChangeText = () => {
    if (!change) return null;
    const absChange = Math.abs(change);
    return `${changeType === 'increase' ? '+' : '-'}${absChange.toFixed(1)}%`;
  };

  if (loading) {
    return (
      <Card className={className}>
        <div className="p-6">
          <div className="animate-pulse">
            <div className="flex items-center justify-between mb-4">
              <div className="h-4 bg-gray-200 rounded w-24"></div>
              <div className="h-6 w-6 bg-gray-200 rounded"></div>
            </div>
            <div className="h-8 bg-gray-200 rounded w-32 mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-20"></div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className={`hover:shadow-md transition-shadow duration-200 ${className}`}>
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-gray-600 truncate">{title}</h3>
          {icon && (
            <div className="flex-shrink-0 p-2 bg-primary-50 rounded-lg">
              {React.cloneElement(icon as React.ReactElement, {
                className: 'w-5 h-5 text-primary-600'
              })}
            </div>
          )}
        </div>

        {/* Main Value */}
        <div className="mb-3">
          <div className="text-2xl font-bold text-gray-900">
            {formatValue(value)}
          </div>
        </div>

        {/* Trend and Change */}
        {(change !== undefined || previousValue !== undefined) && (
          <div className="flex items-center space-x-2">
            {change !== undefined && (
              <div className={`flex items-center space-x-1 ${getTrendColor()}`}>
                {getTrendIcon()}
                <span className="text-sm font-medium">
                  {getChangeText()}
                </span>
              </div>
            )}

            {previousValue !== undefined && (
              <div className="text-sm text-gray-500">
                vs {formatValue(previousValue)}
              </div>
            )}
          </div>
        )}

        {/* Period indicator */}
        <div className="mt-2 text-xs text-gray-400">
          {period ?? 'Últimos 30 dias'}
        </div>
      </div>
    </Card>
  );
};

export default MetricCard;
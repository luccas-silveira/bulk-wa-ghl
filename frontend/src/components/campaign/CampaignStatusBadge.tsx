import React from 'react';
import Badge from '../ui/Badge';
import { CampaignStatus } from '../../types/campaign';

export interface CampaignStatusBadgeProps {
  status: CampaignStatus;
  className?: string;
  showDot?: boolean;
}

const CampaignStatusBadge: React.FC<CampaignStatusBadgeProps> = ({
  status,
  className,
  showDot = false,
}) => {
  // Map campaign status to badge variant and label
  const statusConfig: Record<CampaignStatus, { variant: 'success' | 'warning' | 'error' | 'info' | 'gray' | 'primary'; label: string }> = {
    draft: { variant: 'gray', label: 'Draft' },
    scheduled: { variant: 'info', label: 'Scheduled' },
    executing: { variant: 'warning', label: 'Executing' },
    paused: { variant: 'warning', label: 'Paused' },
    completed: { variant: 'success', label: 'Completed' },
    failed: { variant: 'error', label: 'Failed' },
    cancelled: { variant: 'gray', label: 'Cancelled' },
  };

  const config = statusConfig[status] || { variant: 'gray' as const, label: status };

  return (
    <Badge
      variant={config.variant}
      className={className}
      dot={showDot}
    >
      {config.label}
    </Badge>
  );
};

export default CampaignStatusBadge;

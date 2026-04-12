/**
 * MessageStatusBadge
 * Renders a colored badge for individual message delivery statuses:
 * pending | sent | delivered | read | failed
 */
import React from 'react';
import type { MessageStatus } from '../../types/campaign';

const STATUS_CONFIG: Record<MessageStatus, { label: string; classes: string }> = {
  pending:   { label: 'Pendente',   classes: 'bg-gray-100 text-gray-700' },
  sent:      { label: 'Enviado',    classes: 'bg-blue-100 text-blue-700' },
  delivered: { label: 'Entregue',   classes: 'bg-green-100 text-green-700' },
  read:      { label: 'Lido',       classes: 'bg-purple-100 text-purple-700' },
  failed:    { label: 'Falhou',     classes: 'bg-red-100 text-red-700' },
};

interface MessageStatusBadgeProps {
  status: MessageStatus;
}

const MessageStatusBadge: React.FC<MessageStatusBadgeProps> = ({ status }) => {
  const config = STATUS_CONFIG[status] ?? {
    label: status,
    classes: 'bg-gray-100 text-gray-500',
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${config.classes}`}
    >
      {config.label}
    </span>
  );
};

export default MessageStatusBadge;

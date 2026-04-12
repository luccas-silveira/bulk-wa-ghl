import React, { useState } from 'react';
import Button from '../ui/Button';
import { Campaign } from '../../types/campaign';
import { Pause, Play, Trash2 } from 'lucide-react';

export interface CampaignActionsProps {
  campaign: Campaign;
  onPause?: (campaignId: number) => Promise<void | unknown>;
  onResume?: (campaignId: number) => Promise<void | unknown>;
  onDelete?: (campaignId: number) => Promise<void | unknown>;
}

const CampaignActions: React.FC<CampaignActionsProps> = ({
  campaign,
  onPause,
  onResume,
  onDelete,
}) => {
  const [pauseLoading, setPauseLoading] = useState(false);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteNameInput, setDeleteNameInput] = useState('');

  const handlePause = async () => {
    if (!onPause) return;
    setPauseLoading(true);
    try {
      await onPause(campaign.id);
    } finally {
      setPauseLoading(false);
    }
  };

  const handleResume = async () => {
    if (!onResume) return;
    setResumeLoading(true);
    try {
      await onResume(campaign.id);
    } finally {
      setResumeLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!onDelete) return;
    setDeleteLoading(true);
    try {
      await onDelete(campaign.id);
      setShowDeleteConfirm(false);
      setDeleteNameInput('');
    } finally {
      setDeleteLoading(false);
    }
  };

  const canPause = campaign.status === 'executing';
  const canResume = campaign.status === 'paused';
  const canDelete = ['draft', 'cancelled', 'completed', 'failed'].includes(campaign.status);

  return (
    <div className="flex items-center gap-2">
      {canPause && onPause && (
        <Button
          variant="secondary"
          size="sm"
          loading={pauseLoading}
          icon={<Pause />}
          onClick={handlePause}
          title="Pause campaign execution"
        >
          Pause
        </Button>
      )}

      {canResume && onResume && (
        <Button
          variant="primary"
          size="sm"
          loading={resumeLoading}
          icon={<Play />}
          onClick={handleResume}
          title="Resume campaign execution"
        >
          Resume
        </Button>
      )}

      {canDelete && onDelete && (
        <>
          {!showDeleteConfirm ? (
            <Button
              variant="ghost"
              size="sm"
              loading={deleteLoading}
              icon={<Trash2 />}
              onClick={() => {
                setDeleteNameInput('');
                setShowDeleteConfirm(true);
              }}
              title="Delete campaign"
            >
              Delete
            </Button>
          ) : (
            <div className="flex flex-col gap-2">
              <span className="text-sm text-gray-700">
                Digite <strong>{campaign.name}</strong> para confirmar:
              </span>
              <input
                type="text"
                value={deleteNameInput}
                onChange={(e) => setDeleteNameInput(e.target.value)}
                data-testid="delete-name-input"
                placeholder={campaign.name}
                autoFocus
                className="px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
                aria-label="Nome da campanha para confirmar exclusão"
              />
              <div className="flex items-center gap-2">
                <Button
                  variant="danger"
                  size="sm"
                  loading={deleteLoading}
                  disabled={deleteNameInput !== campaign.name}
                  onClick={handleDelete}
                  data-testid="delete-confirm-btn"
                >
                  Excluir
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setShowDeleteConfirm(false);
                    setDeleteNameInput('');
                  }}
                  disabled={deleteLoading}
                >
                  Cancelar
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default CampaignActions;

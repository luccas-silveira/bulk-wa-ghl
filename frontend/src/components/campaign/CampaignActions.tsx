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
              onClick={() => setShowDeleteConfirm(true)}
              title="Delete campaign"
            >
              Delete
            </Button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Delete campaign?</span>
              <Button
                variant="danger"
                size="sm"
                loading={deleteLoading}
                onClick={handleDelete}
              >
                Confirm
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleteLoading}
              >
                Cancel
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default CampaignActions;

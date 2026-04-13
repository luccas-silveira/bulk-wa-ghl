/**
 * CampaignsPage Component
 * Main page for campaign management with list and details views
 */
import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Plus } from 'lucide-react';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import CampaignList from '../components/campaign/CampaignList';
import CampaignDetails from '../components/campaign/CampaignDetails';
import type { CampaignStatus } from '../types/campaign';

export interface CampaignsPageProps {
  onCreateCampaign?: () => void;
  defaultLocationId?: string;
}

const VALID_STATUSES: CampaignStatus[] = [
  'draft', 'scheduled', 'executing', 'paused', 'completed', 'failed', 'cancelled',
];

const CampaignsPage: React.FC<CampaignsPageProps> = ({ onCreateCampaign, defaultLocationId }) => {
  const [selectedCampaignId, setSelectedCampaignId] = useState<number | null>(null);
  const [searchParams] = useSearchParams();

  const rawStatus = searchParams.get('status');
  const statusFilter = VALID_STATUSES.includes(rawStatus as CampaignStatus)
    ? (rawStatus as CampaignStatus)
    : undefined;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Gerenciamento de Campanhas</h1>
          <p className="mt-1 text-sm text-gray-600">
            Visualize, gerencie e monitore todas as suas campanhas de disparo
          </p>
        </div>
        {onCreateCampaign && (
          <Button
            variant="primary"
            icon={<Plus />}
            onClick={onCreateCampaign}
          >
            Nova Campanha
          </Button>
        )}
      </div>

      {/* Campaign Details Modal/View */}
      {selectedCampaignId && (
        <div className="mb-6">
          <CampaignDetails
            campaignId={selectedCampaignId}
            onClose={() => setSelectedCampaignId(null)}
          />
        </div>
      )}

      {/* Campaign List */}
      <CampaignList
        defaultFilters={{
          ...(statusFilter ? { status: statusFilter } : {}),
          ...(defaultLocationId ? { ghl_location_id: defaultLocationId } : {}),
        }}
        onCampaignClick={(campaignId) => setSelectedCampaignId(campaignId)}
      />
    </div>
  );
};

export default CampaignsPage;

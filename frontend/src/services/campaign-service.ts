/**
 * Campaign Management Service
 * Service for interacting with Campaign Management API
 */

import type {
  CampaignsListResponse,
  CampaignDetailsResponse,
  CampaignLogsResponse,
  CampaignStatisticsResponse,
  CampaignActionResponse,
  CampaignFilters,
  CampaignLogsFilters,
} from '../types/campaign';
import { API_BASE_URL } from '../config/env';

class CampaignService {
  private baseUrl: string;

  constructor() {
    // Use environment variable or default to localhost
    this.baseUrl = API_BASE_URL;
  }

  /**
   * Get list of campaigns with filtering and pagination
   * @param filters Campaign filters
   * @param limit Number of campaigns to return
   * @param offset Number of campaigns to skip
   * @returns Promise resolving to campaigns list response
   */
  async listCampaigns(
    filters?: CampaignFilters,
    limit: number = 20,
    offset: number = 0
  ): Promise<CampaignsListResponse> {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());

    if (filters?.status) {
      params.append('status', filters.status);
    }
    if (filters?.ghl_user_id) {
      params.append('ghl_user_id', filters.ghl_user_id);
    }
    if (filters?.ghl_location_id) {
      params.append('ghl_location_id', filters.ghl_location_id);
    }
    if (filters?.from_date) {
      params.append('from_date', filters.from_date);
    }
    if (filters?.to_date) {
      params.append('to_date', filters.to_date);
    }

    const response = await fetch(`${this.baseUrl}/api/v1/campaigns?${params.toString()}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch campaigns: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get detailed campaign information
   * @param campaignId Campaign ID
   * @returns Promise resolving to campaign details
   */
  async getCampaignDetails(campaignId: number): Promise<CampaignDetailsResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/campaigns/${campaignId}/details`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Campaign ${campaignId} not found`);
      }
      throw new Error(`Failed to fetch campaign details: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get campaign message logs
   * @param campaignId Campaign ID
   * @param filters Log filters
   * @param limit Number of logs to return
   * @param offset Number of logs to skip
   * @returns Promise resolving to campaign logs
   */
  async getCampaignLogs(
    campaignId: number,
    filters?: CampaignLogsFilters,
    limit: number = 50,
    offset: number = 0
  ): Promise<CampaignLogsResponse> {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());

    if (filters?.status) {
      params.append('status', filters.status);
    }
    if (filters?.recipient) {
      params.append('recipient', filters.recipient);
    }

    const response = await fetch(
      `${this.baseUrl}/api/v1/campaigns/${campaignId}/logs?${params.toString()}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to fetch campaign logs: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get campaign statistics
   * @param filters Campaign filters
   * @returns Promise resolving to campaign statistics
   */
  async getCampaignStatistics(filters?: CampaignFilters): Promise<CampaignStatisticsResponse> {
    const params = new URLSearchParams();

    if (filters?.ghl_user_id) {
      params.append('ghl_user_id', filters.ghl_user_id);
    }
    if (filters?.ghl_location_id) {
      params.append('ghl_location_id', filters.ghl_location_id);
    }
    if (filters?.from_date) {
      params.append('from_date', filters.from_date);
    }
    if (filters?.to_date) {
      params.append('to_date', filters.to_date);
    }

    const queryString = params.toString();
    const url = queryString
      ? `${this.baseUrl}/api/v1/campaigns/stats?${queryString}`
      : `${this.baseUrl}/api/v1/campaigns/stats`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch campaign statistics: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Pause an executing campaign
   * @param campaignId Campaign ID
   * @returns Promise resolving to campaign action response
   */
  async pauseCampaign(campaignId: number): Promise<CampaignActionResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/campaigns/${campaignId}/pause`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail?.message || `Failed to pause campaign: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Resume a paused campaign
   * @param campaignId Campaign ID
   * @returns Promise resolving to campaign action response
   */
  async resumeCampaign(campaignId: number): Promise<CampaignActionResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/campaigns/${campaignId}/resume`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail?.message || `Failed to resume campaign: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Delete a campaign
   * @param campaignId Campaign ID
   * @returns Promise resolving when campaign is deleted
   */
  async deleteCampaign(campaignId: number): Promise<{ message: string; campaign_id: number }> {
    const response = await fetch(`${this.baseUrl}/api/v1/campaigns/${campaignId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail?.message || `Failed to delete campaign: ${response.statusText}`);
    }

    return response.json();
  }
}

// Export singleton instance
export const campaignService = new CampaignService();

// Export class for testing
export default CampaignService;

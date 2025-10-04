/**
 * Campaign Management Types
 * Matches backend API schemas from contracts/campaign-management-api.yaml
 */

// Campaign Status enum
export type CampaignStatus =
  | 'draft'
  | 'scheduled'
  | 'executing'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

// Message status for individual messages
export type MessageStatus =
  | 'pending'
  | 'sent'
  | 'delivered'
  | 'read'
  | 'failed';

// Message statistics for a campaign
export interface MessageStats {
  total: number;
  sent: number;
  delivered: number;
  read: number;
  failed: number;
  pending: number;
}

// Campaign with aggregated message statistics
export interface CampaignWithStats {
  id: number;
  name: string;
  status: CampaignStatus;
  ghl_location_id: string | null;
  ghl_location_name: string | null;
  ghl_user_id: string | null;
  ghl_user_name: string | null;
  sending_speed: 'slow' | 'medium' | 'fast';
  schedule_type: 'immediate' | 'scheduled';
  scheduled_time: string | null; // ISO 8601
  paused_at: string | null; // ISO 8601
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
  message_stats: MessageStats;
  progress_percent?: number; // Only present for executing campaigns
}

// Response for GET /api/v1/campaigns
export interface CampaignsListResponse {
  campaigns: CampaignWithStats[];
  count: number;
  limit: number;
  offset: number;
}

// Full Campaign details (without stats - used in details response)
export interface Campaign {
  id: number;
  name: string;
  status: CampaignStatus;
  ghl_location_id: string | null;
  ghl_location_name: string | null;
  ghl_user_id: string | null;
  ghl_user_name: string | null;
  sending_speed: 'slow' | 'medium' | 'fast';
  schedule_type: 'immediate' | 'scheduled';
  scheduled_time: string | null; // ISO 8601
  paused_at: string | null; // ISO 8601
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

// Detailed statistics for a campaign
export interface CampaignStatistics {
  total_messages: number;
  sent: number;
  delivered: number;
  read: number;
  failed: number;
  pending: number;
  delivery_rate: number; // Percentage (0-100)
  read_rate: number; // Percentage (0-100)
}

// Campaign progress information
export interface CampaignProgress {
  percent_complete: number; // Percentage (0-100)
  messages_remaining: number;
  estimated_completion: string | null; // ISO 8601 timestamp or null
}

// Timeline event
export interface TimelineEvent {
  event: string; // e.g., "Campaign Created", "Campaign Started", "Campaign Paused"
  timestamp: string; // ISO 8601
}

// Individual message details
export interface Message {
  id: number;
  campaign_id: number;
  recipient_phone: string;
  content: string;
  status: MessageStatus;
  sent_at: string | null; // ISO 8601
  delivered_at: string | null; // ISO 8601
  read_at: string | null; // ISO 8601
  error_message: string | null;
  ghl_conversation_id: string | null;
  ghl_message_id: string | null;
  ghl_status: string | null;
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

// Response for GET /api/v1/campaigns/{id}/details
export interface CampaignDetailsResponse {
  campaign: Campaign;
  statistics: CampaignStatistics;
  timeline: TimelineEvent[];
  recent_messages: Message[];
}

// Response for GET /api/v1/campaigns/{id}/logs
export interface CampaignLogsResponse {
  messages: Message[];
  count: number;
  limit: number;
  offset: number;
  campaign_id: number;
}

// Campaign counts by status
export interface CampaignCounts {
  draft: number;
  scheduled: number;
  executing: number;
  paused: number;
  completed: number;
  failed: number;
  cancelled: number;
}

// Delivery metrics across campaigns
export interface DeliveryMetrics {
  total_messages: number;
  avg_delivery_rate: number; // Percentage (0-100)
  avg_read_rate: number; // Percentage (0-100)
}

// Campaign with calculated rates (for top performers)
export interface CampaignWithRates extends Campaign {
  read_rate: number; // Percentage (0-100)
  delivery_rate?: number; // Percentage (0-100), optional
}

// Response for GET /api/v1/campaigns/stats
export interface CampaignStatisticsResponse {
  campaign_counts: CampaignCounts;
  delivery_metrics: DeliveryMetrics;
  recent_campaigns: Campaign[];
  top_performing_campaigns: CampaignWithRates[];
}

// Response for PATCH /api/v1/campaigns/{id}/pause and /resume
export interface CampaignActionResponse {
  message: string;
  campaign: Campaign;
}

// Filters for listing campaigns
export interface CampaignFilters {
  status?: CampaignStatus;
  ghl_user_id?: string;
  ghl_location_id?: string;
  from_date?: string; // ISO 8601
  to_date?: string; // ISO 8601
}

// Filters for campaign logs
export interface CampaignLogsFilters {
  status?: MessageStatus;
  recipient?: string; // Partial match on phone number
}

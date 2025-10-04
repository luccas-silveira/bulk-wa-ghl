/**
 * API Types for WhatsApp Campaign Management with GoHighLevel
 *
 * TypeScript type definitions for API requests and responses.
 * Updated to use GoHighLevel (GHL) instead of WAHA.
 */

// Import GHL types
export type { GHLLocation, GHLLocationValidation, GHLMessage, GHLConversation } from './ghl';

// Legacy WAHA Session Types (deprecated)
/**
 * @deprecated Use GHLLocation from './ghl' instead
 */
export interface WAHASession {
  id: string;
  name: string;
  status: 'WORKING' | 'STARTING' | 'SCAN_QR_CODE' | 'STOPPED' | 'FAILED';
  is_active: boolean;
  me: {
    id: string;
    pushName: string;
  };
  last_updated: string;
}

/**
 * @deprecated Use GHLLocation[] instead
 */
export interface WAHASessionsResponse {
  sessions: WAHASession[];
}

/**
 * @deprecated Use GHLLocationValidation instead
 */
export interface WAHASessionValidation {
  valid: boolean;
  session_id: string;
  session_name: string;
  status: string;
  validated_at: string;
}

// Campaign Types (Updated for GHL)
export interface CampaignCreateRequest {
  name: string;
  ghl_location_id: string; // GHL location ID (replaces waha_session_id)
  ghl_user_id?: string; // Single user (backwards compat)
  ghl_user_ids?: string[]; // Multiple users for round-robin distribution
  sending_speed: 'slow' | 'medium' | 'fast';
  schedule_type: 'immediate' | 'scheduled';
  scheduled_time?: string; // ISO datetime string
  messages: CampaignMessage[];
  audience_criteria: AudienceCriteria;
}

export interface CampaignMessage {
  text: string;
  media_url?: string;
  order: number;
}

export interface AudienceCriteria {
  filter_type: 'all_contacts' | 'csv_upload' | 'tag_based';
  csv_data?: ContactCsvData[];
  tag_filters?: TagFilters;
}

export interface ContactCsvData {
  phone_number: string;
  name?: string;
  email?: string;
  [key: string]: string | undefined; // Additional custom fields
}

export interface TagFilters {
  logic: 'AND' | 'OR';
  tags: string[];
}

export interface CampaignResponse {
  id: string;
  name: string;
  status: 'draft' | 'scheduled' | 'executing' | 'completed' | 'failed';
  ghl_location_id: string; // GHL location ID
  ghl_location_name?: string; // Location display name
  sending_speed: 'slow' | 'medium' | 'fast';
  schedule_type: 'immediate' | 'scheduled';
  scheduled_time?: string;
  created_at: string;
  estimated_recipients: number;
}

// Dashboard Types (Updated to match backend API contract)
export interface DashboardResponse {
  campaign_metrics: CampaignMetrics;
  delivery_metrics: DeliveryMetrics;
  recent_campaigns: RecentCampaign[];
  top_performing_campaigns: TopCampaign[];
  time_range: string;
  filter_info: string;
}

export interface CampaignMetrics {
  total_campaigns: number;
  draft_campaigns: number;
  scheduled_campaigns: number;
  active_campaigns: number;
  completed_campaigns: number;
  failed_campaigns: number;
  cancelled_campaigns: number;
}

export interface DeliveryMetrics {
  sent: number;
  delivered: number;
  failed: number;
  delivery_rate: number; // Percentage (0-100)
  read_rate: number; // Percentage (0-100)
}

export interface RecentCampaign {
  id: number;
  name: string;
  status: 'draft' | 'scheduled' | 'executing' | 'completed' | 'failed' | 'cancelled';
  delivery_rate: number;
  created_at: string;
  messages_sent: number;
}

export interface TopCampaign {
  id: number;
  name: string;
  delivered_count: number;
  read_rate: number;
  delivery_rate: number;
}

// Legacy alias for backwards compatibility
export interface DashboardMetrics extends DashboardResponse {}
export interface TopPerformingCampaign extends TopCampaign {}

// Dashboard Request Parameters (Updated)
export interface DashboardParams {
  ghl_user_id?: string; // Now optional for aggregated view
  days?: number; // Number of days to look back (1-365)
  date_range?: 'last_7_days' | 'last_30_days' | 'custom';
  start_date?: string;
  end_date?: string;
}

// Error Response Types
export interface APIError {
  error: string;
  message: string;
  details?: string;
}

export interface ValidationError {
  error: string;
  message: string;
  field_errors?: Record<string, string[]>;
}

export interface SessionValidationError {
  error: 'Session validation failed';
  message: string;
  session_status: string;
}

// Legacy Types (for backwards compatibility during migration)
/**
 * @deprecated Use waha_session_id instead
 */
export interface LegacyCampaignRequest {
  name: string;
  whatsapp_channel?: string;
  ghl_user_id?: string;
  ghl_team_id?: string; // This field no longer exists
  sending_speed: 'slow' | 'medium' | 'fast';
  schedule_type: 'immediate' | 'scheduled';
  messages: CampaignMessage[];
  audience_criteria: AudienceCriteria;
}

// Utility Types
export type CampaignStatus = 'draft' | 'scheduled' | 'executing' | 'completed' | 'failed';
export type SendingSpeed = 'slow' | 'medium' | 'fast';
export type ScheduleType = 'immediate' | 'scheduled';
export type WAHASessionStatus = 'WORKING' | 'STARTING' | 'SCAN_QR_CODE' | 'STOPPED' | 'FAILED';

// Form Types for Frontend Components
export interface CampaignFormData {
  name: string;
  ghl_location_id: string; // GHL location ID (replaces waha_session_id)
  ghl_user_id?: string; // Single user (backwards compat)
  ghl_user_ids?: string[]; // Multiple users for round-robin
  sending_speed: SendingSpeed;
  schedule_type: ScheduleType;
  scheduled_time?: Date;
  messages: {
    text: string;
    media_url?: string;
  }[];
  audience_type: 'all_contacts' | 'csv_upload' | 'tag_based';
  csv_file?: File;
  tag_filters?: {
    logic: 'AND' | 'OR';
    selected_tags: string[];
  };
}

// Component Props Types
export interface SessionSelectorProps {
  value: string;
  onChange: (sessionId: string) => void;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
  error?: string;
}

export interface DashboardCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  loading?: boolean;
}

// API Response Wrapper
export interface APIResponse<T> {
  data: T;
  status: number;
  message?: string;
}

// HTTP Methods for API calls
export type HTTPMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

// API Configuration
export interface APIConfig {
  baseURL: string;
  timeout: number;
  headers: Record<string, string>;
}
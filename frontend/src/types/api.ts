/**
 * API Types for WhatsApp Campaign Interface Improvements
 *
 * TypeScript type definitions for API requests and responses.
 */

// WAHA Session Types
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

export interface WAHASessionsResponse {
  sessions: WAHASession[];
}

export interface WAHASessionValidation {
  valid: boolean;
  session_id: string;
  session_name: string;
  status: string;
  validated_at: string;
}

// Campaign Types (Updated)
export interface CampaignCreateRequest {
  name: string;
  waha_session_id: string; // New field replacing whatsapp_channel + ghl_user_id
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
  waha_session_id: string; // New field
  sending_speed: 'slow' | 'medium' | 'fast';
  schedule_type: 'immediate' | 'scheduled';
  scheduled_time?: string;
  created_at: string;
  estimated_recipients: number;
}

// Dashboard Types (Updated)
export interface DashboardMetrics {
  campaign_metrics: {
    total_campaigns: number;
    active_campaigns: number;
    completed_campaigns: number;
    failed_campaigns: number;
  };
  delivery_metrics: {
    sent: number;
    delivery_rate: number; // Percentage (0-100)
    read_rate: number; // Percentage (0-100)
  };
  recent_campaigns: RecentCampaign[];
  top_performing_campaigns: TopPerformingCampaign[];
}

export interface RecentCampaign {
  id: string;
  name: string;
  status: 'draft' | 'scheduled' | 'executing' | 'completed' | 'failed';
  delivery_rate: number;
  created_at: string;
}

export interface TopPerformingCampaign {
  id: string;
  name: string;
  delivered_count: number;
  read_rate: number;
}

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
  waha_session_id: string;
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
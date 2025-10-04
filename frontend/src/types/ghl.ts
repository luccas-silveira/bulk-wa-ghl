/**
 * GoHighLevel (GHL) Types
 * Type definitions for GHL API entities
 */

/**
 * GHL Location (Sub-Account)
 * Represents a GoHighLevel location with WhatsApp integration
 */
export interface GHLLocation {
  id: number;
  ghl_location_id: string;
  name: string;
  company_id: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  timezone?: string;
  has_whatsapp: boolean;
  whatsapp_number?: string;
  whatsapp_status?: 'active' | 'inactive' | 'pending' | 'error';
  is_active: boolean;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

/**
 * GHL Location Validation Result
 * Result of validating a location for messaging
 */
export interface GHLLocationValidation {
  location_id: string;
  is_valid: boolean;
  has_whatsapp: boolean;
  whatsapp_status: string;
  has_oauth_token: boolean;
  token_expired: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * GHL Conversation
 * Represents a WhatsApp conversation in GHL
 */
export interface GHLConversation {
  id: number;
  ghl_conversation_id: string;
  ghl_location_id: string;
  ghl_contact_id: string;
  contact_phone: string;
  contact_name?: string;
  unread_count: number;
  last_message_at?: string;
  created_at: string;
  updated_at: string;
}

/**
 * GHL Message
 * Represents a WhatsApp message sent through GHL
 */
export interface GHLMessage {
  id: number;
  campaign_id?: number;
  recipient_phone: string;
  content: string;
  status: 'pending' | 'sent' | 'delivered' | 'read' | 'failed';
  sent_at?: string;
  delivered_at?: string;
  read_at?: string;
  error_message?: string;
  ghl_conversation_id?: string;
  ghl_message_id?: string;
  ghl_status?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Send Message Request
 * Request payload for sending a WhatsApp message via GHL
 */
export interface SendMessageRequest {
  ghl_location_id: string;
  contact_phone: string;
  message_text: string;
  media_url?: string;
  campaign_id?: number;
}

/**
 * Send Message Response
 * Response from sending a WhatsApp message via GHL
 */
export interface SendMessageResponse {
  message_id: number;
  ghl_message_id: string;
  conversation_id: string;
  contact_id: string;
  status: string;
  sent_at: string;
  recipient_phone: string;
  message_text: string;
}

/**
 * GHL OAuth Token (for display purposes only - never expose encrypted values)
 */
export interface GHLOAuthTokenInfo {
  ghl_location_id: string;
  expires_at: string;
  scope: string;
  is_expired: boolean;
}

/**
 * GHL User
 * Represents a user within a GHL location
 */
export interface GHLUser {
  id: number;
  ghl_user_id: string;
  ghl_location_id: string;
  name: string;
  email?: string;
  phone?: string;
  role?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

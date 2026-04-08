/**
 * GHL Location Service
 * Service for interacting with GoHighLevel Locations API
 */

import type { GHLLocation, GHLLocationValidation } from '../types/ghl';
import { API_BASE_URL } from '../config/env';

class GHLLocationService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  /**
   * Get all GHL locations with optional filtering
   * @param hasWhatsapp Filter by WhatsApp availability
   * @param isActive Filter by active status
   * @returns Promise resolving to array of GHL locations
   */
  async getLocations(
    hasWhatsapp?: boolean,
    isActive?: boolean
  ): Promise<GHLLocation[]> {
    const params = new URLSearchParams();

    if (hasWhatsapp !== undefined) {
      params.append('whatsapp', hasWhatsapp.toString());
    }

    if (isActive !== undefined) {
      params.append('active', isActive.toString());
    }

    const queryString = params.toString();
    const url = queryString
      ? `${this.baseUrl}/ghl/locations?${queryString}`
      : `${this.baseUrl}/ghl/locations`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch locations: ${response.statusText}`);
    }

    const data = await response.json();
    return data.locations || [];
  }

  /**
   * Get a specific GHL location by ID
   * @param locationId GHL location ID
   * @returns Promise resolving to GHL location
   */
  async getLocation(locationId: string): Promise<GHLLocation> {
    const response = await fetch(`${this.baseUrl}/ghl/locations/${locationId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Location ${locationId} not found`);
      }
      throw new Error(`Failed to fetch location: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Validate a GHL location for messaging
   * @param locationId GHL location ID
   * @returns Promise resolving to validation result
   */
  async validateLocation(locationId: string): Promise<GHLLocationValidation> {
    const response = await fetch(
      `${this.baseUrl}/ghl/locations/${locationId}/validate`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to validate location: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Format a GHL location for display in dropdown
   * @param location GHL location
   * @returns Formatted string for display
   */
  formatLocationForDisplay(location: GHLLocation): string {
    const parts: string[] = [location.name];

    if (location.whatsapp_number) {
      parts.push(`(${location.whatsapp_number})`);
    }

    if (location.whatsapp_status) {
      const statusEmoji = {
        active: '✅',
        inactive: '❌',
        pending: '⏳',
        error: '⚠️',
      }[location.whatsapp_status] || '❓';

      parts.push(`${statusEmoji} ${location.whatsapp_status}`);
    }

    return parts.join(' ');
  }

  /**
   * Get only active locations with WhatsApp enabled
   * Convenience method for campaign creation
   * @returns Promise resolving to array of active GHL locations with WhatsApp
   */
  async getActiveWhatsAppLocations(): Promise<GHLLocation[]> {
    return this.getLocations(true, true);
  }

  /**
   * Check if a location is ready for messaging
   * @param location GHL location
   * @returns True if location is ready
   */
  isLocationReady(location: GHLLocation): boolean {
    return (
      location.is_active &&
      location.has_whatsapp &&
      location.whatsapp_status === 'active'
    );
  }
}

// Export singleton instance
export const ghlLocationService = new GHLLocationService();

// Export class for testing
export default GHLLocationService;

/**
 * WAHA Session Service for WhatsApp Campaign Interface Improvements
 *
 * Service for fetching and managing WAHA (WhatsApp HTTP API) sessions
 * from the backend API.
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

export interface WAHAError {
  error: string;
  message: string;
  retry_after?: number;
}

class WAHASessionService {
  private readonly baseUrl: string;

  constructor() {
    // Use environment variable or default to backend URL
    this.baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  }

  /**
   * Fetch all WAHA sessions
   */
  async getSessions(): Promise<WAHASession[]> {
    try {
      const response = await fetch(`${this.baseUrl}/waha/sessions`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        console.error('Failed to fetch WAHA sessions:', response.statusText);
        return [];
      }

      const data: WAHASessionsResponse = await response.json();
      return data.sessions || [];
    } catch (error) {
      console.error('Error fetching WAHA sessions:', error);
      return [];
    }
  }

  /**
   * Fetch only active (WORKING) WAHA sessions
   */
  async getActiveSessions(): Promise<WAHASession[]> {
    try {
      const response = await fetch(`${this.baseUrl}/waha/sessions/active`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        console.error('Failed to fetch active WAHA sessions:', response.statusText);
        return [];
      }

      const data: WAHASessionsResponse = await response.json();
      return data.sessions || [];
    } catch (error) {
      console.error('Error fetching active WAHA sessions:', error);
      return [];
    }
  }

  /**
   * Get specific session status by ID
   */
  async getSessionStatus(sessionId: string): Promise<WAHASession | null> {
    try {
      const response = await fetch(`${this.baseUrl}/waha/sessions/${sessionId}/status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.status === 404) {
        return null; // Session not found
      }

      if (!response.ok) {
        console.error('Failed to fetch session status:', response.statusText);
        return null;
      }

      const session: WAHASession = await response.json();
      return session;
    } catch (error) {
      console.error('Error fetching session status:', error);
      return null;
    }
  }

  /**
   * Validate session for campaign creation
   */
  async validateSessionForCampaign(sessionId: string): Promise<WAHASessionValidation | null> {
    try {
      const response = await fetch(`${this.baseUrl}/waha/sessions/${sessionId}/validate`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 422) {
          // Session validation failed
          const error: WAHAError = await response.json();
          throw new Error(error.message || 'Session validation failed');
        }
        throw new Error('Service unavailable');
      }

      const validation: WAHASessionValidation = await response.json();
      return validation;
    } catch (error) {
      console.error('Error validating session:', error);
      return null;
    }
  }

  /**
   * Format session for display in dropdown
   */
  formatSessionForDisplay(session: WAHASession): string {
    const statusIcon = session.is_active ? '✓' : '✗';
    const businessName = session.me.pushName || 'Unknown Business';
    return `${statusIcon} ${session.name} (${businessName})`;
  }

  /**
   * Get session display status
   */
  getSessionDisplayStatus(session: WAHASession): {
    text: string;
    color: string;
    icon: string;
  } {
    switch (session.status) {
      case 'WORKING':
        return {
          text: 'Active',
          color: 'text-green-600',
          icon: '✓'
        };
      case 'STARTING':
        return {
          text: 'Starting',
          color: 'text-yellow-600',
          icon: '⏳'
        };
      case 'SCAN_QR_CODE':
        return {
          text: 'Scan QR',
          color: 'text-blue-600',
          icon: '📱'
        };
      case 'STOPPED':
        return {
          text: 'Stopped',
          color: 'text-gray-600',
          icon: '⏹'
        };
      case 'FAILED':
        return {
          text: 'Failed',
          color: 'text-red-600',
          icon: '✗'
        };
      default:
        return {
          text: 'Unknown',
          color: 'text-gray-400',
          icon: '?'
        };
    }
  }

  /**
   * Check if service is available
   */
  async isServiceAvailable(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/waha/sessions`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      return response.ok;
    } catch (error) {
      return false;
    }
  }

  /**
   * Filter sessions for campaign creation (active sessions only)
   */
  filterSessionsForCampaign(sessions: WAHASession[]): WAHASession[] {
    return sessions.filter(session => session.is_active && session.status === 'WORKING');
  }
}

// Export singleton instance
export const wahaSessionService = new WAHASessionService();

// Export class for testing
export default WAHASessionService;
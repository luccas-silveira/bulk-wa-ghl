/**
 * useGHLUsers Hook
 * React hook for fetching and managing GHL users
 */
import { useState, useEffect, useCallback } from 'react';
import { GHLUser } from '../types/ghl';
import { API_BASE_URL } from '../config/env';

interface UseGHLUsersOptions {
  locationId?: string;
  sync?: boolean;
  autoFetch?: boolean;
}

interface UseGHLUsersReturn {
  users: GHLUser[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch users for a specific GHL location
 */
export function useGHLUsers(options: UseGHLUsersOptions = {}): UseGHLUsersReturn {
  const { locationId, sync = false, autoFetch = true } = options;

  const [users, setUsers] = useState<GHLUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    if (!locationId) {
      setUsers([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        location_id: locationId,
        sync: sync.toString(),
      });

      const response = await fetch(`${API_BASE_URL}/ghl/users?${params}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch users: ${response.statusText}`);
      }

      const data = await response.json();
      setUsers(data.users || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [locationId, sync]);

  useEffect(() => {
    if (autoFetch && locationId) {
      fetchUsers();
    }
  }, [locationId, autoFetch, fetchUsers]);

  return {
    users,
    loading,
    error,
    refetch: fetchUsers,
  };
}

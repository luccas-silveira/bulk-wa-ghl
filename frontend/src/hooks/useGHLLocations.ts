/**
 * useGHLLocations Hook
 * React hook for managing GHL locations state
 */

import { useState, useEffect, useCallback } from 'react';
import { ghlLocationService } from '../services/ghl-location-service';
import type { GHLLocation } from '../types/ghl';

interface UseGHLLocationsOptions {
  /** Filter by WhatsApp availability */
  hasWhatsapp?: boolean;
  /** Filter by active status */
  isActive?: boolean;
  /** Auto-fetch on mount */
  autoFetch?: boolean;
}

interface UseGHLLocationsReturn {
  /** Array of GHL locations */
  locations: GHLLocation[];
  /** Loading state */
  loading: boolean;
  /** Error message if fetch failed */
  error: string | null;
  /** Manually trigger a refetch */
  refetch: () => Promise<void>;
  /** Active WhatsApp-enabled locations only */
  activeLocations: GHLLocation[];
}

/**
 * Hook to fetch and manage GHL locations
 *
 * @example
 * ```tsx
 * const { locations, loading, error, refetch } = useGHLLocations({
 *   hasWhatsapp: true,
 *   isActive: true
 * });
 * ```
 */
export function useGHLLocations(
  options: UseGHLLocationsOptions = {}
): UseGHLLocationsReturn {
  const { hasWhatsapp, isActive, autoFetch = true } = options;

  const [locations, setLocations] = useState<GHLLocation[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLocations = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await ghlLocationService.getLocations(
        hasWhatsapp,
        isActive
      );
      setLocations(data);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to fetch GHL locations';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [hasWhatsapp, isActive]);

  // Auto-fetch on mount and when filters change
  useEffect(() => {
    if (autoFetch) {
      fetchLocations();
    }
  }, [autoFetch, fetchLocations]);

  // Computed: active WhatsApp-enabled locations
  const activeLocations = locations.filter(
    (location) => ghlLocationService.isLocationReady(location)
  );

  return {
    locations,
    loading,
    error,
    refetch: fetchLocations,
    activeLocations,
  };
}

/**
 * Hook variant that only fetches active WhatsApp locations
 * Convenience hook for campaign creation
 */
export function useActiveWhatsAppLocations() {
  return useGHLLocations({
    hasWhatsapp: true,
    isActive: true,
    autoFetch: true,
  });
}

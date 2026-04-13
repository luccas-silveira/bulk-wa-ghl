import { useSearchParams } from 'react-router-dom';

export interface EmbeddedMode {
  isEmbedded: boolean;
  ghlLocationId: string | null;
  ghlUserId: string | null;
}

export function useEmbeddedMode(): EmbeddedMode {
  const [params] = useSearchParams();
  const isEmbedded = params.get('embedded') === 'true';
  return {
    isEmbedded,
    ghlLocationId: isEmbedded ? params.get('ghl_location_id') : null,
    ghlUserId: isEmbedded ? params.get('ghl_user_id') : null,
  };
}

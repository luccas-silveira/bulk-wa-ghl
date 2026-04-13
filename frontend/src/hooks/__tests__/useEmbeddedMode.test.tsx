import { renderHook } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { useEmbeddedMode } from '../useEmbeddedMode';

const wrap = (search: string) => ({
  wrapper: ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter initialEntries={[`/embedded${search}`]}>{children}</MemoryRouter>
  ),
});

describe('useEmbeddedMode', () => {
  it('returns embedded=false when param is missing', () => {
    const { result } = renderHook(() => useEmbeddedMode(), wrap(''));
    expect(result.current.isEmbedded).toBe(false);
    expect(result.current.ghlLocationId).toBeNull();
    expect(result.current.ghlUserId).toBeNull();
  });

  it('returns embedded=true with location and user when params present', () => {
    const { result } = renderHook(
      () => useEmbeddedMode(),
      wrap('?embedded=true&ghl_location_id=loc123&ghl_user_id=usr456')
    );
    expect(result.current.isEmbedded).toBe(true);
    expect(result.current.ghlLocationId).toBe('loc123');
    expect(result.current.ghlUserId).toBe('usr456');
  });

  it('returns isEmbedded=false if embedded param is not "true"', () => {
    const { result } = renderHook(
      () => useEmbeddedMode(),
      wrap('?embedded=1&ghl_location_id=loc123')
    );
    expect(result.current.isEmbedded).toBe(false);
  });
});

import { afterEach, describe, expect, it, vi } from 'vitest';
import { authenticatedFetch, logoutSession, setAccessToken } from './auth';

afterEach(() => {
  setAccessToken(null);
  vi.unstubAllGlobals();
});
const refreshed = {
  access_token: 'test-new-access',
  token_type: 'bearer',
  user: { id: 'test-user', name: 'Test', email: 'test@example.invalid', role: 'customer' },
};

describe('in-memory authenticated requests', () => {
  it('refreshes once on 401 and retries with the new bearer token', async () => {
    setAccessToken('test-old-access');
    const mock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(refreshed)))
      .mockResolvedValueOnce(new Response('ok'));
    vi.stubGlobal('fetch', mock);
    expect((await authenticatedFetch('/api/conversations')).status).toBe(200);
    expect(mock).toHaveBeenCalledTimes(3);
    const first = mock.mock.calls[0]?.[1] as RequestInit;
    const retry = mock.mock.calls[2]?.[1] as RequestInit;
    expect(new Headers(first.headers).get('Authorization')).toBe('Bearer test-old-access');
    expect(new Headers(retry.headers).get('Authorization')).toBe('Bearer test-new-access');
    expect(mock).toHaveBeenNthCalledWith(
      2,
      '/api/auth/refresh',
      expect.objectContaining({
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'Humanizar' },
      }),
    );
  });

  it('does not refresh a second time if the retried request still returns 401', async () => {
    const mock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(refreshed)))
      .mockResolvedValueOnce(new Response(null, { status: 401 }));
    vi.stubGlobal('fetch', mock);
    expect((await authenticatedFetch('/api/requests')).status).toBe(401);
    expect(mock).toHaveBeenCalledTimes(3);
  });

  it('deduplicates refresh for concurrent expired requests', async () => {
    const seen = new Set<string>();
    let refreshes = 0;
    vi.stubGlobal(
      'fetch',
      vi.fn((path: string) => {
        if (path === '/api/auth/refresh') {
          refreshes++;
          return Promise.resolve(new Response(JSON.stringify(refreshed)));
        }
        if (!seen.has(path)) {
          seen.add(path);
          return Promise.resolve(new Response(null, { status: 401 }));
        }
        return Promise.resolve(new Response('ok'));
      }),
    );
    const results = await Promise.all([
      authenticatedFetch('/api/one'),
      authenticatedFetch('/api/two'),
    ]);
    expect(results.map((result) => result.status)).toEqual([200, 200]);
    expect(refreshes).toBe(1);
  });

  it('clears access token after logout and includes the anti-CSRF header', async () => {
    setAccessToken('test-access');
    const mock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', mock);
    await logoutSession();
    await authenticatedFetch('/api/health');
    const logout = mock.mock.calls[0]?.[1] as RequestInit;
    const later = mock.mock.calls[1]?.[1] as RequestInit;
    expect(new Headers(logout.headers).get('X-Requested-With')).toBe('Humanizar');
    expect(new Headers(later.headers).has('Authorization')).toBe(false);
  });
});

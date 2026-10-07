import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  authenticatedFetch,
  logoutSession,
  refreshSession,
  SessionRefreshError,
  setAccessToken,
} from './auth';

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
  it.each([503, 429])(
    'preserves the session after 401 followed by a refresh %s',
    async (status) => {
      setAccessToken('test-retained-access');
      vi.stubGlobal('window', new EventTarget());
      const expired = vi.fn();
      window.addEventListener('humanizar-session-expired', expired);
      const mock = vi
        .fn()
        .mockResolvedValueOnce(new Response(null, { status: 401 }))
        .mockResolvedValueOnce(new Response(null, { status }))
        .mockResolvedValueOnce(new Response('ok'));
      vi.stubGlobal('fetch', mock);
      await expect(authenticatedFetch('/api/conversations')).rejects.toMatchObject({
        name: 'SessionRefreshError',
        status,
      });
      expect(expired).not.toHaveBeenCalled();
      expect(mock).toHaveBeenCalledTimes(2);
      await authenticatedFetch('/api/health');
      const later = mock.mock.calls[2]?.[1] as RequestInit;
      expect(new Headers(later.headers).get('Authorization')).toBe('Bearer test-retained-access');
    },
  );

  it('preserves the session when a refresh fails on the network', async () => {
    setAccessToken('test-retained-access');
    vi.stubGlobal('window', new EventTarget());
    const expired = vi.fn();
    window.addEventListener('humanizar-session-expired', expired);
    const mock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockRejectedValueOnce(new TypeError('Synthetic offline'))
      .mockResolvedValueOnce(new Response('ok'));
    vi.stubGlobal('fetch', mock);
    await expect(authenticatedFetch('/api/requests')).rejects.toBeInstanceOf(SessionRefreshError);
    expect(expired).not.toHaveBeenCalled();
    await authenticatedFetch('/api/health');
    const later = mock.mock.calls[2]?.[1] as RequestInit;
    expect(new Headers(later.headers).get('Authorization')).toBe('Bearer test-retained-access');
  });

  it.each([401, 403])(
    'expires only when refresh rejects authentication with %s',
    async (status) => {
      setAccessToken('test-access');
      vi.stubGlobal('window', new EventTarget());
      const expired = vi.fn();
      window.addEventListener('humanizar-session-expired', expired);
      const mock = vi
        .fn()
        .mockResolvedValueOnce(new Response(null, { status: 401 }))
        .mockResolvedValueOnce(new Response(null, { status }))
        .mockResolvedValueOnce(new Response('ok'));
      vi.stubGlobal('fetch', mock);
      expect((await authenticatedFetch('/api/requests')).status).toBe(401);
      expect(expired).toHaveBeenCalledOnce();
      await authenticatedFetch('/api/health');
      const later = mock.mock.calls[2]?.[1] as RequestInit;
      expect(new Headers(later.headers).has('Authorization')).toBe(false);
    },
  );

  it('can renew again after a temporary refresh failure without a loop', async () => {
    setAccessToken('test-old-access');
    const mock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(refreshed)))
      .mockResolvedValueOnce(new Response('ok'));
    vi.stubGlobal('fetch', mock);
    await expect(authenticatedFetch('/api/requests')).rejects.toBeInstanceOf(SessionRefreshError);
    expect((await authenticatedFetch('/api/requests')).status).toBe(200);
    expect(mock).toHaveBeenCalledTimes(5);
  });

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
    vi.stubGlobal('window', new EventTarget());
    const expired = vi.fn();
    window.addEventListener('humanizar-session-expired', expired);
    const mock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(refreshed)))
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response('ok'));
    vi.stubGlobal('fetch', mock);
    expect((await authenticatedFetch('/api/requests')).status).toBe(401);
    expect(mock).toHaveBeenCalledTimes(3);
    expect(expired).toHaveBeenCalledOnce();
    await authenticatedFetch('/api/health');
    const later = mock.mock.calls[3]?.[1] as RequestInit;
    expect(new Headers(later.headers).has('Authorization')).toBe(false);
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

  it('cannot restore a token from a refresh that finishes after logout', async () => {
    let resolveRefresh: (value: Response) => void = () => undefined;
    const pending = new Promise<Response>((resolve) => {
      resolveRefresh = resolve;
    });
    const mock = vi
      .fn()
      .mockReturnValueOnce(pending)
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response('ok'));
    vi.stubGlobal('fetch', mock);
    const refresh = refreshSession();
    await logoutSession();
    resolveRefresh(new Response(JSON.stringify(refreshed)));
    expect(await refresh).toBeNull();
    await authenticatedFetch('/api/health');
    const later = mock.mock.calls[2]?.[1] as RequestInit;
    expect(new Headers(later.headers).has('Authorization')).toBe(false);
  });

  it('cannot replace the access token of a newly authenticated account with an old refresh', async () => {
    let resolveRefresh: (value: Response) => void = () => undefined;
    const pending = new Promise<Response>((resolve) => {
      resolveRefresh = resolve;
    });
    const mock = vi.fn().mockReturnValueOnce(pending).mockResolvedValueOnce(new Response('ok'));
    vi.stubGlobal('fetch', mock);
    const refresh = refreshSession();
    setAccessToken('test-different-account');
    resolveRefresh(new Response(JSON.stringify(refreshed)));
    expect(await refresh).toBeNull();
    await authenticatedFetch('/api/conversations');
    const next = mock.mock.calls[1]?.[1] as RequestInit;
    expect(new Headers(next.headers).get('Authorization')).toBe('Bearer test-different-account');
  });

  it('clears a refresh that completed while the logout request was still in progress', async () => {
    let resolveLogout: (value: Response) => void = () => undefined;
    const pending = new Promise<Response>((resolve) => {
      resolveLogout = resolve;
    });
    const mock = vi
      .fn()
      .mockReturnValueOnce(pending)
      .mockResolvedValueOnce(new Response(JSON.stringify(refreshed)))
      .mockResolvedValueOnce(new Response('ok'));
    vi.stubGlobal('fetch', mock);
    const logout = logoutSession();
    await refreshSession();
    resolveLogout(new Response(null, { status: 204 }));
    await logout;
    await authenticatedFetch('/api/health');
    const later = mock.mock.calls[2]?.[1] as RequestInit;
    expect(new Headers(later.headers).has('Authorization')).toBe(false);
  });

  it('rejects a malformed refresh response without accepting its token', async () => {
    const mock = vi
      .fn()
      .mockResolvedValueOnce(new Response('{"access_token":"unexpected"}'))
      .mockResolvedValueOnce(new Response('ok'));
    vi.stubGlobal('fetch', mock);
    await expect(refreshSession()).rejects.toThrow('datos inválidos');
    await authenticatedFetch('/api/health');
    const later = mock.mock.calls[1]?.[1] as RequestInit;
    expect(new Headers(later.headers).has('Authorization')).toBe(false);
  });
});

import type { AuthResponse } from './types';
import { isAuthResponse, validate } from './validation';

let accessToken: string | null = null;
let refreshInFlight: Promise<AuthResponse | null> | null = null;
let sessionRevision = 0;

export class SessionRefreshError extends Error {
  constructor(
    readonly status: number | null,
    cause?: unknown,
  ) {
    super(
      'No se pudo renovar la sesión temporalmente. Reintenta cuando el servicio esté disponible.',
      {
        cause,
      },
    );
    this.name = 'SessionRefreshError';
  }
}

export function setAccessToken(token: string | null): void {
  sessionRevision++;
  accessToken = token;
  refreshInFlight = null;
}

export async function refreshSession(): Promise<AuthResponse | null> {
  if (refreshInFlight) return refreshInFlight;
  const revision = sessionRevision;
  const pending = (async () => {
    let response: Response;
    try {
      response = await fetch('/api/auth/refresh', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'Humanizar' },
      });
    } catch (error) {
      if (revision !== sessionRevision) return null;
      throw new SessionRefreshError(null, error);
    }
    if (revision !== sessionRevision) return null;
    if (response.status === 401 || response.status === 403) {
      accessToken = null;
      return null;
    }
    if (!response.ok) throw new SessionRefreshError(response.status);
    const result = validate(await response.json(), isAuthResponse);
    if (revision !== sessionRevision) return null;
    accessToken = result.access_token;
    return result;
  })();
  refreshInFlight = pending;
  try {
    return await pending;
  } finally {
    if (refreshInFlight === pending) refreshInFlight = null;
  }
}

export async function authenticatedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const revision = sessionRevision;
  const perform = () => {
    const headers = new Headers(init.headers);
    if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
    return fetch(path, { ...init, headers, credentials: 'same-origin' });
  };
  const response = await perform();
  if (response.status !== 401 || revision !== sessionRevision) return response;
  init.signal?.throwIfAborted();
  const session = await refreshSession();
  init.signal?.throwIfAborted();
  if (revision !== sessionRevision) return response;
  if (session) {
    const retry = await perform();
    if (retry.status !== 401 || revision !== sessionRevision) return retry;
    setAccessToken(null);
    if (typeof window !== 'undefined') window.dispatchEvent(new Event('humanizar-session-expired'));
    return retry;
  }
  setAccessToken(null);
  if (typeof window !== 'undefined') window.dispatchEvent(new Event('humanizar-session-expired'));
  return response;
}

export async function logoutSession(): Promise<void> {
  const token = accessToken;
  setAccessToken(null);
  const headers = new Headers({ 'X-Requested-With': 'Humanizar' });
  if (token) headers.set('Authorization', `Bearer ${token}`);
  try {
    const response = await fetch('/api/auth/logout', {
      method: 'POST',
      headers,
      credentials: 'same-origin',
    });
    if (!response.ok)
      throw new Error('No se pudo cerrar la sesión en el servidor. Intenta de nuevo.');
  } finally {
    // Also invalidate refreshes started while the logout request was in progress.
    setAccessToken(null);
  }
}

import type { AuthResponse } from './types';

let accessToken: string | null = null;
let refreshInFlight: Promise<AuthResponse | null> | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export async function refreshSession(): Promise<AuthResponse | null> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    const response = await fetch('/api/auth/refresh', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'Humanizar' },
    });
    if (!response.ok) {
      accessToken = null;
      return null;
    }
    const result = (await response.json()) as AuthResponse;
    accessToken = result.access_token;
    return result;
  })();
  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

export async function authenticatedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const perform = () => {
    const headers = new Headers(init.headers);
    if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
    return fetch(path, { ...init, headers, credentials: 'same-origin' });
  };
  const response = await perform();
  if (response.status !== 401) return response;
  const session = await refreshSession();
  if (session) return perform();
  if (typeof window !== 'undefined') window.dispatchEvent(new Event('humanizar-session-expired'));
  return response;
}

export async function logoutSession(): Promise<void> {
  try {
    const response = await authenticatedFetch('/api/auth/logout', {
      method: 'POST',
      headers: { 'X-Requested-With': 'Humanizar' },
    });
    if (!response.ok)
      throw new Error('No se pudo cerrar la sesión en el servidor. Intenta de nuevo.');
  } finally {
    accessToken = null;
  }
}

import type {
  ChatResponse,
  DocumentList,
  Config,
  Health,
  ToolDefinition,
  ToolTrace,
  UploadResult,
  Conversation,
  User,
  AuthResponse,
  ProviderSettings,
  CustomerRequest,
} from './types';
import { consumeSse } from './sse';
import { authenticatedFetch } from './auth';

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Ocurrió un error inesperado. Intenta de nuevo.';
}

async function checkResponse(response: Response): Promise<void> {
  if (response.ok) return;
  let message = `El servidor respondió con un error (${response.status}).`;
  try {
    const data: unknown = await response.json();
    if (data && typeof data === 'object') {
      const detail = 'detail' in data ? data.detail : 'message' in data ? data.message : undefined;
      if (typeof detail === 'string') message = detail;
    }
  } catch {
    /* Keep a useful HTTP error if the response is not JSON. */
  }
  throw new Error(message);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response =
    path.startsWith('/auth/') && path !== '/auth/me'
      ? await fetch(`/api${path}`, { ...init, credentials: 'same-origin' })
      : await authenticatedFetch(`/api${path}`, init);
  await checkResponse(response);
  return (await response.json()) as T;
}

export const api = {
  authStatus: () => request<{ setup_required: boolean }>('/auth/status'),
  me: () => request<User>('/auth/me'),
  authenticate: (
    action: 'setup' | 'register' | 'login',
    input: { name?: string; email: string; password: string },
  ) =>
    request<AuthResponse>(`/auth/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    }),
  conversations: () => request<{ conversations: Conversation[] }>('/conversations'),
  deleteConversation: async (id: string) => {
    const response = await authenticatedFetch(`/api/conversations/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    });
    await checkResponse(response);
  },
  requests: () => request<{ requests: CustomerRequest[] }>('/requests'),
  adminRequests: () => request<{ requests: CustomerRequest[] }>('/admin/requests'),
  provider: () => request<ProviderSettings>('/settings/provider'),
  saveProvider: (key: string) =>
    request<ProviderSettings>('/settings/provider', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: key }),
    }),
  testProvider: () =>
    request<{ ok: boolean; message: string }>('/settings/provider/test', { method: 'POST' }),
  confirmAction: (tool: string, input: Record<string, unknown>, actionKey: string) =>
    request<ToolTrace>('/actions/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool, input, action_key: actionKey }),
    }),
  config: () => request<Config>('/config'),
  health: () => request<Health>('/health'),
  documents: () => request<DocumentList>('/documents'),
  tools: () => request<{ tools: ToolDefinition[] }>('/tools'),
  upload: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<UploadResult>('/documents', { method: 'POST', body: form });
  },
  deleteDocument: async (id: string) => {
    const response = await authenticatedFetch(`/api/documents/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    });
    await checkResponse(response);
  },
  runTool: (name: string, input: Record<string, unknown>, confirmed = false) =>
    request<ToolTrace>('/tools/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, input, confirmed }),
    }),
};

export type ChatEvent =
  | { type: 'status'; message: string }
  | { type: 'token'; text: string }
  | { type: 'tool'; trace: ToolTrace }
  | { type: 'done'; response: ChatResponse };

export async function streamChat(
  message: string,
  history: { role: 'user' | 'assistant'; content: string }[],
  sessionId: string | undefined,
  signal: AbortSignal,
  onEvent: (event: ChatEvent) => void,
): Promise<void> {
  const response = await authenticatedFetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history, ...(sessionId ? { session_id: sessionId } : {}) }),
    signal,
  });
  await checkResponse(response);
  const completion = { done: false };
  await consumeSse(response, (event) => {
    const parsed: unknown = JSON.parse(event.data);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('El servidor envió un evento de respuesta inválido.');
    }
    const data = parsed as Record<string, unknown>;
    if (event.event === 'error') {
      throw new Error(
        typeof data.message === 'string' ? data.message : 'La respuesta se interrumpió.',
      );
    }
    if (event.event === 'status' && typeof data.message === 'string') {
      onEvent({ type: 'status', message: data.message });
    }
    if (event.event === 'token' && typeof data.text === 'string') {
      onEvent({ type: 'token', text: data.text });
    }
    if (event.event === 'tool') onEvent({ type: 'tool', trace: data as unknown as ToolTrace });
    if (event.event === 'done') {
      if (
        typeof data.answer !== 'string' ||
        !Array.isArray(data.sources) ||
        !Array.isArray(data.trace)
      ) {
        throw new Error('La respuesta del servidor está incompleta.');
      }
      completion.done = true;
      onEvent({ type: 'done', response: data as unknown as ChatResponse });
    }
  });
  if (!completion.done)
    throw new Error('La conexión terminó antes de completar la respuesta. Puedes reintentar.');
}

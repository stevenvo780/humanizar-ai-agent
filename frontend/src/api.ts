import type { ChatResponse, ToolTrace } from './types';
import { consumeSse } from './sse';
import { authenticatedFetch } from './auth';
import {
  isAuthResponse,
  isAuthStatus,
  isChatResponse,
  isConfig,
  isCompanyIdentity,
  isConversationList,
  isCreatedCustomer,
  isCustomerAccountList,
  isDocumentDetail,
  isDocumentList,
  isHealth,
  isRequestList,
  isToolList,
  isToolTrace,
  isUploadResult,
  isUser,
  validate,
} from './validation';
import type { Validator } from './validation';

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Ocurrió un error inesperado. Intenta de nuevo.';
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
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
  throw new ApiError(message, response.status);
}

async function request<T>(path: string, check: Validator<T>, init?: RequestInit): Promise<T> {
  const response =
    path.startsWith('/auth/') && path !== '/auth/me'
      ? await fetch(`/api${path}`, { ...init, credentials: 'same-origin' })
      : await authenticatedFetch(`/api${path}`, init);
  await checkResponse(response);
  return validate(await response.json(), check);
}

export const api = {
  authStatus: () => request('/auth/status', isAuthStatus),
  me: () => request('/auth/me', isUser),
  authenticate: (
    action: 'setup' | 'register' | 'login',
    input: { name?: string; email: string; password: string },
  ) =>
    request(`/auth/${action}`, isAuthResponse, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    }),
  conversations: () => request('/conversations', isConversationList),
  deleteConversation: async (id: string) => {
    const response = await authenticatedFetch(`/api/conversations/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    });
    await checkResponse(response);
  },
  requests: () => request('/requests', isRequestList),
  adminRequests: () => request('/admin/requests', isRequestList),
  customers: (offset = 0, limit = 25) =>
    request(`/admin/customers?limit=${limit}&offset=${offset}`, isCustomerAccountList),
  createCustomer: (input: { name: string; email: string; password: string }) =>
    request('/admin/customers', isCreatedCustomer, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    }),
  confirmAction: (tool: string, input: Record<string, unknown>, actionKey: string) =>
    request('/actions/confirm', isToolTrace, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool, input, action_key: actionKey }),
    }),
  config: () => request('/config', isConfig),
  company: () => request('/company', isCompanyIdentity),
  health: () => request('/health', isHealth),
  documents: () => request('/documents', isDocumentList),
  document: async (id: string, signal: AbortSignal) => {
    const detail = await request(`/documents/${encodeURIComponent(id)}`, isDocumentDetail, {
      signal,
    });
    if (detail.id !== id)
      throw new Error('El servidor devolvió un documento diferente al solicitado.');
    return detail;
  },
  tools: () => request('/tools', isToolList),
  upload: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request('/documents', isUploadResult, { method: 'POST', body: form });
  },
  deleteDocument: async (id: string) => {
    const response = await authenticatedFetch(`/api/documents/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    });
    await checkResponse(response);
  },
  runTool: (name: string, input: Record<string, unknown>, confirmed = false) =>
    request('/tools/run', isToolTrace, {
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
    if (!['status', 'token', 'tool', 'done', 'error'].includes(event.event)) return;
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
    if (event.event === 'status') {
      if (typeof data.message !== 'string')
        throw new Error('El servidor envió un estado de respuesta inválido.');
      onEvent({ type: 'status', message: data.message });
    }
    if (event.event === 'token') {
      if (typeof data.text !== 'string')
        throw new Error('El servidor envió un fragmento de respuesta inválido.');
      onEvent({ type: 'token', text: data.text });
    }
    if (event.event === 'tool') onEvent({ type: 'tool', trace: validate(data, isToolTrace) });
    if (event.event === 'done') {
      if (!isChatResponse(data)) {
        throw new Error('La respuesta del servidor está incompleta.');
      }
      completion.done = true;
      onEvent({ type: 'done', response: data });
      return false;
    }
  });
  if (!completion.done)
    throw new Error('La conexión terminó antes de completar la respuesta. Puedes reintentar.');
}

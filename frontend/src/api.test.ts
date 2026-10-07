import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, streamChat } from './api';

afterEach(() => vi.unstubAllGlobals());

function reply(body: string): void {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValue(new Response(body, { headers: { 'Content-Type': 'text/event-stream' } })),
  );
}

describe('chat stream lifecycle', () => {
  it('delivers status/token/final answer and sends sanitized history to the API', async () => {
    const response = {
      answer: 'Hola',
      sources: [],
      trace: [],
      mode: 'demo',
      model: 'demo',
      usage: { input_tokens: 0, output_tokens: 0 },
      session_id: 'session',
    };
    reply(
      `event: status\ndata: {"message":"Buscando"}\n\nevent: token\ndata: {"text":"Hola"}\n\nevent: done\ndata: ${JSON.stringify(response)}\n\n`,
    );
    const events: unknown[] = [];
    const signal = new AbortController().signal;
    await streamChat('Ayuda', [{ role: 'user', content: 'Contexto' }], 'session', signal, (event) =>
      events.push(event),
    );
    expect(events).toEqual([
      { type: 'status', message: 'Buscando' },
      { type: 'token', text: 'Hola' },
      { type: 'done', response },
    ]);
    const fetchMock = vi.mocked(fetch);
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/chat/stream',
      expect.objectContaining({
        method: 'POST',
        signal,
        body: JSON.stringify({
          message: 'Ayuda',
          history: [{ role: 'user', content: 'Contexto' }],
          session_id: 'session',
        }),
      }),
    );
  });

  it('rejects an abruptly ended response instead of treating partial tokens as success', async () => {
    reply('event: token\ndata: {"text":"parcial"}\n\n');
    await expect(
      streamChat('hola', [], undefined, new AbortController().signal, () => undefined),
    ).rejects.toThrow('antes de completar');
  });

  it('surfaces an SSE backend error with its actual message', async () => {
    reply('event: error\ndata: {"code":"provider_error","message":"Servicio no disponible"}\n\n');
    await expect(
      streamChat('hola', [], undefined, new AbortController().signal, () => undefined),
    ).rejects.toThrow('Servicio no disponible');
  });

  it('rejects a malformed done event without reporting success', async () => {
    reply('event: done\ndata: {"answer":"hola"}\n\n');
    await expect(
      streamChat('hola', [], undefined, new AbortController().signal, () => undefined),
    ).rejects.toThrow('incompleta');
  });

  it('reports API error detail before trying to parse SSE', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(new Response('{"detail":"Mensaje demasiado largo"}', { status: 413 })),
    );
    await expect(
      streamChat('hola', [], undefined, new AbortController().signal, () => undefined),
    ).rejects.toThrow('Mensaje demasiado largo');
  });

  it('rejects invalid nested source data before passing a done event to the UI', async () => {
    reply(
      `event: done\ndata: ${JSON.stringify({
        answer: 'Hola',
        sources: [{ document_name: { unexpected: true } }],
        trace: [],
        mode: 'demo',
        model: 'demo',
        usage: { input_tokens: 0, output_tokens: 0 },
        session_id: 'session',
      })}\n\n`,
    );
    const onEvent = vi.fn();
    await expect(
      streamChat('hola', [], undefined, new AbortController().signal, onEvent),
    ).rejects.toThrow('incompleta');
    expect(onEvent).not.toHaveBeenCalled();
  });

  it('rejects invalid tool traces before they can reach React', async () => {
    reply('event: tool\ndata: {"id":"tool","input":null}\n\n');
    const onEvent = vi.fn();
    await expect(
      streamChat('hola', [], undefined, new AbortController().signal, onEvent),
    ).rejects.toThrow('datos inválidos');
    expect(onEvent).not.toHaveBeenCalled();
  });

  it('finishes on done and cancels a still-open stream without delivering trailing tokens', async () => {
    const done = {
      answer: 'Respuesta final',
      sources: [],
      trace: [],
      mode: 'demo',
      model: 'demo',
      usage: { input_tokens: 0, output_tokens: 0 },
      session_id: 'session',
    };
    const cancel = vi.fn();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode(
            `event: done\ndata: ${JSON.stringify(done)}\n\nevent: token\ndata: {"text":"extra"}\n\n`,
          ),
        );
      },
      cancel,
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(stream)));
    const events: unknown[] = [];
    await streamChat('hola', [], undefined, new AbortController().signal, (event) => {
      events.push(event);
    });
    expect(events).toEqual([{ type: 'done', response: done }]);
    expect(cancel).toHaveBeenCalledOnce();
  });

  it('rejects corrupted database history instead of loading it into the conversation UI', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('{"conversations":[{"id":"chat","messages":null}]}')),
    );
    await expect(api.conversations()).rejects.toThrow('datos inválidos');
  });

  it('rejects an authentication response with an unknown role', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            access_token: 'test-access',
            token_type: 'bearer',
            user: { id: 'test-user', name: 'Test', email: 'test@example.invalid', role: 'other' },
          }),
        ),
      ),
    );
    await expect(
      api.authenticate('login', { email: 'test@example.invalid', password: 'test-only' }),
    ).rejects.toThrow('datos inválidos');
  });
});

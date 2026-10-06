import { describe, expect, it } from 'vitest';
import { consumeSse, SseParser } from './sse';

describe('SSE stream framing', () => {
  it('buffers fragmented CRLF frames and resets the event type', () => {
    const parser = new SseParser();
    expect(parser.feed('event: token\r')).toEqual([]);
    expect(parser.feed('\ndata: {"text":"hola"}\r\n\r')).toEqual([]);
    expect(parser.feed('\ndata: second\n\n')).toEqual([
      { event: 'token', data: '{"text":"hola"}' },
      { event: 'message', data: 'second' },
    ]);
  });

  it('joins multiline data, ignores heartbeats and flushes a final frame', () => {
    const parser = new SseParser();
    expect(parser.feed(': heartbeat\nevent: done\ndata: first\ndata: second')).toEqual([]);
    expect(parser.finish()).toEqual([{ event: 'done', data: 'first\nsecond' }]);
    expect(parser.finish()).toEqual([]);
  });

  it('preserves fragmented UTF-8 across single-byte network chunks', async () => {
    const bytes = new TextEncoder().encode('event: token\ndata: {"text":"¡Diseño ✨!"}\n\n');
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        for (const byte of bytes) controller.enqueue(new Uint8Array([byte]));
        controller.close();
      },
    });
    const events: unknown[] = [];
    await consumeSse(new Response(stream), (event) => events.push(event));
    expect(events).toEqual([{ event: 'token', data: '{"text":"¡Diseño ✨!"}' }]);
  });

  it('propagates reader errors instead of completing silently', async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.error(new Error('connection lost'));
      },
    });
    await expect(consumeSse(new Response(stream), () => undefined)).rejects.toThrow(
      'connection lost',
    );
  });
});

export interface SseEvent {
  event: string;
  data: string;
}

/** Buffers partial lines; SSE data fields may span several lines and network chunks. */
export class SseParser {
  private buffer = '';
  private eventName = 'message';
  private data: string[] = [];

  feed(chunk: string): SseEvent[] {
    this.buffer += chunk;
    const events: SseEvent[] = [];
    let newline: number;
    while ((newline = this.buffer.indexOf('\n')) >= 0) {
      const line = this.buffer.slice(0, newline).replace(/\r$/, '');
      this.buffer = this.buffer.slice(newline + 1);
      this.line(line, events);
    }
    return events;
  }

  finish(): SseEvent[] {
    const events: SseEvent[] = [];
    if (this.buffer) this.line(this.buffer.replace(/\r$/, ''), events);
    this.buffer = '';
    this.line('', events);
    return events;
  }

  private line(line: string, events: SseEvent[]): void {
    if (!line) {
      if (this.data.length > 0) {
        events.push({ event: this.eventName, data: this.data.join('\n') });
      }
      this.eventName = 'message';
      this.data = [];
      return;
    }
    if (line.startsWith(':')) return;
    const colon = line.indexOf(':');
    const field = colon < 0 ? line : line.slice(0, colon);
    const value = colon < 0 ? '' : line.slice(colon + 1).replace(/^ /, '');
    if (field === 'event') this.eventName = value;
    if (field === 'data') this.data.push(value);
  }
}

export async function consumeSse(
  response: Response,
  // Returning false marks a terminal event and closes the reader immediately.
  onEvent: (event: SseEvent) => unknown,
): Promise<void> {
  if (!response.body) throw new Error('El servidor no devolvió un flujo de respuesta.');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const parser = new SseParser();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const event of parser.feed(decoder.decode(value, { stream: true }))) {
        if (onEvent(event) === false) return;
      }
    }
    for (const event of parser.feed(decoder.decode())) {
      if (onEvent(event) === false) return;
    }
    for (const event of parser.finish()) {
      if (onEvent(event) === false) return;
    }
  } finally {
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}

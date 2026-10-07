import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { ChatAnnouncement, completedChatAnnouncement } from './ChatAnnouncement';

describe('completed response accessibility', () => {
  it('keeps an initially empty atomic live region mounted for future completion', () => {
    const html = renderToStaticMarkup(createElement(ChatAnnouncement, { message: '' }));
    expect(html).toContain('role="status"');
    expect(html).toContain('aria-live="polite"');
    expect(html).toContain('aria-atomic="true"');
    expect(html).not.toContain('aria-hidden');
    expect(html).not.toContain('tabindex');
  });

  it('announces the final answer as text without executing returned HTML', () => {
    const message = completedChatAnnouncement(
      {
        answer: '<script>unsafe()</script> Respuesta final.',
        sources: [],
        trace: [],
        model: 'demo',
        mode: 'demo',
        usage: { input_tokens: 0, output_tokens: 0 },
        session_id: 'synthetic-session',
      },
      'Asistente Ejemplo',
    );
    const html = renderToStaticMarkup(createElement(ChatAnnouncement, { message }));
    expect(html).toContain('Respuesta de Asistente Ejemplo completada.');
    expect(html).toContain('Respuesta final.');
    expect(html).not.toContain('<script>');
  });
});

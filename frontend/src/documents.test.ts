import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from './api';
import { isDocumentDetail, isHealth } from './validation';

const detail = {
  id: 'doc-example',
  name: 'example.md',
  chunks: 2,
  characters: 24,
  created_at: '2026-10-07T00:00:00Z',
  content: '# Example\n\nDocument text.',
  reconstructed: false,
};

afterEach(() => vi.unstubAllGlobals());

describe('document content contract', () => {
  it('accepts original, reconstructed and empty document content', () => {
    expect(isDocumentDetail(detail)).toBe(true);
    expect(isDocumentDetail({ ...detail, reconstructed: true })).toBe(true);
    expect(isDocumentDetail({ ...detail, content: '' })).toBe(true);
  });

  it.each([
    { content: null },
    { content: 42 },
    { reconstructed: undefined },
    { reconstructed: 'false' },
    { chunks: -1 },
    { characters: 1.5 },
    { created_at: 'not a date' },
    { id: '' },
    { name: '' },
  ])('rejects invalid content or metadata: %j', (invalid) => {
    expect(isDocumentDetail({ ...detail, ...invalid })).toBe(false);
  });

  it('keeps the reading capability optional for older backends and requires a boolean', () => {
    const health = {
      status: 'ok',
      mode: 'demo',
      model: 'demo',
      embedding: 'lexical',
      tools: { sandbox: false, mcp: true },
    };
    expect(isHealth(health)).toBe(true);
    expect(isHealth({ ...health, features: { customer_management: true } })).toBe(true);
    expect(
      isHealth({ ...health, features: { customer_management: true, document_reading: true } }),
    ).toBe(true);
    expect(
      isHealth({ ...health, features: { customer_management: false, document_reading: false } }),
    ).toBe(true);
    expect(
      isHealth({ ...health, features: { customer_management: true, document_reading: 'true' } }),
    ).toBe(false);
  });
});

describe('document reading requests', () => {
  it('encodes the document id and forwards cancellation with same-origin credentials', async () => {
    const id = 'doc/with?reserved#characters';
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...detail, id })));
    vi.stubGlobal('fetch', fetchMock);
    const controller = new AbortController();
    await expect(api.document(id, controller.signal)).resolves.toMatchObject({ id });
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/documents/doc%2Fwith%3Freserved%23characters',
      expect.objectContaining({ signal: controller.signal, credentials: 'same-origin' }),
    );
  });

  it('rejects mismatched ids rather than displaying another document', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(detail))));
    await expect(api.document('another-id', new AbortController().signal)).rejects.toThrow(
      'documento diferente',
    );
  });

  it('rejects malformed JSON content before it reaches React', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(new Response(JSON.stringify({ ...detail, content: { nested: true } }))),
    );
    await expect(api.document(detail.id, new AbortController().signal)).rejects.toThrow(
      'datos inválidos',
    );
  });

  it('preserves a 404 status and server error instead of fabricating document content', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(new Response('{"detail":"Documento no disponible"}', { status: 404 })),
    );
    await expect(api.document(detail.id, new AbortController().signal)).rejects.toEqual(
      new ApiError('Documento no disponible', 404),
    );
  });

  it('propagates an abort without converting it into a successful response', async () => {
    const controller = new AbortController();
    vi.stubGlobal(
      'fetch',
      vi.fn((_path: RequestInfo | URL, init?: RequestInit) => {
        return new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener(
            'abort',
            () => reject(new DOMException('Cancelled', 'AbortError')),
            { once: true },
          );
        });
      }),
    );
    const pending = api.document(detail.id, controller.signal);
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: 'AbortError' });
  });
});

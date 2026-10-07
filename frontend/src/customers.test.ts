import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from './api';
import { setAccessToken } from './auth';
import { requestKindLabel } from './AccountPanels';
import {
  isConfig,
  isCustomerAccount,
  isCustomerAccountList,
  isHealth,
  isRequestList,
} from './validation';

const customer = {
  id: 'customer-test',
  name: 'Cliente de prueba',
  email: 'customer@example.test',
  role: 'customer',
  created_at: '2026-10-07T00:00:00Z',
};

afterEach(() => {
  setAccessToken(null);
  vi.unstubAllGlobals();
});

describe('admin customer contract', () => {
  it('accepts older health responses while validating the new capability explicitly', () => {
    const health = {
      status: 'ok',
      mode: 'demo',
      model: 'demo',
      embedding: 'hash',
      tools: { sandbox: false, mcp: false },
    };
    expect(isHealth(health)).toBe(true);
    expect(isHealth({ ...health, features: { customer_management: true } })).toBe(true);
    expect(isHealth({ ...health, features: { customer_management: false } })).toBe(true);
    expect(isHealth({ ...health, features: { customer_management: 'yes' } })).toBe(false);
  });
  it('loads bounded customer pages using the administrator token', async () => {
    setAccessToken('synthetic-admin-token');
    const result = { customers: [customer], total: 26, limit: 25, offset: 25 };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(result)));
    vi.stubGlobal('fetch', fetchMock);
    expect(await api.customers(25)).toEqual(result);
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe('/api/admin/customers?limit=25&offset=25');
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer synthetic-admin-token');
  });

  it('creates a customer without replacing the administrator access token', async () => {
    setAccessToken('synthetic-admin-token');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ customer }), { status: 201 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ customers: [customer], total: 1, limit: 25, offset: 0 })),
      );
    vi.stubGlobal('fetch', fetchMock);
    expect(
      await api.createCustomer({
        name: customer.name,
        email: customer.email,
        password: 'test-only-password',
      }),
    ).toEqual({ customer });
    await api.customers();
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe('/api/admin/customers');
    expect(init.method).toBe('POST');
    if (typeof init.body !== 'string') throw new Error('Expected a JSON request body');
    const body: unknown = JSON.parse(init.body);
    expect(body).not.toHaveProperty('role');
    const [, nextInit] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(new Headers(nextInit.headers).get('Authorization')).toBe('Bearer synthetic-admin-token');
  });

  it('rejects administrator entries, invalid dates and broken pagination in customer responses', () => {
    expect(isCustomerAccount(customer)).toBe(true);
    expect(isCustomerAccount({ ...customer, role: 'admin' })).toBe(false);
    expect(isCustomerAccount({ ...customer, created_at: 'invalid' })).toBe(false);
    const page = { customers: [customer], total: 1, limit: 25, offset: 0 };
    expect(isCustomerAccountList(page)).toBe(true);
    expect(isCustomerAccountList({ ...page, limit: 101 })).toBe(false);
    expect(isCustomerAccountList({ ...page, offset: -1 })).toBe(false);
    expect(isCustomerAccountList({ ...page, total: 0 })).toBe(false);
  });

  it('surfaces duplicate-account errors instead of reporting a successful creation', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ detail: 'No se pudo crear la cuenta.' }), { status: 409 }),
        ),
    );
    await expect(
      api.createCustomer({
        name: customer.name,
        email: customer.email,
        password: 'test-only-password',
      }),
    ).rejects.toThrow('No se pudo crear la cuenta.');
  });
});

describe('forward-compatible response contract', () => {
  const health = {
    status: 'ok',
    mode: 'demo',
    model: 'demo',
    embedding: 'hash',
    tools: { sandbox: false, mcp: false },
  };
  const config = {
    company_name: 'Empresa Ejemplo',
    company_description: 'Descripción sintética.',
    assistant_name: 'Asistente Ejemplo',
    model: 'modelo-nuevo',
    mode: 'demo',
    embedding: 'hash',
    max_upload_mb: 20,
  };

  it('keeps health and config usable when the backend adds an assistant mode', () => {
    expect(isHealth({ ...health, mode: 'openai-compatible' })).toBe(true);
    expect(isConfig({ ...config, mode: 'openai-compatible' })).toBe(true);
    expect(isHealth({ ...health, mode: '' })).toBe(false);
    expect(isConfig({ ...config, mode: 4 })).toBe(false);
  });

  it('lists requests of an unknown kind with a generic label instead of rejecting the list', () => {
    const request = {
      id: 'request-test',
      status: 'received',
      created_at: '2026-10-07T00:00:00Z',
      details: { topic: 'Sintético' },
    };
    const list = {
      requests: [
        { ...request, kind: 'demo' },
        { ...request, id: 'request-new', kind: 'callback' },
      ],
    };
    expect(isRequestList(list)).toBe(true);
    expect(isRequestList({ requests: [{ ...request, kind: '' }] })).toBe(false);
    expect(isRequestList({ requests: [{ ...request, kind: null }] })).toBe(false);
    expect(requestKindLabel('demo')).toBe('Solicitud de demostración');
    expect(requestKindLabel('support')).toBe('Ticket de soporte');
    expect(requestKindLabel('callback')).toBe('Solicitud');
  });

  it('keeps account roles strict because they gate administrator features', () => {
    expect(isCustomerAccount({ ...customer, role: 'owner' })).toBe(false);
  });
});

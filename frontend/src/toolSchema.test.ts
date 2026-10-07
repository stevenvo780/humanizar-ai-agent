import { afterEach, describe, expect, it, vi } from 'vitest';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { api } from './api';
import { toolFormModel, toolInput, toolLabel } from './toolSchema';
import { ToolInputForm } from './ToolInputForm';
import { isToolList } from './validation';
import type { ToolDefinition } from './types';

afterEach(() => vi.unstubAllGlobals());

const orderTool: ToolDefinition = {
  name: 'lookup_order',
  description: 'Consulta sintética de un pedido.',
  enabled: true,
  input_schema: {
    type: 'object',
    properties: {
      order_id: { type: 'string', title: 'Número de pedido', minLength: 1, maxLength: 30 },
    },
    required: ['order_id'],
    additionalProperties: false,
  },
};

describe('tool forms from published schemas', () => {
  it('sends a newly registered order_id field instead of an empty object', async () => {
    const model = toolFormModel(orderTool);
    expect(() => toolInput(model, {}, '')).toThrow('Número de pedido');
    const input = toolInput(model, { order_id: 'ORDER-EXAMPLE' }, '');
    const mock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'synthetic-trace',
          tool: orderTool.name,
          input,
          output: 'Resultado sintético',
          status: 'completed',
          duration_ms: 1,
        }),
      ),
    );
    vi.stubGlobal('fetch', mock);
    await api.runTool(orderTool.name, input);
    expect(mock).toHaveBeenCalledWith(
      '/api/tools/run',
      expect.objectContaining({
        body: JSON.stringify({
          name: 'lookup_order',
          input: { order_id: 'ORDER-EXAMPLE' },
          confirmed: false,
        }),
      }),
    );
  });

  it('renders a required, labelled field for an unknown tool', () => {
    const html = renderToStaticMarkup(
      createElement(ToolInputForm, {
        tool: orderTool,
        online: true,
        health: null,
        running: false,
        onRunning: () => undefined,
      }),
    );
    expect(html).toContain('Número de pedido');
    expect(html).toMatch(
      /<label for="([^"]+)">Número de pedido<\/label><input id="\1"[^>]+required=""/,
    );
    expect(html).not.toContain('Consulta de documentación');
  });

  it('converts enums, numbers, integers and false without dropping values', () => {
    const tool: ToolDefinition = {
      ...orderTool,
      input_schema: {
        type: 'object',
        properties: {
          priority: { type: 'string', enum: ['low', 'high'] },
          quantity: { type: 'integer', minimum: 0, maximum: 10 },
          amount: { type: 'number' },
          notify: { type: 'boolean' },
          note: { type: 'string' },
        },
        required: ['priority', 'quantity', 'amount', 'notify'],
        additionalProperties: false,
      },
    };
    const model = toolFormModel(tool);
    expect(
      toolInput(
        model,
        { priority: 'low', quantity: '0', amount: '2.5', notify: 'false', note: '' },
        '',
      ),
    ).toEqual({ priority: 'low', quantity: 0, amount: 2.5, notify: false });
    expect(() =>
      toolInput(model, { priority: 'other', quantity: '0', amount: '2', notify: 'true' }, ''),
    ).toThrow('opción válida');
    expect(() =>
      toolInput(model, { priority: 'low', quantity: '1.5', amount: '2', notify: 'true' }, ''),
    ).toThrow('entero');
    expect(() =>
      toolInput(model, { priority: 'low', quantity: '11', amount: '2', notify: 'true' }, ''),
    ).toThrow('intervalo');
    expect(() =>
      toolInput(model, { priority: 'low', quantity: '1', amount: 'Infinity', notify: 'true' }, ''),
    ).toThrow('número válido');
  });

  it.each([
    { type: 'object', properties: { address: { type: 'object', properties: {} } } },
    { type: 'object', properties: { lines: { type: 'array', items: { type: 'string' } } } },
    { type: 'object', properties: { id: { type: 'string', pattern: '^ORD' } } },
    { type: 'object', properties: { id: { type: 'string' } }, required: ['missing'] },
    { type: 'object', properties: { id: { type: 'string', enum: [1] } } },
    { type: 'object', properties: { id: { type: 'string', minLength: 10, maxLength: 1 } } },
    { type: 'object', properties: {}, oneOf: [] },
  ])('blocks unsupported or malformed schemas explicitly: %j', (input_schema) => {
    const model = toolFormModel({ ...orderTool, input_schema });
    expect(model.kind).toBe('unsupported');
    expect(() => toolInput(model, {}, '{}')).toThrow('todavía no admite');
  });

  it('requires explicit valid JSON if an older API publishes no schema for a new tool', () => {
    const model = toolFormModel({ name: 'new_tool', description: 'Nueva', enabled: true });
    expect(model.kind).toBe('json');
    expect(() => toolInput(model, {}, '')).toThrow('JSON válido');
    expect(() => toolInput(model, {}, '[]')).toThrow('objeto JSON');
    expect(toolInput(model, {}, '{"order_id":"SYNTHETIC"}')).toEqual({ order_id: 'SYNTHETIC' });
  });

  it('preserves old terminal presets and business confirmation fields', () => {
    const terminal = toolFormModel({ name: 'terminal', description: '', enabled: true });
    expect(toolInput(terminal, { command: 'pwd' }, '')).toEqual({ command: 'pwd' });
    expect(() => toolInput(terminal, { command: 'rm -rf /' }, '')).toThrow('opción válida');
    const demo = toolFormModel({ name: 'create_demo_request', description: '', enabled: true });
    expect(() => toolInput(demo, {}, '')).toThrow('Nombre');
    const empty = toolFormModel({ name: 'mcp_company_info', description: '', enabled: true });
    expect(toolInput(empty, {}, '')).toEqual({});
  });

  it('does not confuse inherited object properties with known tool names', () => {
    expect(toolFormModel({ name: '__proto__', description: '', enabled: true }).kind).toBe('json');
    expect(typeof toolLabel('__proto__')).toBe('string');
  });

  it.each(['constructor', '__proto__', 'toString'])(
    'handles parameter key %s as an own property',
    async (name) => {
      const prototype = Object.getOwnPropertyDescriptors(Object.prototype);
      const optionalTool: ToolDefinition = {
        ...orderTool,
        input_schema: {
          type: 'object',
          properties: { [name]: { type: 'string' } },
          required: [],
          additionalProperties: false,
        },
      };
      expect(toolInput(toolFormModel(optionalTool), {}, '')).toEqual({});
      const html = renderToStaticMarkup(
        createElement(ToolInputForm, {
          tool: optionalTool,
          online: true,
          health: null,
          running: false,
          onRunning: () => undefined,
        }),
      );
      expect(html).toContain('value=""');
      const requiredTool: ToolDefinition = {
        ...optionalTool,
        input_schema: { ...optionalTool.input_schema, required: [name] },
      };
      const model = toolFormModel(requiredTool);
      expect(() => toolInput(model, {}, '')).toThrow(/^Completa /);
      const input = toolInput(model, Object.fromEntries([[name, 'SYNTHETIC-VALUE']]), '');
      expect(Object.hasOwn(input, name)).toBe(true);
      expect(Object.keys(input)).toEqual([name]);
      expect(JSON.stringify(input)).toBe(JSON.stringify({ [name]: 'SYNTHETIC-VALUE' }));
      const mock = vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            id: 'synthetic-trace',
            tool: orderTool.name,
            input,
            output: 'Resultado sintético',
            status: 'completed',
            duration_ms: 1,
          }),
        ),
      );
      vi.stubGlobal('fetch', mock);
      await api.runTool(orderTool.name, input);
      expect(mock).toHaveBeenCalledWith(
        '/api/tools/run',
        expect.objectContaining({
          body: JSON.stringify({
            name: orderTool.name,
            input: { [name]: 'SYNTHETIC-VALUE' },
            confirmed: false,
          }),
        }),
      );
      expect(Object.getOwnPropertyDescriptors(Object.prototype)).toEqual(prototype);
    },
  );

  it('accepts old catalogs and rejects non-object input schemas', async () => {
    expect(isToolList({ tools: [{ name: 'old', description: '', enabled: true }] })).toBe(true);
    expect(isToolList({ tools: [orderTool] })).toBe(true);
    expect(isToolList({ tools: [{ ...orderTool, input_schema: [] }] })).toBe(false);
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ tools: [{ ...orderTool, input_schema: 'unexpected' }] })),
        ),
    );
    await expect(api.tools()).rejects.toThrow('datos inválidos');
  });
});

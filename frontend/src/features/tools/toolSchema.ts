import type { ToolDefinition } from '../../shared/api/types';
import { isRecord } from '../../shared/api/validation';

type Primitive = string | number | boolean;
export interface ToolField {
  name: string;
  label: string;
  description: string;
  type: 'string' | 'number' | 'integer' | 'boolean';
  required: boolean;
  choices: Primitive[] | null;
  minLength: number | null;
  maxLength: number | null;
  minimum: number | null;
  maximum: number | null;
}
export type ToolFormModel =
  | { kind: 'fields'; fields: ToolField[] }
  | { kind: 'json' }
  | { kind: 'unsupported'; message: string };

const fieldLabels: Record<string, string> = {
  expression: 'Expresión matemática',
  query: 'Consulta de documentación',
  process: 'Proceso que necesitas resolver',
  command: 'Comando permitido',
  name: 'Nombre del contacto',
  email: 'Correo del contacto',
  company: 'Empresa',
  interest: 'Producto o servicio de interés',
  needs: 'Necesidad o proceso',
  subject: 'Asunto',
  description: 'Descripción',
};
const toolLabels: Record<string, string> = {
  search_knowledge: 'Buscar documentación',
  calculate: 'Calculadora',
  terminal: 'Terminal aislada',
  mcp_company_info: 'Información de empresa · MCP',
  recommend_product: 'Recomendar producto',
  create_demo_request: 'Solicitar demostración',
  create_support_ticket: 'Crear ticket de soporte',
  list_my_requests: 'Consultar mis solicitudes',
};
export function toolLabel(name: string): string {
  return (
    (Object.hasOwn(toolLabels, name) ? toolLabels[name] : undefined) ?? name.replaceAll('_', ' ')
  );
}

function objectSchema(
  properties: Record<string, unknown>,
  required = Object.keys(properties),
): Record<string, unknown> {
  return { type: 'object', properties, required, additionalProperties: false };
}
const legacySchemas: Record<string, Record<string, unknown>> = {
  calculate: objectSchema({ expression: { type: 'string', maxLength: 200 } }),
  search_knowledge: objectSchema({ query: { type: 'string', maxLength: 1000 } }),
  recommend_product: objectSchema({ process: { type: 'string', minLength: 1, maxLength: 1000 } }),
  terminal: objectSchema({
    command: { type: 'string', enum: ['pwd', 'ls', 'date', 'python --version', 'wc'] },
  }),
  mcp_company_info: objectSchema({}),
  list_my_requests: objectSchema({}),
  create_demo_request: objectSchema({
    name: { type: 'string', minLength: 1, maxLength: 120 },
    email: { type: 'string', minLength: 1, maxLength: 254 },
    company: { type: 'string', minLength: 1, maxLength: 160 },
    interest: { type: 'string', minLength: 1, maxLength: 200 },
    needs: { type: 'string', minLength: 1, maxLength: 2000 },
  }),
  create_support_ticket: objectSchema({
    subject: { type: 'string', minLength: 1, maxLength: 160 },
    description: { type: 'string', minLength: 1, maxLength: 2000 },
  }),
};
const unsupported: ToolFormModel = {
  kind: 'unsupported',
  message:
    'Este esquema contiene campos o reglas que el formulario todavía no admite. No se ejecutará con parámetros incompletos. Consulta el esquema para adaptar esta herramienta.',
};
const rootKeys = new Set([
  'type',
  'properties',
  'required',
  'additionalProperties',
  'title',
  'description',
  '$schema',
]);
const fieldKeys = new Set([
  'type',
  'title',
  'description',
  'enum',
  'minLength',
  'maxLength',
  'minimum',
  'maximum',
]);
const count = (value: unknown): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
const finite = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value);

export function toolFormModel(tool: ToolDefinition): ToolFormModel {
  const schema =
    tool.input_schema ??
    (Object.hasOwn(legacySchemas, tool.name) ? legacySchemas[tool.name] : undefined);
  if (!schema) return { kind: 'json' };
  if (
    schema.type !== 'object' ||
    !isRecord(schema.properties) ||
    Object.keys(schema).some((key) => !rootKeys.has(key)) ||
    (schema.additionalProperties !== undefined && typeof schema.additionalProperties !== 'boolean')
  )
    return unsupported;
  const required = schema.required ?? [];
  const properties = schema.properties;
  if (
    !Array.isArray(required) ||
    !required.every((name: unknown) => typeof name === 'string' && Object.hasOwn(properties, name))
  )
    return unsupported;
  const fields: ToolField[] = [];
  for (const [name, property] of Object.entries(properties)) {
    if (!isRecord(property) || Object.keys(property).some((key) => !fieldKeys.has(key)))
      return unsupported;
    const type = property.type;
    if (type !== 'string' && type !== 'number' && type !== 'integer' && type !== 'boolean')
      return unsupported;
    if (
      (property.title !== undefined && typeof property.title !== 'string') ||
      (property.description !== undefined && typeof property.description !== 'string')
    )
      return unsupported;
    if (
      (property.minLength !== undefined && (type !== 'string' || !count(property.minLength))) ||
      (property.maxLength !== undefined && (type !== 'string' || !count(property.maxLength))) ||
      (property.minimum !== undefined &&
        ((type !== 'number' && type !== 'integer') || !finite(property.minimum))) ||
      (property.maximum !== undefined &&
        ((type !== 'number' && type !== 'integer') || !finite(property.maximum)))
    )
      return unsupported;
    const choices = property.enum;
    if (
      choices !== undefined &&
      (!Array.isArray(choices) ||
        !choices.length ||
        !choices.every((value: unknown) =>
          type === 'string'
            ? typeof value === 'string' && value.length > 0
            : type === 'boolean'
              ? typeof value === 'boolean'
              : finite(value) && (type !== 'integer' || Number.isSafeInteger(value)),
        ))
    )
      return unsupported;
    const minLength = count(property.minLength) ? property.minLength : null;
    const maxLength = count(property.maxLength) ? property.maxLength : null;
    const minimum = finite(property.minimum) ? property.minimum : null;
    const maximum = finite(property.maximum) ? property.maximum : null;
    if (
      (minLength !== null && maxLength !== null && minLength > maxLength) ||
      (minimum !== null && maximum !== null && minimum > maximum)
    )
      return unsupported;
    fields.push({
      name,
      label:
        typeof property.title === 'string'
          ? property.title
          : ((Object.hasOwn(fieldLabels, name) ? fieldLabels[name] : undefined) ??
            name.replaceAll('_', ' ')),
      description: typeof property.description === 'string' ? property.description : '',
      type,
      required: required.includes(name),
      choices: Array.isArray(choices)
        ? choices.filter(
            (value: unknown): value is Primitive =>
              typeof value === 'string' || typeof value === 'boolean' || finite(value),
          )
        : null,
      minLength,
      maxLength,
      minimum,
      maximum,
    });
  }
  return { kind: 'fields', fields };
}

export function toolInput(
  model: ToolFormModel,
  values: Record<string, string>,
  json: string,
): Record<string, unknown> {
  if (model.kind === 'unsupported') throw new Error(model.message);
  if (model.kind === 'json') {
    let parsed: unknown;
    try {
      parsed = JSON.parse(json);
    } catch {
      throw new Error('Introduce un objeto JSON válido para los parámetros de la herramienta.');
    }
    if (!isRecord(parsed))
      throw new Error('Los parámetros deben ser un objeto JSON, no una lista ni un valor simple.');
    return parsed;
  }
  const entries: [string, Primitive][] = [];
  for (const field of model.fields) {
    const raw = (Object.hasOwn(values, field.name) ? values[field.name] : undefined) ?? '';
    if (!raw.trim()) {
      if (field.required) throw new Error(`Completa ${field.label}.`);
      continue;
    }
    let value: Primitive = raw;
    if (field.type === 'number' || field.type === 'integer') {
      value = Number(raw);
      if (!Number.isFinite(value) || (field.type === 'integer' && !Number.isSafeInteger(value)))
        throw new Error(
          `${field.label} debe ser un número válido${field.type === 'integer' ? ' entero' : ''}.`,
        );
      if (
        (field.minimum !== null && value < field.minimum) ||
        (field.maximum !== null && value > field.maximum)
      )
        throw new Error(`${field.label} está fuera del intervalo permitido.`);
    } else if (field.type === 'boolean') {
      if (raw !== 'true' && raw !== 'false')
        throw new Error(`Selecciona una opción válida para ${field.label}.`);
      value = raw === 'true';
    } else {
      const length = Array.from(value).length;
      if (
        (field.minLength !== null && length < field.minLength) ||
        (field.maxLength !== null && length > field.maxLength)
      )
        throw new Error(`${field.label} no cumple la longitud permitida.`);
    }
    if (field.choices && !field.choices.includes(value))
      throw new Error(`Selecciona una opción válida para ${field.label}.`);
    entries.push([field.name, value]);
  }
  return Object.fromEntries(entries);
}

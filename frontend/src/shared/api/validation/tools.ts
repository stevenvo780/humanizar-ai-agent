import type { ToolDefinition, ToolTrace } from '../types';
import { isList, isRecord } from './core';

export function isToolTrace(value: unknown): value is ToolTrace {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    typeof value.tool === 'string' &&
    isRecord(value.input) &&
    typeof value.output === 'string' &&
    (value.status === 'completed' || value.status === 'error') &&
    typeof value.duration_ms === 'number' &&
    Number.isFinite(value.duration_ms) &&
    value.duration_ms >= 0
  );
}

function isTool(value: unknown): value is ToolDefinition {
  return (
    isRecord(value) &&
    typeof value.name === 'string' &&
    typeof value.description === 'string' &&
    typeof value.enabled === 'boolean' &&
    (value.input_schema === undefined || isRecord(value.input_schema))
  );
}

export function isToolList(value: unknown): value is { tools: ToolDefinition[] } {
  return isRecord(value) && isList(value.tools, isTool);
}

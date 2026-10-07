import type { Config } from '../types';

export type Validator<T> = (value: unknown) => value is T;

export function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export function isCount(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}

/** Unknown non-empty modes stay valid so a newer backend cannot brick health or config. */
export function isMode(value: unknown): value is Config['mode'] {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= 64;
}

export function isList<T>(value: unknown, validate: Validator<T>): value is T[] {
  return Array.isArray(value) && value.every((item: unknown) => validate(item));
}

export function validate<T>(value: unknown, check: Validator<T>): T {
  if (!check(value)) throw new Error('El servidor devolvió datos inválidos. Intenta de nuevo.');
  return value;
}

import type { CompanyIdentity, Config, Health } from '../types';
import { safeCompanyWebsite } from '../../config/company';
import { isList, isMode, isRecord } from './core';

export function isConfig(value: unknown): value is Config {
  return (
    isRecord(value) &&
    typeof value.company_name === 'string' &&
    typeof value.company_description === 'string' &&
    typeof value.assistant_name === 'string' &&
    typeof value.model === 'string' &&
    isMode(value.mode) &&
    typeof value.embedding === 'string' &&
    typeof value.max_upload_mb === 'number' &&
    Number.isFinite(value.max_upload_mb) &&
    value.max_upload_mb > 0
  );
}

export function isCompanyIdentity(value: unknown): value is CompanyIdentity {
  return (
    isRecord(value) &&
    typeof value.company_name === 'string' &&
    value.company_name.trim().length > 0 &&
    typeof value.company_description === 'string' &&
    typeof value.assistant_name === 'string' &&
    value.assistant_name.trim().length > 0 &&
    (value.website === undefined || safeCompanyWebsite(value.website) !== null) &&
    (value.suggested_questions === undefined ||
      (isList(
        value.suggested_questions,
        (entry): entry is string =>
          typeof entry === 'string' && entry.trim().length > 0 && entry.length <= 1000,
      ) &&
        value.suggested_questions.length <= 12))
  );
}

export function isHealth(value: unknown): value is Health {
  return (
    isRecord(value) &&
    typeof value.status === 'string' &&
    isMode(value.mode) &&
    typeof value.model === 'string' &&
    typeof value.embedding === 'string' &&
    isRecord(value.tools) &&
    typeof value.tools.sandbox === 'boolean' &&
    typeof value.tools.mcp === 'boolean' &&
    (value.features === undefined ||
      (isRecord(value.features) &&
        typeof value.features.customer_management === 'boolean' &&
        (value.features.document_reading === undefined ||
          typeof value.features.document_reading === 'boolean')))
  );
}

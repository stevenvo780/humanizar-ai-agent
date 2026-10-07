import type { CustomerRequest } from '../types';
import { isList, isRecord } from './core';

function isCustomerRequest(value: unknown): value is CustomerRequest {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    // A new request kind is displayed generically instead of invalidating the whole list.
    typeof value.kind === 'string' &&
    value.kind.trim().length > 0 &&
    value.kind.length <= 64 &&
    typeof value.status === 'string' &&
    typeof value.created_at === 'string' &&
    Number.isFinite(Date.parse(value.created_at)) &&
    isRecord(value.details)
  );
}

export function isRequestList(value: unknown): value is { requests: CustomerRequest[] } {
  return isRecord(value) && isList(value.requests, isCustomerRequest);
}

import type { AuthResponse, CustomerAccount, CustomerAccountList, User } from '../types';
import { isCount, isList, isRecord } from './core';

export function isUser(value: unknown): value is User {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    value.id.length > 0 &&
    typeof value.name === 'string' &&
    typeof value.email === 'string' &&
    (value.role === 'admin' || value.role === 'customer')
  );
}

export function isAuthResponse(value: unknown): value is AuthResponse {
  return (
    isRecord(value) &&
    typeof value.access_token === 'string' &&
    value.access_token.length > 0 &&
    value.token_type === 'bearer' &&
    isUser(value.user)
  );
}

export function isAuthStatus(value: unknown): value is { setup_required: boolean } {
  return isRecord(value) && typeof value.setup_required === 'boolean';
}

export function isCustomerAccount(value: unknown): value is CustomerAccount {
  return (
    isUser(value) &&
    value.role === 'customer' &&
    'created_at' in value &&
    typeof value.created_at === 'string' &&
    Number.isFinite(Date.parse(value.created_at))
  );
}

export function isCustomerAccountList(value: unknown): value is CustomerAccountList {
  return (
    isRecord(value) &&
    isList(value.customers, isCustomerAccount) &&
    isCount(value.total) &&
    isCount(value.limit) &&
    value.limit >= 1 &&
    value.limit <= 100 &&
    isCount(value.offset) &&
    value.customers.length <= value.limit &&
    value.customers.length <= value.total
  );
}

export function isCreatedCustomer(value: unknown): value is { customer: CustomerAccount } {
  return isRecord(value) && isCustomerAccount(value.customer);
}

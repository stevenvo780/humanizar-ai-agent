import type {
  AuthResponse,
  ChatMessage,
  ChatResponse,
  Config,
  CompanyIdentity,
  Conversation,
  CustomerAccount,
  CustomerAccountList,
  CustomerRequest,
  DocumentDetail,
  DocumentList,
  Health,
  KnowledgeDocument,
  Source,
  ToolDefinition,
  ToolTrace,
  UploadResult,
  User,
} from './types';
import { safeCompanyWebsite } from './company';

export type Validator<T> = (value: unknown) => value is T;

export function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isCount(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}

/** Unknown non-empty modes stay valid so a newer backend cannot brick health or config. */
function isMode(value: unknown): value is Config['mode'] {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= 64;
}

function isList<T>(value: unknown, validate: Validator<T>): value is T[] {
  return Array.isArray(value) && value.every((item: unknown) => validate(item));
}

export function validate<T>(value: unknown, check: Validator<T>): T {
  if (!check(value)) throw new Error('El servidor devolvió datos inválidos. Intenta de nuevo.');
  return value;
}

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
        value.suggested_questions.length <= 8))
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

function isDocument(value: unknown): value is KnowledgeDocument {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    typeof value.name === 'string' &&
    isCount(value.chunks) &&
    isCount(value.characters) &&
    typeof value.created_at === 'string'
  );
}

export function isDocumentDetail(value: unknown): value is DocumentDetail {
  return (
    isDocument(value) &&
    value.id.length > 0 &&
    value.name.length > 0 &&
    Number.isFinite(Date.parse(value.created_at)) &&
    'content' in value &&
    typeof value.content === 'string' &&
    'reconstructed' in value &&
    typeof value.reconstructed === 'boolean'
  );
}

export function isDocumentList(value: unknown): value is DocumentList {
  return isRecord(value) && isList(value.documents, isDocument) && isCount(value.total_chunks);
}

export function isUploadResult(value: unknown): value is UploadResult {
  return (
    isDocumentList(value) &&
    'skipped' in value &&
    Array.isArray(value.skipped) &&
    value.skipped.every((entry: unknown) => typeof entry === 'string')
  );
}

function isSource(value: unknown): value is Source {
  return (
    isRecord(value) &&
    typeof value.document_id === 'string' &&
    typeof value.document_name === 'string' &&
    typeof value.chunk_id === 'string' &&
    typeof value.text === 'string' &&
    typeof value.score === 'number' &&
    Number.isFinite(value.score)
  );
}

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

export function isChatResponse(value: unknown): value is ChatResponse {
  return (
    isRecord(value) &&
    typeof value.answer === 'string' &&
    isList(value.sources, isSource) &&
    isList(value.trace, isToolTrace) &&
    isMode(value.mode) &&
    typeof value.model === 'string' &&
    typeof value.session_id === 'string' &&
    isRecord(value.usage) &&
    isCount(value.usage.input_tokens) &&
    isCount(value.usage.output_tokens)
  );
}

function isChatMessage(value: unknown): value is ChatMessage {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    (value.role === 'user' || value.role === 'assistant') &&
    typeof value.content === 'string' &&
    isList(value.sources, isSource) &&
    isList(value.trace, isToolTrace) &&
    (value.error === undefined || typeof value.error === 'string')
  );
}

function isConversation(value: unknown): value is Conversation {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    typeof value.title === 'string' &&
    isList(value.messages, isChatMessage) &&
    typeof value.updatedAt === 'number' &&
    Number.isFinite(value.updatedAt) &&
    (value.sessionId === undefined || typeof value.sessionId === 'string')
  );
}

export function isConversationList(value: unknown): value is { conversations: Conversation[] } {
  return isRecord(value) && isList(value.conversations, isConversation);
}

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

/** Known modes get specific copy; a newer backend mode is shown with a generic label. */
export type AssistantMode = 'demo' | 'anthropic' | (string & Record<never, never>);

export interface Config {
  company_name: string;
  company_description: string;
  assistant_name: string;
  model: string;
  mode: AssistantMode;
  embedding: string;
  max_upload_mb: number;
}

export interface CompanyIdentity {
  company_name: string;
  company_description: string;
  assistant_name: string;
  website?: string;
  suggested_questions?: string[];
}

export interface Health {
  status: string;
  mode: AssistantMode;
  model: string;
  embedding: string;
  tools: { sandbox: boolean; mcp: boolean };
  features?: { customer_management: boolean; document_reading?: boolean };
}

export interface KnowledgeDocument {
  id: string;
  name: string;
  chunks: number;
  characters: number;
  created_at: string;
}

export interface DocumentDetail extends KnowledgeDocument {
  content: string;
  reconstructed: boolean;
}

export interface DocumentList {
  documents: KnowledgeDocument[];
  total_chunks: number;
}

export interface UploadResult extends DocumentList {
  skipped: string[];
}

export interface Source {
  document_id: string;
  document_name: string;
  chunk_id: string;
  text: string;
  score: number;
}

export interface ToolTrace {
  id: string;
  tool: string;
  input: Record<string, unknown>;
  output: string;
  status: 'completed' | 'error';
  duration_ms: number;
}

export interface ToolDefinition {
  name: string;
  description: string;
  enabled: boolean;
  input_schema?: Record<string, unknown>;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  trace: ToolTrace[];
  mode: AssistantMode;
  model: string;
  usage: { input_tokens: number; output_tokens: number };
  session_id: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources: Source[];
  trace: ToolTrace[];
  error?: string;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  sessionId?: string;
  updatedAt: number;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'customer';
}

export interface AuthResponse {
  access_token: string;
  token_type: 'bearer';
  user: User;
}

export interface CustomerAccount extends Omit<User, 'role'> {
  role: 'customer';
  created_at: string;
}

export interface CustomerAccountList {
  customers: CustomerAccount[];
  total: number;
  limit: number;
  offset: number;
}

/** Unknown request kinds from a newer backend are listed with a generic label. */
export type CustomerRequestKind = 'demo' | 'support' | (string & Record<never, never>);

export interface CustomerRequest {
  id: string;
  kind: CustomerRequestKind;
  status: string;
  created_at: string;
  details: Record<string, unknown>;
}

export type WorkspaceSection = 'assistant' | 'knowledge' | 'tools' | 'requests' | 'customers';

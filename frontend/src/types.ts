export interface Config {
  company_name: string;
  company_description: string;
  assistant_name: string;
  model: string;
  mode: 'demo' | 'anthropic';
  embedding: string;
  max_upload_mb: number;
}

export interface Health {
  status: string;
  mode: 'demo' | 'anthropic';
  model: string;
  embedding: string;
  tools: { sandbox: boolean; mcp: boolean };
}

export interface KnowledgeDocument {
  id: string;
  name: string;
  chunks: number;
  characters: number;
  created_at: string;
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
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  trace: ToolTrace[];
  mode: 'demo' | 'anthropic';
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

export interface ProviderSettings {
  configured: boolean;
  model: string;
  mode: 'demo' | 'anthropic';
  verified: boolean;
}

export interface CustomerRequest {
  id: string;
  kind: 'demo' | 'support';
  status: string;
  created_at: string;
  details: Record<string, unknown>;
}

export type Tab = 'assistant' | 'knowledge' | 'tools' | 'requests' | 'provider';

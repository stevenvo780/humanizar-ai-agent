import type { ChatMessage, ChatResponse, Conversation, Source } from '../types';
import { isCount, isList, isMode, isRecord } from './core';
import { isToolTrace } from './tools';

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

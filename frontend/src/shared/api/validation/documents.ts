import type { DocumentDetail, DocumentList, KnowledgeDocument, UploadResult } from '../types';
import { isCount, isList, isRecord } from './core';

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

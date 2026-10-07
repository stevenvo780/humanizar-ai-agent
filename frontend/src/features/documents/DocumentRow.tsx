import { BookOpen, Check, FileText, Trash2, X } from 'lucide-react';
import type { KnowledgeDocument } from '../../shared/api/types';
import { plural } from '../../shared/utils/plural';

export function DocumentRow({
  doc,
  readerAvailable,
  reading,
  readerOpen,
  confirmingDelete,
  deleting,
  online,
  onRead,
  onDelete,
  onDeleteIntent,
}: {
  doc: KnowledgeDocument;
  readerAvailable: boolean;
  /** This document is the one currently open in the reader. */
  reading: boolean;
  /** Any document is currently open in the reader. */
  readerOpen: boolean;
  confirmingDelete: boolean;
  deleting: string | null;
  online: boolean;
  onRead: (document: KnowledgeDocument, trigger: HTMLButtonElement) => void;
  onDelete: (id: string) => Promise<void>;
  onDeleteIntent: (id: string | null) => void;
}) {
  return (
    <div className={`document-row ${reading ? 'document-row-reading' : ''}`}>
      <span className="document-icon">
        <FileText size={22} />
      </span>
      <div className="document-info">
        <button
          className="document-read-button"
          type="button"
          aria-label={`Leer ${doc.name}`}
          aria-expanded={reading}
          aria-controls={readerOpen ? 'document-reader' : undefined}
          aria-describedby={!readerAvailable ? 'document-reader-unavailable' : undefined}
          disabled={!readerAvailable || deleting === doc.id}
          onClick={(event) => onRead(doc, event.currentTarget)}
        >
          <span>{doc.name}</span>
          <BookOpen size={16} />
        </button>
        <span>
          {plural(doc.chunks, 'fragmento', 'fragmentos')} · {doc.characters.toLocaleString('es')}{' '}
          caracteres
        </span>
      </div>
      {confirmingDelete ? (
        <div className="delete-confirm">
          <span>¿Eliminar?</span>
          <button
            className="danger-link"
            disabled={!!deleting}
            onClick={() => void onDelete(doc.id)}
          >
            {deleting === doc.id ? 'Eliminando…' : 'Confirmar'}
          </button>
          <button
            className="icon-button"
            aria-label="Cancelar eliminación"
            onClick={() => onDeleteIntent(null)}
          >
            <X size={16} />
          </button>
        </div>
      ) : (
        <>
          <span className="ready-badge">
            <Check size={12} />
            Indexado
          </span>
          <button
            className="icon-button delete-button"
            aria-label={`Eliminar ${doc.name}`}
            disabled={!online}
            onClick={() => onDeleteIntent(doc.id)}
          >
            <Trash2 size={16} />
          </button>
        </>
      )}
    </div>
  );
}

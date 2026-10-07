import { useEffect, useRef, useState } from 'react';
import { BookOpen, Code2, FileText, LoaderCircle, RefreshCw, X } from 'lucide-react';
import { api, ApiError, errorMessage } from './api';
import { DocumentMarkdown } from './DocumentMarkdown';
import type { DocumentDetail, KnowledgeDocument } from './types';

type ReaderState =
  | { status: 'loading' }
  | { status: 'ready'; detail: DocumentDetail }
  | { status: 'error'; message: string };

export function DocumentReader({
  document,
  onClose,
}: {
  document: KnowledgeDocument;
  onClose: () => void;
}) {
  const [state, setState] = useState<ReaderState>({ status: 'loading' });
  const [view, setView] = useState<'markdown' | 'text'>('markdown');
  const [attempt, setAttempt] = useState(0);
  const readerRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    titleRef.current?.focus({ preventScroll: true });
    readerRef.current?.scrollIntoView({ block: 'start', behavior: 'auto' });
  }, [document.id, attempt]);

  useEffect(() => {
    if (state.status === 'ready' && readerRef.current?.contains(window.document.activeElement)) {
      readerRef.current.scrollIntoView({ block: 'start', behavior: 'auto' });
    }
  }, [state.status]);

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: 'loading' });

    async function load(): Promise<void> {
      try {
        const detail = await api.document(document.id, controller.signal);
        if (!controller.signal.aborted) setState({ status: 'ready', detail });
      } catch (error) {
        if (controller.signal.aborted) return;
        setState({
          status: 'error',
          message:
            error instanceof ApiError && error.status === 404
              ? 'Este documento no está disponible para lectura. Puede haber sido eliminado o el servidor todavía no admite esta función.'
              : errorMessage(error),
        });
      }
    }

    void load();
    return () => controller.abort();
  }, [document.id, attempt]);

  return (
    <section
      ref={readerRef}
      className="document-reader"
      id="document-reader"
      aria-labelledby="document-reader-title"
      aria-busy={state.status === 'loading'}
    >
      <header className="document-reader-header">
        <div>
          <span className="document-reader-eyebrow">
            <BookOpen size={15} /> LECTOR DE DOCUMENTOS
          </span>
          <h2 id="document-reader-title" ref={titleRef} tabIndex={-1}>
            {document.name}
          </h2>
        </div>
        <button
          className="icon-button"
          type="button"
          aria-label="Cerrar lector de documentos"
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </header>
      {state.status === 'loading' && (
        <div className="document-reader-loading" role="status">
          <LoaderCircle className="spin" size={20} /> Cargando el documento…
        </div>
      )}
      {state.status === 'error' && (
        <div className="document-reader-error">
          <p className="notice error" role="alert">
            {state.message}
          </p>
          <button
            className="secondary-button"
            type="button"
            onClick={() => setAttempt((current) => current + 1)}
          >
            <RefreshCw size={16} /> Reintentar lectura
          </button>
        </div>
      )}
      {state.status === 'ready' && (
        <>
          <div className="document-reader-toolbar" aria-label="Formato de lectura">
            <div className="document-reader-formats">
              <button
                type="button"
                className={view === 'markdown' ? 'selected' : ''}
                aria-pressed={view === 'markdown'}
                onClick={() => setView('markdown')}
              >
                <BookOpen size={16} /> Lectura
              </button>
              <button
                type="button"
                className={view === 'text' ? 'selected' : ''}
                aria-pressed={view === 'text'}
                onClick={() => setView('text')}
              >
                <Code2 size={16} />{' '}
                {state.detail.reconstructed ? 'Texto recuperado' : 'Texto original'}
              </button>
            </div>
            <span className="document-reader-meta">
              <FileText size={14} /> {state.detail.content.length.toLocaleString('es')} caracteres
            </span>
          </div>
          {state.detail.reconstructed && (
            <p className="document-reconstruction-note" role="note">
              Este texto se recuperó de los fragmentos indexados. El formato y los espacios pueden
              diferir del archivo original.
            </p>
          )}
          <div className="document-reader-content">
            {!state.detail.content.trim() ? (
              <p className="document-reader-empty">El documento no contiene texto para mostrar.</p>
            ) : view === 'markdown' ? (
              <DocumentMarkdown content={state.detail.content} />
            ) : (
              <pre className="document-original-text">{state.detail.content}</pre>
            )}
          </div>
        </>
      )}
    </section>
  );
}

import { useEffect, useRef, useState } from 'react';
import type { ChangeEvent } from 'react';
import {
  BookOpen,
  Check,
  CheckCheck,
  FileText,
  FolderOpen,
  Layers3,
  LoaderCircle,
  ShieldCheck,
  Trash2,
  UploadCloud,
  X,
} from 'lucide-react';
import { api, errorMessage } from '../../shared/api/api';
import type { DocumentList, KnowledgeDocument } from '../../shared/api/types';
import { EmptyState } from '../../shared/ui/EmptyState';
import { plural } from '../../shared/utils/plural';
import { DocumentReader } from './DocumentReader';

export function Knowledge({
  documents,
  refresh,
  maxUpload,
  online,
  readerAvailable,
}: {
  documents: DocumentList;
  refresh: () => Promise<void>;
  maxUpload: number;
  online: boolean;
  readerAvailable: boolean;
}) {
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [readingDocument, setReadingDocument] = useState<KnowledgeDocument | null>(null);
  const readingSelection = useRef<KnowledgeDocument | null>(null);
  const readingTrigger = useRef<HTMLButtonElement | null>(null);
  const libraryHeading = useRef<HTMLHeadingElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function readDocument(document: KnowledgeDocument, trigger: HTMLButtonElement): void {
    readingSelection.current = document;
    readingTrigger.current = trigger;
    setReadingDocument(document);
  }

  function closeReader(restoreTrigger = true): void {
    readingSelection.current = null;
    setReadingDocument(null);
    if (restoreTrigger && readingTrigger.current?.isConnected) readingTrigger.current.focus();
    else libraryHeading.current?.focus();
  }

  useEffect(() => {
    if (!readerAvailable && readingSelection.current) {
      readingSelection.current = null;
      setReadingDocument(null);
      libraryHeading.current?.focus();
    }
  }, [readerAvailable]);

  async function upload(files: FileList | File[]): Promise<void> {
    if (uploading || !online) return;
    setUploading(true);
    setError('');
    setNotice('');
    const skipped: string[] = [];
    const errors: string[] = [];
    let uploaded = 0;
    for (const file of Array.from(files)) {
      if (file.size > maxUpload * 1024 * 1024) {
        errors.push(`${file.name}: supera ${maxUpload} MB.`);
        continue;
      }
      try {
        const result = await api.upload(file);
        uploaded += result.documents.length;
        skipped.push(...result.skipped);
      } catch (err) {
        errors.push(`${file.name}: ${errorMessage(err)}`);
      }
    }
    try {
      await refresh();
    } catch (err) {
      errors.push(errorMessage(err));
    }
    if (uploaded)
      setNotice(
        `${uploaded} documento${uploaded === 1 ? '' : 's'} procesado${uploaded === 1 ? '' : 's'}.${skipped.length ? ` Archivos omitidos: ${skipped.join(', ')}` : ''}`,
      );
    else if (skipped.length) setNotice(`Archivos omitidos: ${skipped.join(', ')}`);
    setError(errors.join(' '));
    setUploading(false);
    if (inputRef.current) inputRef.current.value = '';
  }

  async function remove(id: string): Promise<void> {
    setDeleting(id);
    setError('');
    try {
      await api.deleteDocument(id);
      if (readingSelection.current?.id === id) closeReader(false);
      await refresh();
      setDeleteId(null);
      setNotice('Documento eliminado de la biblioteca de la empresa.');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setDeleting(null);
    }
  }

  return (
    <section className="workspace-page" aria-labelledby="knowledge-title">
      <div className="page-eyebrow">
        <BookOpen size={15} /> ADMINISTRACIÓN · DOCUMENTACIÓN
      </div>
      <h1 id="knowledge-title">
        Información de la empresa.
        <br />
        <span>En un solo lugar.</span>
      </h1>
      <p className="page-intro">
        Añade archivos Markdown (.md) con información de tu empresa. El asistente los consultará al
        responder a los clientes.
        <br className="desktop-break" /> También puedes subir otros formatos o varios documentos
        juntos.
      </p>
      <div className="knowledge-summary">
        <div>
          <FolderOpen size={19} />
          <span>
            <strong>{documents.documents.length}</strong> documentos
          </span>
        </div>
        <div>
          <Layers3 size={19} />
          <span>
            <strong>{documents.total_chunks}</strong> fragmentos consultables
          </span>
        </div>
      </div>
      <div
        className={`upload-zone ${dragging ? 'dragging' : ''}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          void upload(event.dataTransfer.files);
        }}
      >
        <span className="upload-icon">
          {uploading ? <LoaderCircle className="spin" size={26} /> : <UploadCloud size={26} />}
        </span>
        <h2>
          {uploading ? 'Procesando la documentación…' : 'Un nuevo archivo. Mejores respuestas.'}
        </h2>
        <p>
          Arrastra documentos de la empresa aquí o{' '}
          <button
            className="text-link"
            disabled={uploading || !online}
            onClick={() => inputRef.current?.click()}
          >
            selecciona archivos
          </button>
        </p>
        <button
          className="primary-button"
          disabled={uploading || !online}
          onClick={() => inputRef.current?.click()}
        >
          <UploadCloud size={18} /> {uploading ? 'Procesando archivos…' : 'Añadir documentos'}
        </button>
        <span className="upload-formats">
          TXT, MD, PDF, DOCX, CSV, JSON y ZIP · Hasta {maxUpload} MB por archivo
        </span>
        <input
          className="sr-only"
          id="document-upload"
          ref={inputRef}
          type="file"
          multiple
          accept=".txt,.md,.pdf,.docx,.csv,.json,.zip"
          aria-label="Seleccionar documentos para subir"
          disabled={uploading || !online}
          onChange={(event: ChangeEvent<HTMLInputElement>) => {
            if (event.target.files) void upload(event.target.files);
          }}
        />
      </div>
      {notice && (
        <div className="notice success" role="status">
          <CheckCheck size={17} />
          {notice}
        </div>
      )}
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
      <div className="document-heading">
        <h2 ref={libraryHeading} tabIndex={-1}>
          Biblioteca de la empresa <span>{documents.documents.length}</span>
        </h2>
        <span>Disponible para el asistente</span>
      </div>
      {!readerAvailable && (
        <p className="document-reader-availability" id="document-reader-unavailable" role="status">
          La lectura de documentos requiere una actualización del servidor. Puedes seguir
          administrando la biblioteca.
        </p>
      )}
      {documents.documents.length ? (
        <div className="document-list">
          {documents.documents.map((doc: KnowledgeDocument) => (
            <div
              className={`document-row ${readerAvailable && readingDocument?.id === doc.id ? 'document-row-reading' : ''}`}
              key={doc.id}
            >
              <span className="document-icon">
                <FileText size={22} />
              </span>
              <div className="document-info">
                <button
                  className="document-read-button"
                  type="button"
                  aria-label={`Leer ${doc.name}`}
                  aria-expanded={readerAvailable && readingDocument?.id === doc.id}
                  aria-controls={readerAvailable && readingDocument ? 'document-reader' : undefined}
                  aria-describedby={!readerAvailable ? 'document-reader-unavailable' : undefined}
                  disabled={!readerAvailable || deleting === doc.id}
                  onClick={(event) => readDocument(doc, event.currentTarget)}
                >
                  <span>{doc.name}</span>
                  <BookOpen size={16} />
                </button>
                <span>
                  {plural(doc.chunks, 'fragmento', 'fragmentos')} ·{' '}
                  {doc.characters.toLocaleString('es')} caracteres
                </span>
              </div>
              {deleteId === doc.id ? (
                <div className="delete-confirm">
                  <span>¿Eliminar?</span>
                  <button
                    className="danger-link"
                    disabled={!!deleting}
                    onClick={() => void remove(doc.id)}
                  >
                    {deleting === doc.id ? 'Eliminando…' : 'Confirmar'}
                  </button>
                  <button
                    className="icon-button"
                    aria-label="Cancelar eliminación"
                    onClick={() => setDeleteId(null)}
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
                    onClick={() => setDeleteId(doc.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      ) : (
        <EmptyState icon={<BookOpen size={24} />} title="Prepara las fuentes del asistente">
          Los documentos de la empresa aparecerán aquí después de subirlos.
        </EmptyState>
      )}
      {readerAvailable && readingDocument && (
        <DocumentReader
          key={readingDocument.id}
          document={readingDocument}
          onClose={() => closeReader()}
        />
      )}
      <p className="page-footnote">
        <ShieldCheck size={13} /> Los ZIP se procesan sin extraer archivos al sistema anfitrión.
      </p>
    </section>
  );
}

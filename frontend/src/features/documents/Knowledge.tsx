import { useEffect, useRef, useState } from 'react';
import { BookOpen, CheckCheck, FolderOpen, Layers3, ShieldCheck } from 'lucide-react';
import { api, errorMessage } from '../../shared/api/api';
import type { DocumentList, KnowledgeDocument } from '../../shared/api/types';
import { EmptyState } from '../../shared/ui/EmptyState';
import { DocumentReader } from './DocumentReader';
import { DocumentRow } from './DocumentRow';
import { UploadZone } from './UploadZone';

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
      <UploadZone
        uploading={uploading}
        online={online}
        maxUpload={maxUpload}
        inputRef={inputRef}
        onUpload={upload}
      />
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
            <DocumentRow
              key={doc.id}
              doc={doc}
              readerAvailable={readerAvailable}
              reading={readerAvailable && readingDocument?.id === doc.id}
              readerOpen={readerAvailable && !!readingDocument}
              confirmingDelete={deleteId === doc.id}
              deleting={deleting}
              online={online}
              onRead={readDocument}
              onDelete={remove}
              onDeleteIntent={setDeleteId}
            />
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

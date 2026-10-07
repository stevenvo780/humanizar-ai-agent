import { useState } from 'react';
import type { ChangeEvent, RefObject } from 'react';
import { LoaderCircle, UploadCloud } from 'lucide-react';

export function UploadZone({
  uploading,
  online,
  maxUpload,
  inputRef,
  onUpload,
}: {
  uploading: boolean;
  online: boolean;
  maxUpload: number;
  inputRef: RefObject<HTMLInputElement | null>;
  onUpload: (files: FileList | File[]) => Promise<void>;
}) {
  const [dragging, setDragging] = useState(false);
  return (
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
        void onUpload(event.dataTransfer.files);
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
          if (event.target.files) void onUpload(event.target.files);
        }}
      />
    </div>
  );
}

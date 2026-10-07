import { ChevronDown } from 'lucide-react';
import type { Source } from '../../shared/api/types';

export function SourceCard({ source, index }: { source: Source; index: number }) {
  return (
    <details className="source-card">
      <summary>
        <span className="source-number">{index + 1}</span>
        <span className="source-name">
          {source.document_name}
          <small>Fragmento consultado</small>
        </span>
        <ChevronDown size={14} />
      </summary>
      <div className="source-excerpt">
        <p>{source.text}</p>
        <span>Referencia: {source.chunk_id}</span>
      </div>
    </details>
  );
}

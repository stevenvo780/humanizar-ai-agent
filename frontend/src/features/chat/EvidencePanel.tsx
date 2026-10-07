import {
  ArrowUpRight,
  ChevronRight,
  FileText,
  Layers3,
  LoaderCircle,
  ShieldCheck,
} from 'lucide-react';
import type { ChatMessage, DocumentList } from '../../shared/api/types';
import { StatusDot } from '../../shared/ui/StatusDot';
import { plural } from '../../shared/utils/plural';
import { SourceCard } from './SourceCard';
import { Trace } from './Trace';

export function EvidencePanel({
  documents,
  company,
  selected,
  busy,
  onKnowledge,
  isAdmin,
}: {
  documents: DocumentList;
  company: string;
  selected: ChatMessage | undefined;
  busy: boolean;
  onKnowledge: () => void;
  isAdmin: boolean;
}) {
  const sources = selected?.sources ?? [];
  const trace = selected?.trace ?? [];
  return (
    <aside className="evidence-panel" aria-label="Contexto y fuentes">
      <div className="panel-heading">
        <span>FUENTES DE INFORMACIÓN</span>
        <Layers3 size={15} />
      </div>
      <div className="context-company">
        <span className="context-company-icon">
          {company.slice(0, 1).toUpperCase()}
          <span />
        </span>
        <div>
          <strong>Documentación de {company}</strong>
          <p>Información para decidir con claridad.</p>
        </div>
      </div>
      <div className="context-stat">
        <span>
          <StatusDot online />
          {isAdmin
            ? plural(documents.documents.length, 'documento disponible', 'documentos disponibles')
            : sources.length
              ? plural(sources.length, 'fuente consultada', 'fuentes consultadas')
              : 'Respuestas con documentación'}
        </span>
        <span>
          {isAdmin
            ? plural(documents.total_chunks, 'fragmento', 'fragmentos')
            : 'Explora las referencias de cada respuesta'}
        </span>
      </div>
      <div className="panel-section-heading">
        <h2>{sources.length ? 'Fuentes de esta respuesta' : 'Información de la empresa'}</h2>
        {sources.length > 0 && <span className="count-badge">{sources.length}</span>}
      </div>
      {sources.length ? (
        <div className="source-list">
          {sources.map((source, index) => (
            <SourceCard key={`${source.chunk_id}-${index}`} source={source} index={index} />
          ))}
        </div>
      ) : (
        <div className="library-list">
          {documents.documents.slice(0, 4).map((doc) => (
            <button className="library-item" key={doc.id} onClick={onKnowledge}>
              <span className="file-icon">
                <FileText size={17} />
              </span>
              <span>
                {doc.name}
                <small>
                  {plural(doc.chunks, 'fragmento', 'fragmentos')} · Disponible para consultar
                </small>
              </span>
              <ChevronRight size={13} />
            </button>
          ))}
          {documents.documents.length === 0 && (
            <p className="panel-empty-copy">
              Las fuentes consultadas aparecerán junto a cada respuesta.
            </p>
          )}
          {isAdmin && (
            <button className="text-link library-link" onClick={onKnowledge}>
              {documents.documents.length ? 'Ver documentación' : 'Administrar fuentes'}
              <ArrowUpRight size={14} />
            </button>
          )}
        </div>
      )}
      <div className="panel-rule" />
      <div className="panel-section-heading">
        <h2>{trace.length ? 'Actividad de herramientas' : 'De la pregunta a la claridad'}</h2>
        {busy && <LoaderCircle size={14} className="spin" />}
      </div>
      {trace.length > 0 ? (
        <div className="trace-list">
          {trace.map((item) => (
            <Trace key={item.id} trace={item} />
          ))}
        </div>
      ) : (
        <div className="how-list">
          <div>
            <span>01</span>
            <p>
              <strong>Encuentra el contexto</strong>
              <small>Consulta la documentación de la empresa.</small>
            </p>
          </div>
          <div>
            <span>02</span>
            <p>
              <strong>Conecta la información</strong>
              <small>Usa las herramientas que necesita.</small>
            </p>
          </div>
          <div>
            <span>03</span>
            <p>
              <strong>Responde con fuentes</strong>
              <small>Puedes explorar cada referencia.</small>
            </p>
          </div>
        </div>
      )}
      <div className="trust-card">
        <ShieldCheck size={19} />
        <div>
          <strong>Claridad, también en el proceso.</strong>
          <p>Respuestas conectadas a la documentación de la empresa. Explora cada fuente.</p>
        </div>
      </div>
      <div className="panel-bottom">
        <span className="tiny-star" aria-hidden="true">
          ✦
        </span>{' '}
        Menos buscar. Más avanzar.
      </div>
    </aside>
  );
}

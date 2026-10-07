import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowRight,
  CircleHelp,
  Clock3,
  LoaderCircle,
  MessageSquare,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { api, errorMessage } from './api';
import type { CustomerRequest } from './types';

/** Known kinds keep their copy; a kind added by a newer backend gets a generic label. */
export function requestKindLabel(kind: CustomerRequest['kind']): string {
  if (kind === 'demo') return 'Solicitud de demostración';
  if (kind === 'support') return 'Ticket de soporte';
  return 'Solicitud';
}

function RequestKindIcon({ kind }: { kind: CustomerRequest['kind'] }) {
  if (kind === 'demo') return <Sparkles size={21} />;
  if (kind === 'support') return <CircleHelp size={21} />;
  return <MessageSquare size={21} />;
}

export function RequestsPanel({ onChat, isAdmin }: { onChat: () => void; isAdmin: boolean }) {
  const [requests, setRequests] = useState<CustomerRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const loadRevision = useRef(0);
  const load = useCallback(async () => {
    const revision = ++loadRevision.current;
    setLoading(true);
    setError('');
    try {
      const result = await (isAdmin ? api.adminRequests() : api.requests());
      if (revision === loadRevision.current) setRequests(result.requests);
    } catch (err) {
      if (revision === loadRevision.current) setError(errorMessage(err));
    } finally {
      if (revision === loadRevision.current) setLoading(false);
    }
  }, [isAdmin]);
  const invalidateLoad = useCallback(() => {
    loadRevision.current++;
  }, []);
  useEffect(() => {
    void load();
    const changed = () => {
      void load();
    };
    window.addEventListener('humanizar-requests-changed', changed);
    return () => {
      invalidateLoad();
      window.removeEventListener('humanizar-requests-changed', changed);
    };
  }, [load, invalidateLoad]);
  const labels: Record<string, string> = {
    received: 'Recibida',
    open: 'Abierta',
    pending: 'Pendiente',
    completed: 'Completada',
    closed: 'Cerrada',
  };
  return (
    <section className="workspace-page requests-page">
      <div className="page-eyebrow">
        <MessageSquare size={15} /> {isAdmin ? 'SOLICITUDES DE CLIENTES' : 'MIS SOLICITUDES'}
      </div>
      <div className="account-page-header">
        <div>
          <h1>
            {isAdmin ? 'Solicitudes de clientes.' : 'Cada siguiente paso.'}
            <br />
            <span>En un mismo lugar.</span>
          </h1>
          <p className="page-intro">
            {isAdmin
              ? 'Consulta las demostraciones y los tickets de soporte registrados por los clientes.'
              : 'Aquí puedes seguir las demostraciones y consultas de soporte que confirmaste en tu conversación.'}
          </p>
        </div>
        <button
          className="icon-button"
          aria-label={isAdmin ? 'Actualizar solicitudes de clientes' : 'Actualizar mis solicitudes'}
          disabled={loading}
          onClick={() => void load()}
        >
          <RefreshCw size={17} className={loading ? 'spin' : ''} />
        </button>
      </div>
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
      {loading && requests.length === 0 ? (
        <div className="account-loading">
          <LoaderCircle className="spin" size={20} /> Consultando tus solicitudes…
        </div>
      ) : requests.length === 0 ? (
        <div className="requests-empty">
          <span className="empty-icon">
            <MessageSquare size={25} />
          </span>
          <h2>{isAdmin ? 'Todavía no hay solicitudes.' : 'El siguiente paso lo decides tú.'}</h2>
          {isAdmin ? (
            <p>
              Las demostraciones y los tickets de soporte que confirmen los clientes
              <br className="desktop-break" /> aparecerán aquí con su estado.
            </p>
          ) : (
            <p>
              Cuando confirmes una demo o un ticket de soporte,
              <br className="desktop-break" /> su registro y estado aparecerán aquí.
            </p>
          )}
          <button className="primary-button" onClick={onChat}>
            Hablar con el asistente
            <ArrowRight size={15} />
          </button>
        </div>
      ) : (
        <div className="request-list">
          {requests.map((request) => (
            <article className="request-card" key={request.id}>
              <div className="request-card-header">
                <span
                  className={`request-kind-icon ${request.kind === 'support' ? 'support' : ''}`}
                >
                  <RequestKindIcon kind={request.kind} />
                </span>
                <div>
                  <h2>{requestKindLabel(request.kind)}</h2>
                  <span className="request-id">#{request.id}</span>
                </div>
                <span className="request-status">
                  <span className="status-dot" />
                  {labels[request.status] ?? request.status}
                </span>
              </div>
              <dl className="request-details">
                {Object.entries(request.details).map(([key, value]) => (
                  <div key={key}>
                    <dt>{key.replaceAll('_', ' ')}</dt>
                    <dd>{typeof value === 'string' ? value : JSON.stringify(value)}</dd>
                  </div>
                ))}
              </dl>
              <div className="request-card-footer">
                <Clock3 size={12} />
                <time dateTime={request.created_at}>
                  {new Date(request.created_at).toLocaleString('es', {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}
                </time>
                <span>{isAdmin ? 'Solicitud de cliente' : 'Registrada en tu cuenta'}</span>
              </div>
            </article>
          ))}
        </div>
      )}
      <p className="page-footnote">
        <ShieldCheck size={13} /> Las solicitudes se guardan en la plataforma. No se envían mensajes
        externos automáticamente.
      </p>
    </section>
  );
}

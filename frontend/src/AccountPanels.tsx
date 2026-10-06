import { useCallback, useEffect, useState } from 'react';
import type { SyntheticEvent } from 'react';
import {
  ArrowRight,
  CheckCheck,
  CircleHelp,
  Clock3,
  KeyRound,
  LoaderCircle,
  MessageSquare,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { api, errorMessage } from './api';
import type { CustomerRequest, ProviderSettings } from './types';

export function RequestsPanel({ onChat, isAdmin }: { onChat: () => void; isAdmin: boolean }) {
  const [requests, setRequests] = useState<CustomerRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setRequests((await (isAdmin ? api.adminRequests() : api.requests())).requests);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);
  useEffect(() => {
    void load();
    const changed = () => {
      void load();
    };
    window.addEventListener('humanizar-requests-changed', changed);
    return () => window.removeEventListener('humanizar-requests-changed', changed);
  }, [load]);
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
          <h2>El siguiente paso lo decides tú.</h2>
          <p>
            Cuando confirmes una demo o un ticket de soporte,
            <br />
            su registro y estado aparecerán aquí.
          </p>
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
                <span className={`request-kind-icon ${request.kind}`}>
                  {request.kind === 'demo' ? <Sparkles size={21} /> : <CircleHelp size={21} />}
                </span>
                <div>
                  <h2>
                    {request.kind === 'demo' ? 'Solicitud de demostración' : 'Ticket de soporte'}
                  </h2>
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

export function ProviderPanel({ onChanged }: { onChanged: () => Promise<void> }) {
  const [settings, setSettings] = useState<ProviderSettings | null>(null);
  const [key, setKey] = useState('');
  const [busy, setBusy] = useState<'load' | 'save' | 'test' | null>('load');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const load = useCallback(async () => {
    setBusy('load');
    setError('');
    try {
      setSettings(await api.provider());
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  async function save(event: SyntheticEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setBusy('save');
    setError('');
    setNotice('');
    const credential = key.trim();
    setKey('');
    try {
      await api.saveProvider(credential);
      setSettings(await api.provider());
      await onChanged();
      setNotice('Clave guardada. Verifica la conexión para comprobar que Claude está disponible.');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }
  async function test(): Promise<void> {
    setBusy('test');
    setError('');
    setNotice('');
    try {
      const result = await api.testProvider();
      setSettings(await api.provider());
      await onChanged();
      if (result.ok) setNotice(result.message);
      else setError(result.message);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }
  return (
    <section className="workspace-page provider-page">
      <div className="page-eyebrow">
        <KeyRound size={15} /> ADMINISTRACIÓN · CONEXIÓN CLAUDE
      </div>
      <h1>
        Conecta la inteligencia.
        <br />
        <span>Conserva el control.</span>
      </h1>
      <p className="page-intro">
        Configura el proveedor del asistente desde tu cuenta de administrador.
        <br className="desktop-break" /> El modelo de esta conexión es Claude Haiku 4.5.
      </p>
      <div className="provider-status-card">
        <span className="provider-logo">
          <Sparkles size={27} />
        </span>
        <div>
          <h2>Claude Haiku 4.5</h2>
          <p>
            {busy === 'load'
              ? 'Consultando configuración…'
              : settings?.verified
                ? 'Conexión verificada con el proveedor'
                : settings?.configured
                  ? 'Clave configurada · Verificación pendiente'
                  : 'Sin clave configurada · Modo demo'}
          </p>
        </div>
        <span className={`provider-state ${settings?.verified ? 'verified' : ''}`}>
          <span className="status-dot" />
          {settings?.verified ? 'Verificada' : 'Pendiente'}
        </span>
      </div>
      <form className="provider-form" onSubmit={(event) => void save(event)}>
        <div className="provider-form-heading">
          <ShieldCheck size={19} />
          <div>
            <h2>{settings?.configured ? 'Actualizar clave de API' : 'Añadir clave de API'}</h2>
            <p>
              Se envía al backend para su custodia. No se guarda en el historial ni en el
              almacenamiento del navegador.
            </p>
          </div>
        </div>
        <label htmlFor="provider-key">Clave de Anthropic</label>
        <input
          id="provider-key"
          type="password"
          autoComplete="off"
          value={key}
          onChange={(event) => setKey(event.target.value)}
          placeholder="Ingresa una clave nueva"
          required
          minLength={8}
          spellCheck={false}
        />
        <div className="provider-form-actions">
          <button className="primary-button" disabled={!!busy || !key.trim()}>
            {busy === 'save' ? <LoaderCircle size={15} className="spin" /> : <KeyRound size={15} />}
            {busy === 'save' ? 'Guardando…' : 'Guardar clave'}
          </button>
          <button
            type="button"
            className="secondary-button"
            disabled={!!busy || !settings?.configured}
            onClick={() => void test()}
          >
            {busy === 'test' ? (
              <LoaderCircle size={15} className="spin" />
            ) : (
              <CheckCheck size={16} />
            )}
            {busy === 'test' ? 'Verificando…' : 'Verificar conexión'}
          </button>
        </div>
        {error && (
          <div className="notice error" role="alert">
            {error}
          </div>
        )}
        {notice && (
          <div className="notice success" role="status">
            <CheckCheck size={16} />
            {notice}
          </div>
        )}
      </form>
      <div className="provider-explanation">
        <ShieldCheck size={20} />
        <div>
          <h3>El estado cuenta lo que está comprobado.</h3>
          <p>
            Guardar una clave no confirma su validez. La conexión se presenta como verificada
            únicamente después de una comprobación exitosa. Sin conexión activa, el asistente
            informa que está en modo demo.
          </p>
        </div>
      </div>
    </section>
  );
}

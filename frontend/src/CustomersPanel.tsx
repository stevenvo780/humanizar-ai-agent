import { useCallback, useEffect, useRef, useState } from 'react';
import type { SyntheticEvent } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  CheckCheck,
  LoaderCircle,
  RefreshCw,
  UserPlus,
  Users,
} from 'lucide-react';
import { api, errorMessage } from './api';
import type { CustomerAccountList } from './types';

const PAGE_SIZE = 25;

export function CustomersPanel() {
  const [data, setData] = useState<CustomerAccountList | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const revision = useRef(0);
  const mounted = useRef(false);

  const load = useCallback(async () => {
    const current = ++revision.current;
    setLoading(true);
    setError('');
    try {
      const result = await api.customers(offset, PAGE_SIZE);
      if (current === revision.current && mounted.current) setData(result);
    } catch (err) {
      if (current === revision.current && mounted.current) setError(errorMessage(err));
    } finally {
      if (current === revision.current && mounted.current) setLoading(false);
    }
  }, [offset]);

  const invalidateLoad = useCallback(() => {
    mounted.current = false;
    revision.current++;
  }, []);

  useEffect(() => {
    mounted.current = true;
    void load();
    return invalidateLoad;
  }, [load, invalidateLoad]);

  async function create(event: SyntheticEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const result = await api.createCustomer({ name: name.trim(), email: email.trim(), password });
      if (!mounted.current) return;
      setPassword('');
      setName('');
      setEmail('');
      setNotice(
        `Cuenta de ${result.customer.name} creada. Ya puede iniciar sesión con su correo y contraseña.`,
      );
      if (offset === 0) await load();
      else setOffset(0);
    } catch (err) {
      if (mounted.current) setError(errorMessage(err));
    } finally {
      if (mounted.current) setSaving(false);
    }
  }

  const displayed = data?.customers ?? [];
  const total = data?.total ?? 0;

  return (
    <section className="workspace-page customers-page" aria-labelledby="customers-title">
      <div className="page-eyebrow">
        <Users size={15} /> ADMINISTRACIÓN · CLIENTES
      </div>
      <div className="account-page-header">
        <div>
          <h1 id="customers-title">
            Cuentas de clientes.
            <br />
            <span>Acceso a su propio espacio.</span>
          </h1>
          <p className="page-intro">
            Crea cuentas para tus clientes y consulta los registros. Cada cliente tiene sus propias
            conversaciones y solicitudes.
          </p>
        </div>
        <button
          className="icon-button"
          aria-label="Actualizar cuentas de clientes"
          disabled={loading || saving}
          onClick={() => void load()}
        >
          <RefreshCw size={18} className={loading ? 'spin' : ''} />
        </button>
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
      <form
        className="customer-form"
        onSubmit={(event) => void create(event)}
        aria-labelledby="new-customer-title"
      >
        <h2 id="new-customer-title">
          <UserPlus size={20} /> Crear cuenta de cliente
        </h2>
        <div className="customer-grid">
          <div className="form-field">
            <label htmlFor="customer-name">Nombre</label>
            <input
              id="customer-name"
              name="customer-name"
              autoComplete="off"
              required
              maxLength={120}
              value={name}
              disabled={saving}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className="form-field">
            <label htmlFor="customer-email">Correo electrónico</label>
            <input
              id="customer-email"
              name="customer-email"
              type="email"
              autoComplete="off"
              required
              maxLength={254}
              value={email}
              disabled={saving}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div className="form-field">
            <label htmlFor="customer-password">Contraseña inicial</label>
            <input
              id="customer-password"
              name="customer-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={6}
              maxLength={128}
              aria-describedby="customer-password-hint"
              value={password}
              disabled={saving}
              onChange={(event) => setPassword(event.target.value)}
            />
            <p id="customer-password-hint" className="customer-meta">
              Mínimo 6 caracteres. Comparte el acceso directamente con el cliente.
            </p>
          </div>
        </div>
        <button
          type="submit"
          className="primary-button"
          disabled={saving || !name.trim() || !email.trim() || password.length < 6}
        >
          {saving ? <LoaderCircle size={17} className="spin" /> : <UserPlus size={17} />}
          {saving ? 'Creando cuenta…' : 'Crear cliente'}
        </button>
      </form>
      <div className="customer-toolbar">
        <h2>
          Clientes registrados <span className="customer-badge">{total}</span>
        </h2>
        {loading && (
          <span className="customer-meta" role="status">
            <LoaderCircle className="spin" size={16} /> Actualizando…
          </span>
        )}
      </div>
      {!loading && !displayed.length ? (
        <div className="customer-empty">
          <Users size={26} />
          <p>
            {error
              ? 'No se pudo consultar la lista. Vuelve a intentar.'
              : 'Todavía no hay clientes. Crea la primera cuenta con el formulario.'}
          </p>
        </div>
      ) : (
        <div className="customer-list" aria-busy={loading}>
          {displayed.map((customer) => (
            <article key={customer.id} className="customer-card">
              <div>
                <h3>{customer.name}</h3>
                <p>{customer.email}</p>
              </div>
              <div className="customer-meta">
                <span className="customer-badge">Cliente</span>
                <time dateTime={customer.created_at}>
                  Creado el{' '}
                  {new Date(customer.created_at).toLocaleDateString('es', { dateStyle: 'medium' })}
                </time>
              </div>
            </article>
          ))}
        </div>
      )}
      {total > PAGE_SIZE && (
        <nav className="customer-pagination" aria-label="Páginas de clientes">
          <button
            className="secondary-button"
            disabled={loading || saving || offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          >
            <ArrowLeft size={16} /> Anterior
          </button>
          <span className="customer-meta">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} de {total}
          </span>
          <button
            className="secondary-button"
            disabled={loading || saving || offset + PAGE_SIZE >= total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Siguiente <ArrowRight size={16} />
          </button>
        </nav>
      )}
    </section>
  );
}

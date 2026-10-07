import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowRight,
  Check,
  ChevronRight,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import type { SyntheticEvent } from 'react';
import App from './App';
import { api, errorMessage } from './api';
import { logoutSession, refreshSession, setAccessToken } from './auth';
import { ActionsProvider } from './actions';
import type { CompanyIdentity, Config, User } from './types';
import { SiteLink } from './navigation';
import { companyPresentation } from './company';

function AuthScreen({
  setup,
  config,
  identity,
  onAuthenticated,
  initialError,
}: {
  setup: boolean;
  config: Config | null;
  identity: CompanyIdentity | null;
  onAuthenticated: (user: User) => void;
  initialError: string;
}) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialError);
  const submitting = useRef(false);
  const creating = setup || mode === 'register';
  const { company, assistant, humanizar, website } = companyPresentation(config, identity);
  const brand = (
    <>
      <Sparkles size={29} strokeWidth={1.4} />
      <span>
        {assistant}
        <i>.</i>
      </span>
    </>
  );

  async function submit(event: SyntheticEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError('');
    try {
      const result = await api.authenticate(setup ? 'setup' : mode, {
        email: email.trim(),
        password,
        ...(creating ? { name: name.trim() } : {}),
      });
      setAccessToken(result.access_token);
      setPassword('');
      onAuthenticated(result.user);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return (
    <div className="auth-layout">
      <section className="auth-story">
        {website ? (
          <a href={website} target="_blank" rel="noopener noreferrer" className="auth-brand">
            {brand}
          </a>
        ) : (
          <div className="auth-brand">{brand}</div>
        )}
        <div className="auth-editorial">
          <span className="page-eyebrow">
            <span className="status-dot" />{' '}
            {humanizar ? 'SOFTWARE. AGENTES. POSIBILIDADES.' : 'INFORMACIÓN. AYUDA. CONVERSACIÓN.'}
          </span>
          <h1>
            Las buenas preguntas
            <br />
            abren <span>nuevos caminos.</span>
          </h1>
          <p>
            Conoce los productos de {company}, encuentra la solución para tu empresa y da el
            siguiente paso con un asistente que conecta la información.
          </p>
          <div className="auth-orbit" aria-hidden="true">
            <svg viewBox="0 0 300 240" fill="none">
              <g stroke="#86c4af" strokeWidth=".65">
                <ellipse cx="150" cy="120" rx="105" ry="82" />
                <ellipse cx="150" cy="120" rx="70" ry="82" />
                <ellipse cx="150" cy="120" rx="32" ry="82" />
                <ellipse cx="150" cy="120" rx="105" ry="29" />
                <ellipse cx="150" cy="120" rx="105" ry="57" />
                <ellipse cx="150" cy="120" rx="44" ry="105" transform="rotate(50 150 120)" />
                <ellipse cx="150" cy="120" rx="44" ry="105" transform="rotate(-50 150 120)" />
              </g>
              <path
                d="m150 89 8.5 22.5L181 120l-22.5 8.5L150 151l-8.5-22.5L119 120l22.5-8.5Z"
                fill="#c3ecd9"
              />
              <circle cx="66" cy="74" r="4" fill="#a8e5cd" />
              <circle cx="239" cy="162" r="3" fill="#aaa2d2" />
            </svg>
            <span className="orbit-chip chip-one">
              <Sparkles size={13} /> {humanizar ? 'Agentes a medida' : 'Información de la empresa'}
            </span>
            <span className="orbit-chip chip-two">
              <Check size={13} /> Respuestas con fuentes
            </span>
          </div>
        </div>
        <div className="auth-story-footer">
          <span>
            {company} · {humanizar ? 'Tecnología que resuelve.' : 'Información que conecta.'}
          </span>
          {website && (
            <a href={website} target="_blank" rel="noopener noreferrer">
              Conoce {company} <ChevronRight size={12} />
            </a>
          )}
        </div>
      </section>
      <main className="auth-form-panel">
        <div className="auth-form-wrap">
          <span className="auth-welcome-icon">
            <LockKeyhole size={23} />
          </span>
          <div className="auth-eyebrow">
            {setup ? 'PRIMER PASO · ADMINISTRACIÓN' : 'TU CONVERSACIÓN EMPIEZA AQUÍ'}
          </div>
          <h2>
            {setup
              ? 'Prepara tu espacio.'
              : creating
                ? 'Un espacio para tus ideas.'
                : 'Qué bueno verte.'}
          </h2>
          <p className="auth-subtitle">
            {setup
              ? 'Crea la primera cuenta de administrador para configurar el asistente.'
              : creating
                ? 'Crea tu cuenta para conversar y dar seguimiento a tus solicitudes.'
                : 'Entra para continuar tus conversaciones y consultar tus solicitudes.'}
          </p>
          {!setup && (
            <div className="auth-tabs" role="tablist" aria-label="Acceso a la cuenta">
              <button
                id="auth-tab-login"
                role="tab"
                aria-controls="auth-panel"
                aria-selected={mode === 'login'}
                tabIndex={mode === 'login' ? 0 : -1}
                disabled={busy}
                onKeyDown={(event) => {
                  if (['ArrowLeft', 'ArrowRight', 'End'].includes(event.key)) {
                    event.preventDefault();
                    setMode('register');
                    setError('');
                    document.getElementById('auth-tab-register')?.focus();
                  }
                }}
                onClick={() => {
                  setMode('login');
                  setError('');
                }}
                className={mode === 'login' ? 'selected' : ''}
              >
                Entrar
              </button>
              <button
                id="auth-tab-register"
                role="tab"
                aria-controls="auth-panel"
                aria-selected={mode === 'register'}
                tabIndex={mode === 'register' ? 0 : -1}
                disabled={busy}
                onKeyDown={(event) => {
                  if (['ArrowLeft', 'ArrowRight', 'Home'].includes(event.key)) {
                    event.preventDefault();
                    setMode('login');
                    setError('');
                    document.getElementById('auth-tab-login')?.focus();
                  }
                }}
                onClick={() => {
                  setMode('register');
                  setError('');
                }}
                className={mode === 'register' ? 'selected' : ''}
              >
                Crear cuenta
              </button>
            </div>
          )}
          <form
            id="auth-panel"
            role={setup ? undefined : 'tabpanel'}
            aria-labelledby={setup ? undefined : `auth-tab-${mode}`}
            className="auth-form"
            onSubmit={(event) => void submit(event)}
          >
            {creating && (
              <>
                <label htmlFor="auth-name">Tu nombre</label>
                <input
                  id="auth-name"
                  name="name"
                  autoComplete="name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  required
                  minLength={2}
                  maxLength={100}
                  placeholder="¿Cómo te llamas?"
                />
              </>
            )}
            <label htmlFor="auth-email">Correo electrónico</label>
            <input
              id="auth-email"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              maxLength={254}
              placeholder="tu@empresa.com"
            />
            <label htmlFor="auth-password">Contraseña</label>
            <input
              id="auth-password"
              name="password"
              type="password"
              autoComplete={creating ? 'new-password' : 'current-password'}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={creating ? 6 : 1}
              maxLength={128}
              placeholder={creating ? 'Al menos 6 caracteres' : 'Tu contraseña'}
            />
            {creating && (
              <span className="auth-password-hint">
                Usa al menos 6 caracteres para proteger tu cuenta.
              </span>
            )}
            {error && (
              <div className="notice error" role="alert">
                {error}
              </div>
            )}
            <button className="primary-button auth-submit" disabled={busy}>
              {busy ? <LoaderCircle size={17} className="spin" /> : <ArrowRight size={17} />}
              {busy
                ? 'Un momento…'
                : setup
                  ? 'Crear administrador'
                  : creating
                    ? 'Crear mi cuenta'
                    : 'Entrar a mi espacio'}
            </button>
          </form>
          <p className="auth-security">
            <ShieldCheck size={14} /> Tu sesión se mantiene con una cookie protegida. Tus
            conversaciones pertenecen a tu cuenta.
          </p>
        </div>
        <div className="auth-form-footer">
          <span>Información clara. Decisiones con contexto.</span>
          <SiteLink href="/docs">
            Cómo está construido
            <ChevronRight size={12} />
          </SiteLink>
        </div>
      </main>
    </div>
  );
}

export default function SessionApp() {
  const [user, setUser] = useState<User | null>(null);
  const [setup, setSetup] = useState(false);
  const [config, setConfig] = useState<Config | null>(null);
  const [identity, setIdentity] = useState<CompanyIdentity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [unavailable, setUnavailable] = useState(false);
  const bootstrapRevision = useRef(0);

  const bootstrap = useCallback(async () => {
    const revision = ++bootstrapRevision.current;
    setLoading(true);
    setError('');
    setUnavailable(false);
    try {
      const status = await api.authStatus();
      if (revision !== bootstrapRevision.current) return;
      setSetup(status.setup_required);
      try {
        const configuration = await api.config();
        if (revision !== bootstrapRevision.current) return;
        setConfig(configuration);
      } catch {
        /* Brand fallback is available offline. */
      }
      try {
        const company = await api.company();
        if (revision !== bootstrapRevision.current) return;
        setIdentity(company);
      } catch {
        /* Older APIs retain the configured company presentation. */
      }
      if (revision !== bootstrapRevision.current) return;
      if (!status.setup_required) {
        const session = await refreshSession();
        if (revision !== bootstrapRevision.current) return;
        if (session) {
          const account = await api.me();
          if (revision === bootstrapRevision.current) setUser(account);
        }
      }
    } catch (err) {
      if (revision === bootstrapRevision.current) {
        setError(errorMessage(err));
        setUnavailable(true);
      }
    } finally {
      if (revision === bootstrapRevision.current) setLoading(false);
    }
  }, []);

  const invalidateBootstrap = useCallback(() => {
    bootstrapRevision.current++;
  }, []);
  useEffect(() => {
    void bootstrap();
    return invalidateBootstrap;
  }, [bootstrap, invalidateBootstrap]);
  useEffect(() => {
    const expired = () => {
      setUser(null);
      setAccessToken(null);
      setError('Tu sesión terminó. Entra de nuevo para continuar.');
    };
    window.addEventListener('humanizar-session-expired', expired);
    return () => window.removeEventListener('humanizar-session-expired', expired);
  }, []);

  async function logout(): Promise<void> {
    try {
      await logoutSession();
      setError('');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUser(null);
    }
  }

  if (loading)
    return (
      <main className="session-loading">
        <Sparkles size={35} strokeWidth={1.3} />
        <strong>{companyPresentation(config, identity).assistant}</strong>
        <span>
          <LoaderCircle size={14} className="spin" />
          Preparando tu espacio…
        </span>
      </main>
    );
  if (unavailable)
    return (
      <main className="session-loading">
        <ShieldCheck size={35} />
        <strong>No pudimos conectar</strong>
        <p>{error}</p>
        <button className="primary-button" onClick={() => void bootstrap()}>
          Reintentar
          <ArrowRight size={16} />
        </button>
      </main>
    );
  if (!user)
    return (
      <AuthScreen
        key={setup ? 'setup' : 'auth'}
        setup={setup}
        config={config}
        identity={identity}
        onAuthenticated={(account) => {
          setSetup(false);
          setUser(account);
        }}
        initialError={error}
      />
    );
  return (
    <ActionsProvider key={user.id}>
      <App user={user} onLogout={logout} />
    </ActionsProvider>
  );
}

import { useRef, useState } from 'react';
import type { SyntheticEvent } from 'react';
import { ArrowRight, ChevronRight, LoaderCircle, LockKeyhole, ShieldCheck } from 'lucide-react';
import { api, errorMessage } from '../../shared/api/api';
import { setAccessToken } from '../../shared/api/auth';
import type { CompanyIdentity, Config, User } from '../../shared/api/types';
import { companyPresentation } from '../../shared/config/company';
import { SiteLink } from '../../shared/routing/navigation';
import { AuthStory } from './AuthStory';
import { AuthTabs } from './AuthTabs';
import type { AuthMode } from './AuthTabs';

export function AuthScreen({
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
  const [mode, setMode] = useState<AuthMode>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialError);
  const submitting = useRef(false);
  const creating = setup || mode === 'register';
  const { company, assistant, humanizar, website } = companyPresentation(config, identity);

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
      <AuthStory assistant={assistant} company={company} humanizar={humanizar} website={website} />
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
            <AuthTabs
              mode={mode}
              busy={busy}
              onSelect={(next) => {
                setMode(next);
                setError('');
              }}
            />
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

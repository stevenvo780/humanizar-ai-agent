import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowRight, LoaderCircle, ShieldCheck, Sparkles } from 'lucide-react';
import { AuthScreen } from '../features/auth/AuthScreen';
import { ActionsProvider } from '../features/requests/actions';
import { api, errorMessage } from '../shared/api/api';
import { logoutSession, refreshSession, setAccessToken } from '../shared/api/auth';
import type { CompanyIdentity, Config, User } from '../shared/api/types';
import { companyPresentation } from '../shared/config/company';
import App from './App';

export default function SessionApp() {
  const [user, setUser] = useState<User | null>(null);
  const [setup, setSetup] = useState(false);
  const [config, setConfig] = useState<Config | null>(null);
  const [identity, setIdentity] = useState<CompanyIdentity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [unavailable, setUnavailable] = useState(false);
  const bootstrapRevision = useRef(0);
  const { assistant, company } = companyPresentation(config, identity);
  const branded = config !== null || identity !== null;

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

  useEffect(() => {
    document.title = branded ? `${assistant} — ${company}` : 'Asistente de atención al cliente';
  }, [assistant, company, branded]);

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
        <strong>{assistant}</strong>
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

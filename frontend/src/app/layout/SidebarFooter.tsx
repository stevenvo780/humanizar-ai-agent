import { ArrowUpRight, CircleHelp, Code2, LogOut } from 'lucide-react';
import type { Config, User } from '../../shared/api/types';
import { SiteLink } from '../../shared/routing/navigation';

export function SidebarFooter({
  config,
  user,
  isAdmin,
  company,
  onHelp,
  onLogout,
}: {
  config: Config | null;
  user: User;
  isAdmin: boolean;
  company: string;
  onHelp: () => void;
  onLogout: () => Promise<void>;
}) {
  return (
    <div className="sidebar-bottom">
      <div className="connection-card">
        <p>
          {config
            ? config.mode === 'demo'
              ? 'Modo demo · Sin llamadas a Claude'
              : config.mode === 'anthropic'
                ? `${config.model} · Anthropic`
                : `${config.model} · Modo ${config.mode}`
            : 'Esperando la configuración'}
        </p>
        <span>
          {config?.embedding === 'hash'
            ? 'Vectores léxicos'
            : config
              ? `Embeddings: ${config.embedding}`
              : 'Conexión segura con la API'}
        </span>
      </div>
      <button
        className="help-button"
        onClick={() => {
          onHelp();
        }}
      >
        <CircleHelp size={16} />
        <span>Cómo usar el asistente</span>
        <ArrowUpRight size={13} />
      </button>
      <SiteLink href="/docs" className="technical-docs-link">
        <Code2 size={15} />
        <span>Documentación técnica</span>
        <ArrowUpRight size={12} />
      </SiteLink>
      <div className="profile">
        <span className="profile-avatar">{user.name.slice(0, 1).toUpperCase()}</span>
        <div>
          <strong>{user.name}</strong>
          <span>{isAdmin ? 'Administrador' : `Cliente de ${company}`}</span>
        </div>
        <button className="icon-button" aria-label="Cerrar sesión" onClick={() => void onLogout()}>
          <LogOut size={16} />
        </button>
      </div>
    </div>
  );
}

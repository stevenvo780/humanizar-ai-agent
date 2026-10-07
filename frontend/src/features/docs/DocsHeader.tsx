import { ArrowUpRight, Globe2, Sparkles } from 'lucide-react';
import { SiteLink } from '../../shared/routing/navigation';

export function DocsHeader({ assistant }: { assistant: string }) {
  return (
    <header className="docs-header">
      <SiteLink href="/" className="docs-brand">
        <Sparkles size={25} strokeWidth={1.4} />
        <strong>
          {assistant}
          <span>.</span>
        </strong>
        <span className="docs-header-divider" />
        <span className="docs-header-label">Ingeniería, a la vista</span>
      </SiteLink>
      <div className="docs-header-actions">
        <span className="docs-public-badge">
          <Globe2 size={12} /> Documentación pública
        </span>
        <SiteLink href="/" className="docs-return">
          Abrir asistente
          <ArrowUpRight size={14} />
        </SiteLink>
      </div>
    </header>
  );
}

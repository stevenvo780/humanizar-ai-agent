import { ArrowUpRight, Globe2, Link2, Presentation, Sparkles } from 'lucide-react';
import type { RefObject } from 'react';
import { SiteLink } from '../../shared/routing/navigation';

export function DocsHeader({
  assistant,
  presenting,
  onTogglePresentation,
  presentRef,
}: {
  assistant: string;
  presenting: boolean;
  onTogglePresentation: () => void;
  presentRef: RefObject<HTMLButtonElement | null>;
}) {
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
        <a href="#recursos" className="docs-header-link">
          <Link2 size={14} /> Recursos
        </a>
        <button
          ref={presentRef}
          type="button"
          className="docs-present-toggle"
          aria-pressed={presenting}
          onClick={onTogglePresentation}
        >
          <Presentation size={15} />
          <span className="docs-present-text">Presentar</span>
        </button>
        <SiteLink href="/" className="docs-return">
          <span className="docs-return-long">Abrir asistente</span>
          <span className="docs-return-short">Asistente</span>
          <ArrowUpRight size={14} />
        </SiteLink>
      </div>
    </header>
  );
}

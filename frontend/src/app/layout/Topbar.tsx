import type { RefObject } from 'react';
import { ChevronRight, Menu, ShieldCheck } from 'lucide-react';
import type { AssistantMode } from '../../shared/api/types';
import { StatusDot } from '../../shared/ui/StatusDot';

export function Topbar({
  toggleRef,
  drawerOpen,
  onOpenNavigation,
  company,
  sectionLabel,
  online,
  loading,
  mode,
}: {
  toggleRef: RefObject<HTMLButtonElement | null>;
  drawerOpen: boolean;
  onOpenNavigation: () => void;
  company: string;
  sectionLabel: string;
  online: boolean;
  loading: boolean;
  mode: AssistantMode | undefined;
}) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <button
          className="icon-button mobile-menu-toggle"
          ref={toggleRef}
          aria-label="Abrir navegación"
          aria-controls="workspace-navigation"
          aria-expanded={drawerOpen}
          onClick={() => onOpenNavigation()}
        >
          <Menu size={20} />
        </button>
        <span className="breadcrumb">
          <span className="breadcrumb-root">Asistente de {company}</span>
          <ChevronRight size={12} aria-hidden="true" />
          <strong id="workspace-section-title">{sectionLabel}</strong>
        </span>
      </div>
      <div className="topbar-right">
        <span className="private-badge">
          <ShieldCheck size={13} /> Tu espacio
        </span>
        <span className={`mode-pill ${!online ? 'offline' : ''}`}>
          <StatusDot online={online} />
          {loading
            ? 'Conectando'
            : !online
              ? 'Sin conexión'
              : mode === 'demo'
                ? 'Modo demo'
                : 'En línea'}
        </span>
      </div>
    </header>
  );
}

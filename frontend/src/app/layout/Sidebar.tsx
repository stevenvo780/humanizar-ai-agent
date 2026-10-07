import type { ReactNode, RefObject } from 'react';
import { Plus, X } from 'lucide-react';
import type { WorkspaceSection } from '../../shared/api/types';
import { BrandMark } from '../../shared/ui/BrandMark';
import type { WorkspaceNavigationItem } from '../workspaceNavigation';

/** Workspace navigation: a fixed column on desktop and a modal drawer on mobile. */
export function Sidebar({
  navigationRef,
  drawerOpen,
  inert,
  onClose,
  assistant,
  company,
  onHome,
  onNewConversation,
  newConversationDisabled,
  navigationItems,
  section,
  onSelectSection,
  documentCount,
  children,
}: {
  navigationRef: RefObject<HTMLElement | null>;
  drawerOpen: boolean;
  inert: boolean;
  onClose: () => void;
  assistant: string;
  company: string;
  onHome: () => void;
  onNewConversation: () => void;
  newConversationDisabled: boolean;
  navigationItems: readonly WorkspaceNavigationItem[];
  section: WorkspaceSection;
  onSelectSection: (section: WorkspaceSection) => void;
  documentCount: number;
  children: ReactNode;
}) {
  return (
    <>
      {drawerOpen && (
        <button className="sidebar-overlay" onClick={onClose} aria-label="Cerrar menú" />
      )}
      <aside
        id="workspace-navigation"
        ref={navigationRef}
        className={`sidebar ${drawerOpen ? 'sidebar-open' : ''}`}
        aria-label="Navegación principal"
        role={drawerOpen ? 'dialog' : undefined}
        aria-modal={drawerOpen ? true : undefined}
        inert={inert}
      >
        <button
          className="icon-button mobile-menu-close"
          aria-label="Cerrar navegación"
          onClick={onClose}
        >
          <X size={20} />
        </button>
        <button
          className="brand"
          onClick={() => {
            onHome();
          }}
        >
          <BrandMark />
          <span
            style={{
              fontSize: assistant.length > 10 ? 20 : 29,
              letterSpacing: assistant.length > 10 ? '-0.6px' : '-1.6px',
            }}
          >
            {assistant}
            <span className="brand-period">.</span>
          </span>
        </button>
        <div className="workspace-identity">
          <span className="workspace-avatar">
            {company.slice(0, 1).toUpperCase()}
            <span />
          </span>
          <span>
            <strong>{company}</strong>
            <small>Atención al cliente</small>
          </span>
        </div>
        <button className="new-chat" onClick={onNewConversation} disabled={newConversationDisabled}>
          <Plus size={17} />
          <span>Nueva conversación</span>
          <span className="new-shortcut" aria-hidden="true">
            ↗
          </span>
        </button>
        <div className="sidebar-section-label">EXPLORA</div>
        <nav className="sidebar-navigation" aria-label="Secciones del espacio">
          {navigationItems.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${section === item.id ? 'active' : ''}`}
              onClick={() => onSelectSection(item.id)}
              aria-current={section === item.id ? 'page' : undefined}
            >
              <item.icon size={17} />
              <span>{item.label}</span>
              {item.id === 'knowledge' && documentCount > 0 && (
                <span className="nav-count">{documentCount}</span>
              )}
              {item.id === 'assistant' && <span className="nav-active-dot" />}
            </button>
          ))}
        </nav>
        {children}
      </aside>
    </>
  );
}

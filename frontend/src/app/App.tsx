import { useState } from 'react';
import { ChatAnnouncement } from '../features/chat/ChatAnnouncement';
import { ChatWorkspace } from '../features/chat/ChatWorkspace';
import { EvidencePanel } from '../features/chat/EvidencePanel';
import { RecentConversations } from '../features/chat/RecentConversations';
import { useChat } from '../features/chat/useChat';
import { CustomersPanel } from '../features/customers/CustomersPanel';
import { Knowledge } from '../features/documents/Knowledge';
import { RequestsPanel } from '../features/requests/RequestsPanel';
import { ToolsPanel } from '../features/tools/ToolsPanel';
import type { WorkspaceSection, User } from '../shared/api/types';
import { useWorkspaceData } from './hooks/useWorkspaceData';
import { useWorkspaceOverlays } from './hooks/useWorkspaceOverlays';
import { HelpModal } from './layout/HelpModal';
import { Sidebar } from './layout/Sidebar';
import { SidebarFooter } from './layout/SidebarFooter';
import { Topbar } from './layout/Topbar';
import { WorkspaceNotices } from './layout/WorkspaceNotices';
import { workspaceNavigation } from './workspaceNavigation';

export default function App({ user, onLogout }: { user: User; onLogout: () => Promise<void> }) {
  const isAdmin = user.role === 'admin';
  const overlays = useWorkspaceOverlays();
  const { isMobile, drawerOpen, showHelp, closeNavigation } = overlays;
  const [selectedSection, setSelectedSection] = useState<WorkspaceSection>('assistant');
  const workspace = useWorkspaceData(isAdmin);
  const { config, health, documents, online, loading } = workspace;
  const { company, assistant, prompts } = workspace.presentation;
  const chat = useChat({
    userId: user.id,
    online,
    assistant,
    onOffline: workspace.markOffline,
  });

  function selectSection(next: WorkspaceSection): void {
    setSelectedSection(next);
    closeNavigation();
  }
  function newConversation(): void {
    if (chat.startNewConversation()) selectSection('assistant');
  }

  const navigationItems = workspaceNavigation({
    isAdmin,
    customerManagement: health?.features?.customer_management === true,
  });
  const activeNavigation =
    navigationItems.find((item) => item.id === selectedSection) ?? navigationItems[0];
  const section = activeNavigation.id;

  return (
    <div className="app-shell">
      <ChatAnnouncement message={chat.announcement} />
      <a className="skip-link" href="#main-content" inert={drawerOpen || showHelp}>
        Saltar al contenido
      </a>
      <Sidebar
        navigationRef={overlays.navigationRef}
        drawerOpen={drawerOpen}
        inert={(isMobile && !drawerOpen) || showHelp}
        onClose={closeNavigation}
        assistant={assistant}
        company={company}
        onHome={() => selectSection('assistant')}
        onNewConversation={newConversation}
        newConversationDisabled={chat.busy || chat.historyLoading}
        navigationItems={navigationItems}
        section={section}
        onSelectSection={selectSection}
        documentCount={documents.documents.length}
      >
        <RecentConversations
          conversations={chat.conversations}
          activeId={chat.activeId}
          busy={chat.busy}
          onOpen={(id) => {
            chat.selectConversation(id);
            selectSection('assistant');
          }}
          onRemove={chat.removeConversation}
        />
        <SidebarFooter
          config={config}
          user={user}
          isAdmin={isAdmin}
          company={company}
          onHelp={overlays.openHelp}
          onLogout={onLogout}
        />
      </Sidebar>
      <div className="workspace-main" inert={drawerOpen || showHelp}>
        <Topbar
          toggleRef={overlays.navigationToggleRef}
          drawerOpen={drawerOpen}
          onOpenNavigation={overlays.openNavigation}
          company={company}
          sectionLabel={activeNavigation.label}
          online={online}
          loading={loading}
          mode={config?.mode}
        />
        <div className="main-columns">
          <main
            className={`main-content ${section === 'assistant' ? 'assistant-main' : ''}`}
            id="main-content"
            tabIndex={-1}
          >
            <WorkspaceNotices
              online={online}
              loading={loading}
              connectionError={workspace.connectionError}
              storageError={chat.storageError}
              onRetry={workspace.refresh}
            />
            <section
              aria-labelledby="workspace-section-title"
              className={`workspace-content ${section === 'assistant' ? 'chat-panel' : ''}`}
            >
              {section === 'assistant' && (
                <ChatWorkspace
                  chat={chat}
                  online={online}
                  config={config}
                  assistant={assistant}
                  company={company}
                  prompts={prompts}
                  userName={user.name}
                />
              )}
              {section === 'knowledge' && isAdmin && (
                <Knowledge
                  documents={documents}
                  refresh={workspace.refreshDocuments}
                  maxUpload={config?.max_upload_mb ?? 20}
                  online={online}
                  readerAvailable={health?.features?.document_reading === true}
                />
              )}
              {section === 'tools' && isAdmin && (
                <ToolsPanel tools={workspace.tools} online={online} health={health} />
              )}
              {section === 'customers' && isAdmin && <CustomersPanel />}
              {section === 'requests' && (
                <RequestsPanel isAdmin={isAdmin} onChat={() => selectSection('assistant')} />
              )}
            </section>
          </main>
          {section === 'assistant' && (
            <EvidencePanel
              documents={documents}
              company={company}
              selected={chat.selected}
              busy={chat.busy}
              onKnowledge={() => selectSection('knowledge')}
              isAdmin={isAdmin}
            />
          )}
        </div>
      </div>
      {showHelp && (
        <HelpModal
          dialogRef={overlays.helpRef}
          onClose={overlays.closeHelp}
          company={company}
          assistant={assistant}
          isAdmin={isAdmin}
          demoMode={config?.mode === 'demo'}
        />
      )}
    </div>
  );
}

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clock3,
  Code2,
  FileText,
  Menu,
  MessageSquare,
  LogOut,
  Plus,
  ShieldCheck,
  Sparkles,
  Terminal,
  WandSparkles,
  WifiOff,
  X,
} from 'lucide-react';
import { ChatAnnouncement, completedChatAnnouncement } from '../features/chat/ChatAnnouncement';
import { Composer } from '../features/chat/Composer';
import { EvidencePanel } from '../features/chat/EvidencePanel';
import { SourceCard } from '../features/chat/SourceCard';
import { Trace } from '../features/chat/Trace';
import { CustomersPanel } from '../features/customers/CustomersPanel';
import { ChatMarkdown } from '../features/documents/DocumentMarkdown';
import { Knowledge } from '../features/documents/Knowledge';
import { RequestsPanel } from '../features/requests/RequestsPanel';
import { ToolsPanel } from '../features/tools/ToolsPanel';
import { api, errorMessage, streamChat } from '../shared/api/api';
import type {
  ChatMessage,
  Config,
  CompanyIdentity,
  Conversation,
  DocumentList,
  Health,
  WorkspaceSection,
  ToolDefinition,
  User,
} from '../shared/api/types';
import { companyPresentation } from '../shared/config/company';
import { useDialogFocus } from '../shared/hooks/useDialogFocus';
import { SiteLink } from '../shared/routing/navigation';
import { StatusDot } from '../shared/ui/StatusDot';
import { createId } from '../shared/utils/id';
import { plural } from '../shared/utils/plural';
import { workspaceNavigation } from './workspaceNavigation';

const EMPTY_MESSAGES: ChatMessage[] = [];

const MOBILE_NAVIGATION = '(max-width: 760px)';
const promptStyles = [
  { icon: BookOpen, color: 'mint' },
  { icon: WandSparkles, color: 'lavender' },
  { icon: FileText, color: 'peach' },
  { icon: Code2, color: 'blue' },
];

function subscribeMobileNavigation(listener: () => void): () => void {
  const query = window.matchMedia(MOBILE_NAVIGATION);
  query.addEventListener('change', listener);
  return () => query.removeEventListener('change', listener);
}

function mobileNavigationSnapshot(): boolean {
  return window.matchMedia(MOBILE_NAVIGATION).matches;
}
function BrandMark({ small = false }: { small?: boolean }) {
  return (
    <span className={`brand-mark ${small ? 'brand-mark-small' : ''}`} aria-hidden="true">
      <Sparkles strokeWidth={1.5} />
    </span>
  );
}

function Orb() {
  return (
    <div className="orb-wrap" aria-hidden="true">
      <div className="orb-halo" />
      <svg className="orb" viewBox="0 0 144 144" fill="none">
        <defs>
          <radialGradient id="orb-fill">
            <stop stopColor="#74d6bb" stopOpacity=".2" />
            <stop offset="1" stopColor="#74d6bb" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="orb-stroke" x1="30" y1="15" x2="120" y2="125">
            <stop stopColor="#b6f3de" />
            <stop offset=".5" stopColor="#6dccad" />
            <stop offset="1" stopColor="#576cbe" />
          </linearGradient>
        </defs>
        <circle cx="72" cy="72" r="53" fill="url(#orb-fill)" />
        <g stroke="url(#orb-stroke)" strokeWidth=".8" opacity=".8">
          <circle cx="72" cy="72" r="51" />
          <ellipse cx="72" cy="72" rx="24" ry="51" />
          <ellipse cx="72" cy="72" rx="42" ry="51" />
          <ellipse cx="72" cy="72" rx="51" ry="17" />
          <ellipse cx="72" cy="72" rx="51" ry="35" />
          <ellipse cx="72" cy="72" rx="25" ry="51" transform="rotate(55 72 72)" />
          <ellipse cx="72" cy="72" rx="25" ry="51" transform="rotate(-55 72 72)" />
          <path d="M21 72h102M72 21v102M36 36l72 72M36 108l72-72" opacity=".35" />
        </g>
        <path d="m72 52 5.3 14.7L92 72l-14.7 5.3L72 92l-5.3-14.7L52 72l14.7-5.3Z" fill="#c9f7e6" />
        <circle cx="29" cy="45" r="2.5" fill="#aaf3d7" />
        <circle cx="116" cy="96" r="2" fill="#a8b4ed" />
        <circle cx="104" cy="32" r="1.5" fill="#aaf3d7" />
      </svg>
      <span className="orb-dot orb-dot-one" />
      <span className="orb-dot orb-dot-two" />
    </div>
  );
}

export default function App({ user, onLogout }: { user: User; onLogout: () => Promise<void> }) {
  const [selectedSection, setSelectedSection] = useState<WorkspaceSection>('assistant');
  const [config, setConfig] = useState<Config | null>(null);
  const [identity, setIdentity] = useState<CompanyIdentity | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [documents, setDocuments] = useState<DocumentList>({ documents: [], total_chunks: 0 });
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [online, setOnline] = useState(false);
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [streamStatus, setStreamStatus] = useState('');
  const [announcement, setAnnouncement] = useState('');
  const [mobileMenu, setMobileMenu] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [storageError, setStorageError] = useState('');
  const abortRef = useRef<AbortController | null>(null);
  const busyRef = useRef(false);
  const messagesEnd = useRef<HTMLDivElement>(null);
  const helpRef = useRef<HTMLElement>(null);
  const navigationRef = useRef<HTMLElement>(null);
  const navigationToggleRef = useRef<HTMLButtonElement>(null);
  const closeNavigation = useCallback(() => setMobileMenu(false), []);
  const closeHelp = useCallback(() => setShowHelp(false), []);
  const subscribeNavigation = useCallback(
    (listener: () => void) =>
      subscribeMobileNavigation(() => {
        closeNavigation();
        listener();
      }),
    [closeNavigation],
  );
  const isMobile = useSyncExternalStore(subscribeNavigation, mobileNavigationSnapshot);
  const drawerOpen = isMobile && mobileMenu;
  useDialogFocus(navigationRef, drawerOpen, closeNavigation, navigationToggleRef);
  useDialogFocus(helpRef, showHelp, closeHelp, isMobile ? navigationToggleRef : undefined);
  const active = conversations.find((item) => item.id === activeId);
  const messages = active?.messages ?? EMPTY_MESSAGES;
  const { company, assistant, humanizar, prompts } = companyPresentation(config, identity);
  const selected = [...messages].reverse().find((item) => item.role === 'assistant');
  const isAdmin = user.role === 'admin';

  const refreshDocuments = useCallback(async () => {
    setDocuments(await api.documents());
  }, []);
  const refresh = useCallback(async () => {
    setLoading(true);
    const results = await Promise.allSettled([
      api.config(),
      api.health(),
      isAdmin ? api.documents() : Promise.resolve({ documents: [], total_chunks: 0 }),
      isAdmin ? api.tools() : Promise.resolve({ tools: [] }),
      api.company(),
    ]);
    const [configuration, healthResult, documentResult, toolResult, companyResult] = results;
    if (configuration.status === 'fulfilled') setConfig(configuration.value);
    if (companyResult.status === 'fulfilled') setIdentity(companyResult.value);
    if (healthResult.status === 'fulfilled') {
      setHealth(healthResult.value);
      setOnline(true);
      setConnectionError('');
    } else {
      setOnline(false);
      setConnectionError('El servidor no está disponible.');
    }
    if (documentResult.status === 'fulfilled') setDocuments(documentResult.value);
    if (toolResult.status === 'fulfilled') setTools(toolResult.value.tools);
    if (
      configuration.status === 'rejected' ||
      documentResult.status === 'rejected' ||
      toolResult.status === 'rejected'
    )
      setConnectionError('No se pudo cargar toda la información. Vuelve a intentar.');
    setLoading(false);
  }, [isAdmin]);

  useEffect(() => {
    void refresh();
  }, [refresh]);
  useEffect(() => {
    document.title = `${assistant} — ${company}`;
  }, [assistant, company]);
  useEffect(() => {
    const check = async () => {
      try {
        const result = await api.health();
        setHealth(result);
        setOnline(true);
      } catch {
        setOnline(false);
      }
    };
    const reconnect = () => {
      void refresh();
    };
    const disconnect = () => setOnline(false);
    window.addEventListener('online', reconnect);
    window.addEventListener('offline', disconnect);
    const interval = window.setInterval(() => {
      void check();
    }, 20000);
    return () => {
      window.removeEventListener('online', reconnect);
      window.removeEventListener('offline', disconnect);
      window.clearInterval(interval);
      abortRef.current?.abort();
    };
  }, [refresh]);
  useEffect(() => {
    let current = true;
    setHistoryLoading(true);
    setConversations([]);
    setActiveId(null);
    void api
      .conversations()
      .then((result) => {
        if (current) {
          setConversations(result.conversations);
          setStorageError('');
        }
      })
      .catch((err: unknown) => {
        if (current)
          setStorageError(`No pudimos cargar el historial de tu cuenta. ${errorMessage(err)}`);
      })
      .finally(() => {
        if (current) setHistoryLoading(false);
      });
    return () => {
      current = false;
    };
  }, [user.id]);
  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: busy ? 'instant' : 'smooth', block: 'end' });
  }, [messages, busy]);
  function selectSection(next: WorkspaceSection): void {
    setSelectedSection(next);
    setMobileMenu(false);
  }
  function newConversation(): void {
    if (busyRef.current) return;
    setActiveId(null);
    setDraft('');
    selectSection('assistant');
  }
  async function removeConversation(id: string): Promise<void> {
    try {
      await api.deleteConversation(id);
      setConversations((current) => current.filter((chat) => chat.id !== id));
      if (activeId === id) setActiveId(null);
    } catch (err) {
      setStorageError(errorMessage(err));
    }
  }
  function updateMessage(
    conversationId: string,
    messageId: string,
    update: (message: ChatMessage) => ChatMessage,
  ): void {
    setConversations((current) =>
      current.map((item) =>
        item.id === conversationId
          ? {
              ...item,
              messages: item.messages.map((message) =>
                message.id === messageId ? update(message) : message,
              ),
            }
          : item,
      ),
    );
  }

  async function send(text: string): Promise<void> {
    if (!text.trim() || busyRef.current || !online || historyLoading) return;
    const message = text.trim();
    const conversationId = activeId ?? createId();
    const assistantId = createId();
    const userMessage: ChatMessage = {
      id: createId(),
      role: 'user',
      content: message,
      sources: [],
      trace: [],
    };
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      sources: [],
      trace: [],
    };
    const history: { role: 'user' | 'assistant'; content: string }[] = [];
    let historyCharacters = 0;
    for (const item of [...messages].reverse()) {
      if (!item.content || item.error) continue;
      if (history.length >= 40 || historyCharacters + item.content.length > 32000) break;
      history.unshift({ role: item.role, content: item.content });
      historyCharacters += item.content.length;
    }
    setConversations((current) =>
      activeId
        ? current.map((item) =>
            item.id === conversationId
              ? {
                  ...item,
                  messages: [...item.messages, userMessage, assistantMessage],
                  updatedAt: Date.now(),
                }
              : item,
          )
        : [
            {
              id: conversationId,
              title: message.slice(0, 44),
              messages: [userMessage, assistantMessage],
              updatedAt: Date.now(),
            },
            ...current,
          ].slice(0, 20),
    );
    setActiveId(conversationId);
    setDraft('');
    setBusy(true);
    setAnnouncement('');
    busyRef.current = true;
    setStreamStatus('Buscando el contexto adecuado…');
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await streamChat(
        message,
        history,
        active?.sessionId ?? conversationId,
        controller.signal,
        (event) => {
          if (event.type === 'status') setStreamStatus(event.message);
          if (event.type === 'token')
            updateMessage(conversationId, assistantId, (item) => ({
              ...item,
              content: item.content + event.text,
            }));
          if (event.type === 'tool')
            updateMessage(conversationId, assistantId, (item) => ({
              ...item,
              trace: [...item.trace.filter((trace) => trace.id !== event.trace.id), event.trace],
            }));
          if (event.type === 'done') {
            setAnnouncement(completedChatAnnouncement(event.response, assistant));
            updateMessage(conversationId, assistantId, (item) => ({
              ...item,
              content: event.response.answer,
              sources: event.response.sources,
              trace: event.response.trace,
            }));
            setConversations((current) =>
              current.map((item) =>
                item.id === conversationId
                  ? { ...item, sessionId: event.response.session_id }
                  : item,
              ),
            );
          }
        },
      );
    } catch (err) {
      updateMessage(conversationId, assistantId, (item) => ({
        ...item,
        error: controller.signal.aborted
          ? 'Respuesta detenida. Puedes enviar otro mensaje.'
          : errorMessage(err),
      }));
      if (!controller.signal.aborted) {
        try {
          await api.health();
        } catch {
          setOnline(false);
        }
      }
    } finally {
      setBusy(false);
      busyRef.current = false;
      setStreamStatus('');
      abortRef.current = null;
    }
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
      <ChatAnnouncement message={announcement} />
      <a className="skip-link" href="#main-content" inert={drawerOpen || showHelp}>
        Saltar al contenido
      </a>
      {drawerOpen && (
        <button className="sidebar-overlay" onClick={closeNavigation} aria-label="Cerrar menú" />
      )}
      <aside
        id="workspace-navigation"
        ref={navigationRef}
        className={`sidebar ${drawerOpen ? 'sidebar-open' : ''}`}
        aria-label="Navegación principal"
        role={drawerOpen ? 'dialog' : undefined}
        aria-modal={drawerOpen ? true : undefined}
        inert={(isMobile && !drawerOpen) || showHelp}
      >
        <button
          className="icon-button mobile-menu-close"
          aria-label="Cerrar navegación"
          onClick={closeNavigation}
        >
          <X size={20} />
        </button>
        <button
          className="brand"
          onClick={() => {
            selectSection('assistant');
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
        <button className="new-chat" onClick={newConversation} disabled={busy || historyLoading}>
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
              onClick={() => selectSection(item.id)}
              aria-current={section === item.id ? 'page' : undefined}
            >
              <item.icon size={17} />
              <span>{item.label}</span>
              {item.id === 'knowledge' && documents.documents.length > 0 && (
                <span className="nav-count">{documents.documents.length}</span>
              )}
              {item.id === 'assistant' && <span className="nav-active-dot" />}
            </button>
          ))}
        </nav>
        <div className="recent-heading">
          <span className="sidebar-section-label">CONVERSACIONES</span>
          <Clock3 size={12} />
        </div>
        <div className="recent-list">
          {conversations.slice(0, 7).map((item) => (
            <div className={`recent-item ${activeId === item.id ? 'selected' : ''}`} key={item.id}>
              <button
                disabled={busy}
                onClick={() => {
                  setActiveId(item.id);
                  selectSection('assistant');
                }}
              >
                <MessageSquare size={14} />
                <span>{item.title}</span>
              </button>
              <button
                className="remove-chat"
                disabled={busy}
                aria-label={`Eliminar conversación ${item.title}`}
                onClick={() => void removeConversation(item.id)}
              >
                <X size={12} />
              </button>
            </div>
          ))}
          {conversations.length === 0 && (
            <p className="recent-empty">
              Estamos para ayudarte.
              <br />
              Las conversaciones se guardan
              <br />
              en tu cuenta.
            </p>
          )}
        </div>
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
              closeNavigation();
              setShowHelp(true);
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
            <button
              className="icon-button"
              aria-label="Cerrar sesión"
              onClick={() => void onLogout()}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>
      <div className="workspace-main" inert={drawerOpen || showHelp}>
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="icon-button mobile-menu-toggle"
              ref={navigationToggleRef}
              aria-label="Abrir navegación"
              aria-controls="workspace-navigation"
              aria-expanded={drawerOpen}
              onClick={() => setMobileMenu(true)}
            >
              <Menu size={20} />
            </button>
            <span className="breadcrumb">
              <span className="breadcrumb-root">Asistente de {company}</span>
              <ChevronRight size={12} aria-hidden="true" />
              <strong id="workspace-section-title">{activeNavigation.label}</strong>
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
                  : config?.mode === 'demo'
                    ? 'Modo demo'
                    : 'En línea'}
            </span>
          </div>
        </header>
        <div className="main-columns">
          <main
            className={`main-content ${section === 'assistant' ? 'assistant-main' : ''}`}
            id="main-content"
            tabIndex={-1}
          >
            {((!online && !loading) || connectionError) && (
              <div className="offline-banner" role="status">
                <WifiOff size={16} />
                <span>
                  {!online
                    ? 'No podemos conectar con el servidor. Tu historial sigue aquí.'
                    : connectionError}
                </span>
                <button onClick={() => void refresh()} disabled={loading}>
                  {loading ? 'Conectando…' : 'Reintentar'}
                </button>
              </div>
            )}
            {storageError && (
              <div className="notice error" role="status">
                {storageError}
              </div>
            )}
            <section
              aria-labelledby="workspace-section-title"
              className={`workspace-content ${section === 'assistant' ? 'chat-panel' : ''}`}
            >
              {section === 'assistant' && (
                <>
                  {messages.length === 0 ? (
                    <section className="welcome">
                      <div className="welcome-eyebrow">
                        <span /> RESPUESTAS CLARAS. DECISIONES MÁS FÁCILES.
                      </div>
                      <Orb />
                      <div className="welcome-heading">
                        <span className="greeting">Hola, soy {assistant}.</span>
                        <h1>
                          Todo sobre {company},
                          <br />
                          <span>en una conversación.</span>
                        </h1>
                        <p>
                          {humanizar
                            ? 'Descubre servicios, explora agentes de IA y resuelve tus dudas.'
                            : 'Descubre productos y servicios y resuelve tus dudas con fuentes.'}
                          <br className="desktop-break" /> Te ayudamos a dar el siguiente paso.
                        </p>
                      </div>
                      {prompts.length > 0 && (
                        <>
                          <div className="prompt-section-heading">
                            <span>¿Cómo podemos ayudarte?</span>
                            <ArrowDown size={13} />
                          </div>
                          <div className="prompt-grid">
                            {prompts.map((prompt, index) => {
                              const style = promptStyles[index % promptStyles.length] ?? {
                                icon: BookOpen,
                                color: 'mint',
                              };
                              return (
                                <button
                                  className="prompt-card"
                                  key={`${index}-${prompt.question}`}
                                  disabled={!online || busy || historyLoading}
                                  onClick={() => void send(prompt.question)}
                                >
                                  <span className={`prompt-icon ${style.color}`}>
                                    <style.icon size={19} strokeWidth={1.7} />
                                  </span>
                                  <strong>{prompt.title}</strong>
                                  <p>{prompt.subtitle}</p>
                                  <ArrowUpRight className="prompt-arrow" size={17} />
                                </button>
                              );
                            })}
                          </div>
                        </>
                      )}
                    </section>
                  ) : (
                    <section className="conversation" aria-label="Conversación" aria-busy={busy}>
                      <div className="conversation-heading">
                        <span>
                          <MessageSquare size={14} />
                          {active?.title}
                        </span>
                        <span className="local-label">Historial de tu cuenta</span>
                      </div>
                      {messages.map((message) => (
                        <article className={`message message-${message.role}`} key={message.id}>
                          <div className="message-avatar">
                            {message.role === 'assistant' ? (
                              <BrandMark small />
                            ) : (
                              user.name.slice(0, 1).toUpperCase()
                            )}
                          </div>
                          <div className="message-content">
                            <div className="message-byline">
                              <strong>
                                {message.role === 'assistant' ? assistant : user.name}
                              </strong>
                              {message.role === 'assistant' && <span>Asistente de {company}</span>}
                            </div>
                            {message.content ? (
                              <ChatMarkdown content={message.content} />
                            ) : (
                              !message.error && (
                                <div className="thinking">
                                  <span />
                                  <span />
                                  <span />
                                  <p>{streamStatus || 'Preparando una respuesta…'}</p>
                                </div>
                              )
                            )}
                            {message.error && (
                              <div className="message-error" role="alert">
                                {message.error}
                              </div>
                            )}
                            {message.sources.length > 0 && (
                              <div className="message-sources">
                                <span>
                                  <BookOpen size={12} />
                                  {plural(
                                    message.sources.length,
                                    'fuente consultada',
                                    'fuentes consultadas',
                                  )}
                                </span>
                                {message.sources.map((source, index) => (
                                  <SourceCard
                                    key={`${source.chunk_id}-${index}`}
                                    source={source}
                                    index={index}
                                  />
                                ))}
                              </div>
                            )}
                            {message.trace.length > 0 && (
                              <details className="message-tools">
                                <summary>
                                  <Terminal size={12} />
                                  {plural(
                                    message.trace.length,
                                    'herramienta ejecutada',
                                    'herramientas ejecutadas',
                                  )}
                                  <ChevronDown size={12} />
                                </summary>
                                {message.trace.map((trace) => (
                                  <Trace key={trace.id} trace={trace} />
                                ))}
                              </details>
                            )}
                          </div>
                        </article>
                      ))}
                      <div ref={messagesEnd} />
                    </section>
                  )}
                  <Composer
                    draft={draft}
                    setDraft={setDraft}
                    onSend={send}
                    busy={busy}
                    onStop={() => abortRef.current?.abort()}
                    online={online && !historyLoading}
                    config={config}
                    conversation={messages.length > 0}
                  />
                </>
              )}
              {section === 'knowledge' && isAdmin && (
                <Knowledge
                  documents={documents}
                  refresh={refreshDocuments}
                  maxUpload={config?.max_upload_mb ?? 20}
                  online={online}
                  readerAvailable={health?.features?.document_reading === true}
                />
              )}
              {section === 'tools' && isAdmin && (
                <ToolsPanel tools={tools} online={online} health={health} />
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
              selected={selected}
              busy={busy}
              onKnowledge={() => selectSection('knowledge')}
              isAdmin={isAdmin}
            />
          )}
        </div>
      </div>
      {showHelp && (
        <div className="modal-backdrop">
          <section
            className="help-modal"
            ref={helpRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="help-title"
          >
            <button
              className="icon-button modal-close"
              aria-label="Cerrar ayuda"
              onClick={() => setShowHelp(false)}
            >
              <X size={20} />
            </button>
            <BrandMark />
            <h2 id="help-title">
              Conoce {company}.
              <br />
              Resuelve tus dudas con {assistant}.
            </h2>
            <p>
              Pregunta por productos, servicios
              {humanizar ? ', agentes de IA o demostraciones' : ' o ayuda'}. El asistente consulta
              la documentación de la empresa y puede usar herramientas para ayudarte. Abre las
              fuentes para revisar la información de cada respuesta.
            </p>
            <p>
              En <strong>Mis solicitudes</strong> puedes revisar las demostraciones y los tickets de
              soporte que confirmaste.{' '}
              {isAdmin &&
                'Desde tu cuenta de administrador también puedes gestionar la documentación y las herramientas.'}
            </p>
            <p className="help-detail">
              {config?.mode === 'demo'
                ? 'Este asistente está en modo demo: las respuestas son de demostración y no llaman a Claude. Los documentos y las herramientas usan la API real.'
                : 'La información del modelo y el estado de las conexiones aparecen en la barra lateral.'}{' '}
              El historial se guarda en tu cuenta.
            </p>
            <button className="primary-button" onClick={() => setShowHelp(false)}>
              Empezar a explorar
              <ArrowRight size={16} />
            </button>
          </section>
        </div>
      )}
    </div>
  );
}

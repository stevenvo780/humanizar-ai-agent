import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import type { ChangeEvent, SyntheticEvent, KeyboardEvent, ReactNode } from 'react';
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  ArrowUpRight,
  BookOpen,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clock3,
  Code2,
  FileText,
  FolderOpen,
  Layers3,
  LoaderCircle,
  Menu,
  MessageSquare,
  LogOut,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Square,
  Terminal,
  Trash2,
  UploadCloud,
  WandSparkles,
  WifiOff,
  X,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { api, errorMessage, streamChat } from './api';
import { createId } from './id';
import { ActionConfirmation, actionProposal, useConfirmedAction } from './actions';
import { RequestsPanel } from './AccountPanels';
import { CustomersPanel } from './CustomersPanel';
import { SiteLink } from './navigation';
import { workspaceNavigation } from './workspaceNavigation';
import { useDialogFocus } from './useDialogFocus';
import type {
  ChatMessage,
  Config,
  Conversation,
  DocumentList,
  Health,
  KnowledgeDocument,
  Source,
  WorkspaceSection,
  ToolDefinition,
  ToolTrace,
  User,
} from './types';

const EMPTY_MESSAGES: ChatMessage[] = [];
const MOBILE_NAVIGATION = '(max-width: 760px)';

function subscribeMobileNavigation(listener: () => void): () => void {
  const query = window.matchMedia(MOBILE_NAVIGATION);
  query.addEventListener('change', listener);
  return () => query.removeEventListener('change', listener);
}

function mobileNavigationSnapshot(): boolean {
  return window.matchMedia(MOBILE_NAVIGATION).matches;
}
const prompts = [
  {
    icon: BookOpen,
    color: 'mint',
    title: 'Productos y servicios',
    subtitle: 'Productos y servicios para ti.',
    question: '¿Qué productos y servicios ofrece {company}?',
  },
  {
    icon: WandSparkles,
    color: 'lavender',
    title: 'Agentes de IA a medida',
    subtitle: 'Explora cómo pueden ayudarte.',
    question: '¿Cómo funcionan los agentes de IA a medida de {company}?',
  },
  {
    icon: FileText,
    color: 'peach',
    title: 'Hablemos de tu proyecto',
    subtitle: 'Contacto y solicitud de demostración.',
    question: '¿Cómo puedo contactar a {company} para solicitar una demostración?',
  },
  {
    icon: Code2,
    color: 'blue',
    title: 'Conoce Cauce V3',
    subtitle: 'Pregunta por la plataforma.',
    question: '¿Qué es Cauce V3?',
  },
];

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

function StatusDot({ online }: { online: boolean }) {
  return <span className={`status-dot ${online ? '' : 'status-dot-offline'}`} />;
}

function EmptyState({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">{icon}</span>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}

function Trace({ trace }: { trace: ToolTrace }) {
  const proposal = actionProposal(trace);
  const confirmed = useConfirmedAction(trace.id);
  return (
    <details className={`trace-detail ${proposal ? 'trace-proposal' : ''}`} open={!!proposal}>
      <summary>
        <span className={`trace-status ${trace.status}`}>
          <Terminal size={14} />
        </span>
        <span>
          {proposal
            ? confirmed
              ? 'Solicitud registrada'
              : 'Pendiente de confirmar'
            : toolLabel(trace.tool)}
        </span>
        <span className="trace-time">{trace.duration_ms} ms</span>
        <ChevronDown size={13} />
      </summary>
      <div className="trace-body">
        {proposal ? (
          <ActionConfirmation trace={trace} />
        ) : (
          <>
            <div className="mini-label">Entrada</div>
            <pre>{JSON.stringify(trace.input, null, 2)}</pre>
            <div className="mini-label">
              {trace.status === 'error' ? 'Error de ejecución' : 'Resultado'}
            </div>
            <pre>{trace.output}</pre>
          </>
        )}
      </div>
    </details>
  );
}

function toolLabel(name: string): string {
  const labels: Record<string, string> = {
    search_knowledge: 'Buscar documentación',
    calculate: 'Calculadora',
    terminal: 'Terminal aislada',
    mcp_company_info: 'Información de empresa · MCP',
    recommend_product: 'Recomendar producto',
    create_demo_request: 'Solicitar demostración',
    create_support_ticket: 'Crear ticket de soporte',
    list_my_requests: 'Consultar mis solicitudes',
  };
  return labels[name] ?? name;
}

function SourceCard({ source, index }: { source: Source; index: number }) {
  return (
    <details className="source-card">
      <summary>
        <span className="source-number">{index + 1}</span>
        <span className="source-name">
          {source.document_name}
          <small>Fragmento consultado</small>
        </span>
        <ChevronDown size={14} />
      </summary>
      <div className="source-excerpt">
        <p>{source.text}</p>
        <span>Referencia: {source.chunk_id}</span>
      </div>
    </details>
  );
}

function EvidencePanel({
  documents,
  company,
  selected,
  busy,
  onKnowledge,
  isAdmin,
}: {
  documents: DocumentList;
  company: string;
  selected: ChatMessage | undefined;
  busy: boolean;
  onKnowledge: () => void;
  isAdmin: boolean;
}) {
  const sources = selected?.sources ?? [];
  const trace = selected?.trace ?? [];
  return (
    <aside className="evidence-panel" aria-label="Contexto y fuentes">
      <div className="panel-heading">
        <span>FUENTES DE INFORMACIÓN</span>
        <Layers3 size={15} />
      </div>
      <div className="context-company">
        <span className="context-company-icon">
          {company.slice(0, 1).toUpperCase()}
          <span />
        </span>
        <div>
          <strong>Documentación de {company}</strong>
          <p>Información para decidir con claridad.</p>
        </div>
      </div>
      <div className="context-stat">
        <span>
          <StatusDot online />
          {isAdmin
            ? `${documents.documents.length} documentos disponibles`
            : sources.length
              ? `${sources.length} fuentes consultadas`
              : 'Respuestas con documentación'}
        </span>
        <span>
          {isAdmin
            ? `${documents.total_chunks} fragmentos`
            : 'Explora las referencias de cada respuesta'}
        </span>
      </div>
      <div className="panel-section-heading">
        <h2>{sources.length ? 'Fuentes de esta respuesta' : 'Información de la empresa'}</h2>
        {sources.length > 0 && <span className="count-badge">{sources.length}</span>}
      </div>
      {sources.length ? (
        <div className="source-list">
          {sources.map((source, index) => (
            <SourceCard key={`${source.chunk_id}-${index}`} source={source} index={index} />
          ))}
        </div>
      ) : (
        <div className="library-list">
          {documents.documents.slice(0, 4).map((doc) => (
            <button className="library-item" key={doc.id} onClick={onKnowledge}>
              <span className="file-icon">
                <FileText size={17} />
              </span>
              <span>
                {doc.name}
                <small>{doc.chunks} fragmentos · Disponible para consultar</small>
              </span>
              <ChevronRight size={13} />
            </button>
          ))}
          {documents.documents.length === 0 && (
            <p className="panel-empty-copy">
              Las fuentes consultadas aparecerán junto a cada respuesta.
            </p>
          )}
          {isAdmin && (
            <button className="text-link library-link" onClick={onKnowledge}>
              {documents.documents.length ? 'Ver documentación' : 'Administrar fuentes'}
              <ArrowUpRight size={14} />
            </button>
          )}
        </div>
      )}
      <div className="panel-rule" />
      <div className="panel-section-heading">
        <h2>{trace.length ? 'Actividad de herramientas' : 'De la pregunta a la claridad'}</h2>
        {busy && <LoaderCircle size={14} className="spin" />}
      </div>
      {trace.length > 0 ? (
        <div className="trace-list">
          {trace.map((item) => (
            <Trace key={item.id} trace={item} />
          ))}
        </div>
      ) : (
        <div className="how-list">
          <div>
            <span>01</span>
            <p>
              <strong>Encuentra el contexto</strong>
              <small>Consulta la documentación de la empresa.</small>
            </p>
          </div>
          <div>
            <span>02</span>
            <p>
              <strong>Conecta la información</strong>
              <small>Usa las herramientas que necesita.</small>
            </p>
          </div>
          <div>
            <span>03</span>
            <p>
              <strong>Responde con fuentes</strong>
              <small>Podés explorar cada referencia.</small>
            </p>
          </div>
        </div>
      )}
      <div className="trust-card">
        <ShieldCheck size={19} />
        <div>
          <strong>Claridad, también en el proceso.</strong>
          <p>Respuestas conectadas a la documentación de la empresa. Explora cada fuente.</p>
        </div>
      </div>
      <div className="panel-bottom">
        <span className="tiny-star">✦</span> Menos buscar. Más avanzar.
      </div>
    </aside>
  );
}

function Knowledge({
  documents,
  refresh,
  maxUpload,
  online,
}: {
  documents: DocumentList;
  refresh: () => Promise<void>;
  maxUpload: number;
  online: boolean;
}) {
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function upload(files: FileList | File[]): Promise<void> {
    if (uploading || !online) return;
    setUploading(true);
    setError('');
    setNotice('');
    const skipped: string[] = [];
    const errors: string[] = [];
    let uploaded = 0;
    for (const file of Array.from(files)) {
      if (file.size > maxUpload * 1024 * 1024) {
        errors.push(`${file.name}: supera ${maxUpload} MB.`);
        continue;
      }
      try {
        const result = await api.upload(file);
        uploaded += result.documents.length;
        skipped.push(...result.skipped);
      } catch (err) {
        errors.push(`${file.name}: ${errorMessage(err)}`);
      }
    }
    try {
      await refresh();
    } catch (err) {
      errors.push(errorMessage(err));
    }
    if (uploaded)
      setNotice(
        `${uploaded} documento${uploaded === 1 ? '' : 's'} procesado${uploaded === 1 ? '' : 's'}.${skipped.length ? ` Archivos omitidos: ${skipped.join(', ')}` : ''}`,
      );
    else if (skipped.length) setNotice(`Archivos omitidos: ${skipped.join(', ')}`);
    setError(errors.join(' '));
    setUploading(false);
    if (inputRef.current) inputRef.current.value = '';
  }

  async function remove(id: string): Promise<void> {
    setDeleting(id);
    setError('');
    try {
      await api.deleteDocument(id);
      await refresh();
      setDeleteId(null);
      setNotice('Documento eliminado de la biblioteca de la empresa.');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setDeleting(null);
    }
  }

  return (
    <section className="workspace-page" aria-labelledby="knowledge-title">
      <div className="page-eyebrow">
        <BookOpen size={15} /> ADMINISTRACIÓN · DOCUMENTACIÓN
      </div>
      <h1 id="knowledge-title">
        Información de la empresa.
        <br />
        <span>En un solo lugar.</span>
      </h1>
      <p className="page-intro">
        Añade archivos Markdown (.md) con información de tu empresa. El asistente los consultará al
        responder a los clientes.
        <br className="desktop-break" /> También puedes subir otros formatos o varios documentos
        juntos.
      </p>
      <div className="knowledge-summary">
        <div>
          <FolderOpen size={19} />
          <span>
            <strong>{documents.documents.length}</strong> documentos
          </span>
        </div>
        <div>
          <Layers3 size={19} />
          <span>
            <strong>{documents.total_chunks}</strong> fragmentos consultables
          </span>
        </div>
      </div>
      <div
        className={`upload-zone ${dragging ? 'dragging' : ''}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          void upload(event.dataTransfer.files);
        }}
      >
        <span className="upload-icon">
          {uploading ? <LoaderCircle className="spin" size={26} /> : <UploadCloud size={26} />}
        </span>
        <h2>
          {uploading ? 'Procesando la documentación…' : 'Un nuevo archivo. Mejores respuestas.'}
        </h2>
        <p>
          Arrastra documentos de la empresa aquí o{' '}
          <button
            className="text-link"
            disabled={uploading || !online}
            onClick={() => inputRef.current?.click()}
          >
            selecciona archivos
          </button>
        </p>
        <button
          className="primary-button"
          disabled={uploading || !online}
          onClick={() => inputRef.current?.click()}
        >
          <UploadCloud size={18} /> {uploading ? 'Procesando archivos…' : 'Añadir documentos'}
        </button>
        <span className="upload-formats">
          TXT, MD, PDF, DOCX, CSV, JSON y ZIP · Hasta {maxUpload} MB por archivo
        </span>
        <input
          className="sr-only"
          id="document-upload"
          ref={inputRef}
          type="file"
          multiple
          accept=".txt,.md,.pdf,.docx,.csv,.json,.zip"
          aria-label="Seleccionar documentos para subir"
          disabled={uploading || !online}
          onChange={(event: ChangeEvent<HTMLInputElement>) => {
            if (event.target.files) void upload(event.target.files);
          }}
        />
      </div>
      {notice && (
        <div className="notice success" role="status">
          <CheckCheck size={17} />
          {notice}
        </div>
      )}
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
      <div className="document-heading">
        <h2>
          Biblioteca de la empresa <span>{documents.documents.length}</span>
        </h2>
        <span>Disponible para el asistente</span>
      </div>
      {documents.documents.length ? (
        <div className="document-list">
          {documents.documents.map((doc: KnowledgeDocument) => (
            <div className="document-row" key={doc.id}>
              <span className="document-icon">
                <FileText size={22} />
              </span>
              <div className="document-info">
                <strong>{doc.name}</strong>
                <span>
                  {doc.chunks} fragmentos · {doc.characters.toLocaleString('es')} caracteres
                </span>
              </div>
              {deleteId === doc.id ? (
                <div className="delete-confirm">
                  <span>¿Eliminar?</span>
                  <button
                    className="danger-link"
                    disabled={!!deleting}
                    onClick={() => void remove(doc.id)}
                  >
                    {deleting === doc.id ? 'Eliminando…' : 'Confirmar'}
                  </button>
                  <button
                    className="icon-button"
                    aria-label="Cancelar eliminación"
                    onClick={() => setDeleteId(null)}
                  >
                    <X size={16} />
                  </button>
                </div>
              ) : (
                <>
                  <span className="ready-badge">
                    <Check size={12} />
                    Indexado
                  </span>
                  <button
                    className="icon-button delete-button"
                    aria-label={`Eliminar ${doc.name}`}
                    disabled={!online}
                    onClick={() => setDeleteId(doc.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      ) : (
        <EmptyState icon={<BookOpen size={24} />} title="Prepara las fuentes del asistente">
          Los documentos de la empresa aparecerán aquí después de subirlos.
        </EmptyState>
      )}
      <p className="page-footnote">
        <ShieldCheck size={13} /> Los ZIP se procesan sin extraer archivos al sistema anfitrión.
      </p>
    </section>
  );
}

function Tools({
  tools,
  online,
  health,
}: {
  tools: ToolDefinition[];
  online: boolean;
  health: Health | null;
}) {
  const [selected, setSelected] = useState('calculate');
  const [value, setValue] = useState('(120 + 80) * 2');
  const [preset, setPreset] = useState('pwd');
  const [running, setRunning] = useState(false);
  const runningRef = useRef(false);
  const [result, setResult] = useState<ToolTrace | null>(null);
  const [error, setError] = useState('');
  const definition = tools.find((tool) => tool.name === selected);
  const [businessInput, setBusinessInput] = useState<Record<string, string>>({});
  const [writeConfirmed, setWriteConfirmed] = useState(false);
  const writeTool = selected === 'create_demo_request' || selected === 'create_support_ticket';
  const fields: string[] =
    selected === 'create_demo_request'
      ? ['name', 'email', 'company', 'interest', 'needs']
      : selected === 'create_support_ticket'
        ? ['subject', 'description']
        : [];
  const fieldLabels: Record<string, string> = {
    name: 'Nombre del contacto',
    email: 'Correo del contacto',
    company: 'Empresa',
    interest: 'Producto o servicio de interés',
    needs: 'Necesidad o proceso',
    subject: 'Asunto',
    description: 'Descripción',
  };
  const icons: Record<string, ReactNode> = {
    calculate: <Code2 size={21} />,
    terminal: <Terminal size={21} />,
    search_knowledge: <Search size={21} />,
    mcp_company_info: <Layers3 size={21} />,
  };

  async function run(event: SyntheticEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (runningRef.current || !online || !definition?.enabled) return;
    runningRef.current = true;
    setRunning(true);
    setError('');
    setResult(null);
    const input: Record<string, unknown> =
      selected === 'calculate'
        ? { expression: value }
        : selected === 'search_knowledge'
          ? { query: value }
          : selected === 'recommend_product'
            ? { process: value }
            : writeTool
              ? businessInput
              : selected === 'terminal'
                ? { command: preset }
                : {};
    try {
      setResult(await api.runTool(selected, input, writeTool && writeConfirmed));
      if (writeTool && writeConfirmed)
        window.dispatchEvent(new Event('humanizar-requests-changed'));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      runningRef.current = false;
      setRunning(false);
      setWriteConfirmed(false);
    }
  }

  return (
    <section className="workspace-page" aria-labelledby="tools-title">
      <div className="page-eyebrow">
        <WandSparkles size={15} /> ADMINISTRACIÓN · HERRAMIENTAS
      </div>
      <h1 id="tools-title">
        Una respuesta puede
        <br />
        <span>hacer mucho más.</span>
      </h1>
      <p className="page-intro">
        Prueba las herramientas que el asistente puede usar para ayudarte.
        <br className="desktop-break" /> Comprueba las integraciones y sus resultados reales.
      </p>
      <div className="tool-grid">
        {tools.map((tool) => (
          <button
            className={`tool-card ${selected === tool.name ? 'selected' : ''}`}
            key={tool.name}
            aria-pressed={selected === tool.name}
            disabled={running}
            onClick={() => {
              setSelected(tool.name);
              setValue(tool.name === 'calculate' ? '(120 + 80) * 2' : 'servicios de la empresa');
              setResult(null);
              setError('');
              setBusinessInput({});
              setWriteConfirmed(false);
            }}
          >
            <span className="tool-card-top">
              <span className="tool-icon">{icons[tool.name] ?? <Code2 size={21} />}</span>
              <span className={`tool-enabled ${tool.enabled ? '' : 'unavailable'}`}>
                <StatusDot online={tool.enabled} />
                {tool.enabled ? 'Habilitada' : 'No disponible'}
              </span>
            </span>
            <strong>{toolLabel(tool.name)}</strong>
            <p>{tool.description}</p>
            <span className="tool-card-link">
              Explorar herramienta <ArrowUpRight size={14} />
            </span>
          </button>
        ))}
      </div>
      {!tools.length && (
        <EmptyState icon={<WandSparkles size={24} />} title="Sin herramientas disponibles">
          La lista se actualizará cuando el servidor esté conectado.
        </EmptyState>
      )}
      {definition && (
        <form className="tool-playground" onSubmit={(event) => void run(event)}>
          <div className="playground-heading">
            <span className="mini-label">PRUEBA LA HERRAMIENTA</span>
            <h2>{toolLabel(selected)}</h2>
          </div>
          {selected === 'terminal' ? (
            <>
              <label htmlFor="tool-command">Comando permitido</label>
              <select
                id="tool-command"
                value={preset}
                onChange={(event) => setPreset(event.target.value)}
              >
                <option>pwd</option>
                <option>ls</option>
                <option>date</option>
                <option>python --version</option>
                <option>wc</option>
              </select>
              <p className="field-help">
                Se ejecuta en el servicio aislado. Conexión:{' '}
                {health?.tools.sandbox ? 'disponible' : 'no disponible'}.
              </p>
            </>
          ) : selected === 'mcp_company_info' || selected === 'list_my_requests' ? (
            <p className="field-help">
              Esta consulta no requiere parámetros y devuelve información de la cuenta o empresa.
            </p>
          ) : writeTool ? (
            <>
              {fields.map((field) => (
                <div key={field}>
                  <label htmlFor={`tool-${field}`}>{fieldLabels[field] ?? field}</label>
                  <input
                    id={`tool-${field}`}
                    type={field === 'email' ? 'email' : 'text'}
                    value={businessInput[field] ?? ''}
                    onChange={(event) =>
                      setBusinessInput((current) => ({ ...current, [field]: event.target.value }))
                    }
                    required
                    maxLength={2000}
                    placeholder={fieldLabels[field] ?? field}
                  />
                </div>
              ))}
              <label className="tool-write-confirm">
                <input
                  type="checkbox"
                  checked={writeConfirmed}
                  onChange={(event) => setWriteConfirmed(event.target.checked)}
                />
                <span>
                  Confirmo que quiero registrar esta solicitud con los datos indicados. No se
                  enviarán mensajes externos.
                </span>
              </label>
            </>
          ) : (
            <>
              <label htmlFor="tool-input">
                {selected === 'calculate'
                  ? 'Expresión matemática'
                  : selected === 'recommend_product'
                    ? 'Proceso que necesitas resolver'
                    : 'Consulta de documentación'}
              </label>
              <input
                id="tool-input"
                value={value}
                onChange={(event) => setValue(event.target.value)}
                required
                placeholder={
                  selected === 'calculate' ? '(120 + 80) * 2' : '¿Qué quieres encontrar?'
                }
              />
            </>
          )}
          <button
            className="primary-button tool-run"
            disabled={
              running ||
              !online ||
              !definition.enabled ||
              (writeTool &&
                (!writeConfirmed || fields.some((field) => !businessInput[field]?.trim()))) ||
              (!writeTool &&
                selected !== 'terminal' &&
                selected !== 'mcp_company_info' &&
                selected !== 'list_my_requests' &&
                !value.trim())
            }
          >
            {running ? <LoaderCircle size={16} className="spin" /> : <ArrowRight size={16} />}
            {running
              ? 'Ejecutando…'
              : writeTool
                ? 'Confirmar y registrar solicitud'
                : 'Ejecutar herramienta'}
          </button>
          {error && (
            <div className="notice error" role="alert">
              {error}
            </div>
          )}
          {result && (
            <div className="tool-result" aria-live="polite">
              <div>
                <span className={result.status === 'error' ? 'result-error' : 'result-success'}>
                  {result.status === 'error'
                    ? 'La herramienta informó un error'
                    : 'Ejecución completada'}
                </span>
                <span>{result.duration_ms} ms</span>
              </div>
              <pre>{result.output}</pre>
            </div>
          )}
        </form>
      )}
    </section>
  );
}

function Composer({
  draft,
  setDraft,
  onSend,
  busy,
  onStop,
  online,
  config,
  conversation,
}: {
  draft: string;
  setDraft: (text: string) => void;
  onSend: (text: string) => Promise<void>;
  busy: boolean;
  onStop: () => void;
  online: boolean;
  config: Config | null;
  conversation: boolean;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 130)}px`;
    }
  }, [draft]);
  function submit(event: SyntheticEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (draft.trim() && !busy && online) {
      void onSend(draft);
    }
  }
  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>): void {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      if (draft.trim() && !busy && online) void onSend(draft);
    }
  }
  return (
    <div className={`composer-area ${conversation ? 'conversation-composer' : ''}`}>
      <form className="composer" onSubmit={submit}>
        <label className="sr-only" htmlFor="chat-message">
          Tu mensaje para {config?.assistant_name ?? 'el asistente'}
        </label>
        <textarea
          id="chat-message"
          ref={textareaRef}
          rows={1}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={keyDown}
          placeholder="Pregunta por servicios, agentes de IA o cómo podemos ayudarte…"
          maxLength={10000}
          disabled={!online}
        />
        <div className="composer-bottom">
          <span className="composer-context">
            <span>
              <BookOpen size={13} /> Información de {config?.company_name ?? 'la empresa'}
            </span>
            <ChevronDown size={12} />
          </span>
          <div className="composer-actions">
            <span className="keyboard-hint">↵ para enviar</span>
            {busy ? (
              <button
                type="button"
                className="send-button stop-button"
                onClick={onStop}
                aria-label="Detener respuesta"
              >
                <Square size={14} fill="currentColor" />
              </button>
            ) : (
              <button
                className="send-button"
                type="submit"
                aria-label="Enviar mensaje"
                disabled={!draft.trim() || !online}
              >
                <ArrowUp size={19} />
              </button>
            )}
          </div>
        </div>
      </form>
      <div className="composer-footnote">
        <ShieldCheck size={11} />
        <span>
          {config?.mode === 'demo'
            ? 'Modo demo · Respuestas de demostración, sin llamadas a Claude.'
            : config?.mode === 'anthropic'
              ? 'El asistente puede cometer errores. Consulta las fuentes de cada respuesta.'
              : 'Conectando con el asistente…'}
        </span>
        <span className="composer-powered">
          Hecho para pensar contigo <Sparkles size={10} />
        </span>
      </div>
    </div>
  );
}

export default function App({ user, onLogout }: { user: User; onLogout: () => Promise<void> }) {
  const [selectedSection, setSelectedSection] = useState<WorkspaceSection>('assistant');
  const [config, setConfig] = useState<Config | null>(null);
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
  const company = config?.company_name ?? 'Humanizar';
  const assistant = config?.assistant_name ?? 'Humanizar IA';
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
    ]);
    const [configuration, healthResult, documentResult, toolResult] = results;
    if (configuration.status === 'fulfilled') setConfig(configuration.value);
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
          <span className="new-shortcut">↗</span>
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
                  : `${config.model} · Anthropic`
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
              <span>{isAdmin ? 'Administrador' : 'Cliente de Humanizar'}</span>
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
              Asistente de {company}
              <ChevronRight size={12} />
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
                          Descubre servicios, explora agentes de IA y resuelve tus dudas.
                          <br className="desktop-break" /> Te ayudamos a dar el siguiente paso.
                        </p>
                      </div>
                      <div className="prompt-section-heading">
                        <span>¿Cómo podemos ayudarte?</span>
                        <ArrowDown size={13} />
                      </div>
                      <div className="prompt-grid">
                        {prompts.map((prompt) => (
                          <button
                            className="prompt-card"
                            key={prompt.title}
                            disabled={!online || busy || historyLoading}
                            onClick={() => void send(prompt.question.replace('{company}', company))}
                          >
                            <span className={`prompt-icon ${prompt.color}`}>
                              <prompt.icon size={19} strokeWidth={1.7} />
                            </span>
                            <strong>{prompt.title}</strong>
                            <p>{prompt.subtitle}</p>
                            <ArrowUpRight className="prompt-arrow" size={17} />
                          </button>
                        ))}
                      </div>
                    </section>
                  ) : (
                    <section className="conversation" aria-label="Conversación">
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
                              <div className="markdown">
                                <ReactMarkdown
                                  components={{
                                    a: ({ children, href }) => (
                                      <a href={href} target="_blank" rel="noopener noreferrer">
                                        {children}
                                        <ArrowUpRight size={12} />
                                      </a>
                                    ),
                                  }}
                                >
                                  {message.content}
                                </ReactMarkdown>
                              </div>
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
                                  {message.sources.length} fuentes consultadas
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
                                  {message.trace.length} herramientas ejecutadas
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
                />
              )}
              {section === 'tools' && isAdmin && (
                <Tools tools={tools} online={online} health={health} />
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
              Pregunta por productos, servicios, agentes de IA o demostraciones. El asistente
              consulta la documentación de la empresa y puede usar herramientas para ayudarte. Abre
              las fuentes para revisar la información de cada respuesta.
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

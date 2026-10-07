import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Boxes,
  Braces,
  Check,
  CheckCheck,
  ChevronRight,
  CircleDot,
  Code2,
  Database,
  FileCheck2,
  Fingerprint,
  GitBranch,
  Globe2,
  Layers3,
  LockKeyhole,
  MessageSquare,
  Network,
  ShieldCheck,
  Sparkles,
  Terminal,
  Workflow,
  Wrench,
} from 'lucide-react';
import { SiteLink } from './navigation';
import './docs.css';

const REPOSITORY_URL = 'https://github.com/stevenvo780/humanizar-ai-agent';
const sections = [
  { id: 'vision', label: 'El proyecto', icon: <BookOpen size={15} /> },
  { id: 'arquitectura', label: 'Arquitectura', icon: <Network size={15} /> },
  { id: 'agente', label: 'Cómo responde el agente', icon: <Workflow size={15} /> },
  { id: 'datos', label: 'Conocimiento y persistencia', icon: <Database size={15} /> },
  { id: 'seguridad', label: 'Acceso y seguridad', icon: <ShieldCheck size={15} /> },
  { id: 'herramientas', label: 'Herramientas e integraciones', icon: <Wrench size={15} /> },
  { id: 'calidad', label: 'Calidad y evidencia', icon: <FileCheck2 size={15} /> },
  { id: 'estado', label: 'Estado y límites', icon: <CircleDot size={15} /> },
  { id: 'empezar', label: 'Explorar el código', icon: <Code2 size={15} /> },
];

function Section({
  id,
  number,
  label,
  title,
  children,
}: {
  id: string;
  number: string;
  label: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="docs-section" id={id} tabIndex={-1} aria-labelledby={`${id}-title`}>
      <div className="docs-section-kicker">
        <span>{number}</span>
        {label}
      </div>
      <h2 id={`${id}-title`}>{title}</h2>
      {children}
    </section>
  );
}

function Architecture() {
  return (
    <figure className="docs-architecture">
      <figcaption>
        <span>
          <Network size={16} /> Un contrato claro entre cada pieza
        </span>
        <span>Vercel → VPS · REST + SSE</span>
      </figcaption>
      <div className="docs-diagram-scroll">
        <svg
          viewBox="0 0 760 390"
          role="img"
          aria-labelledby="architecture-title architecture-description"
        >
          <title id="architecture-title">Arquitectura de Humanizar IA</title>
          <desc id="architecture-description">
            React se sirve desde Vercel. Las llamadas REST y SSE del mismo origen pasan por un
            rewrite que añade una cabecera privada hacia FastAPI en Docker en el VPS. La API valida
            JWT, consulta PostgreSQL con TLS en el schema lumen, recupera evidencia de Qdrant local
            y coordina Claude Haiku y el sandbox aislado. SQLite es la alternativa local opcional.
            MCP consulta la misma API por HTTP. Este diagrama describe la configuración preparada;
            las comprobaciones del despliegue público se registran por separado.
          </desc>
          <defs>
            <marker
              id="docs-arrow"
              markerWidth="6"
              markerHeight="6"
              refX="5"
              refY="3"
              orient="auto"
            >
              <path d="M0 0 6 3 0 6" fill="none" stroke="#6f9484" />
            </marker>
          </defs>
          <g fill="none" stroke="#587e70" strokeWidth="1.2" markerEnd="url(#docs-arrow)">
            <path d="M164 90h48" />
            <path d="M362 90h54" />
            <path d="M502 120v42" />
            <path d="M502 120v20H285v22" />
            <path d="M285 218v49" />
            <path d="M362 298h32V190h22" />
            <path d="M285 298h131" />
            <path d="M164 298h23V38h315v22" strokeDasharray="4 5" />
          </g>
          <g className="diagram-labels" fill="#7b9a8b" fontSize="9">
            <text x="177" y="78">
              REST/SSE
            </text>
            <text x="376" y="78">
              HTTPS
            </text>
            <text x="300" y="132">
              agente
            </text>
            <text x="529" y="144">
              datos
            </text>
            <text x="375" y="178">
              persiste
            </text>
            <text x="299" y="247">
              tool_use
            </text>
            <text x="18" y="250">
              stdio · identidad por HTTP
            </text>
          </g>
          <g className="diagram-boxes">
            <rect x="14" y="60" width="150" height="60" rx="9" />
            <rect x="14" y="267" width="150" height="60" rx="9" />
            <rect x="212" y="60" width="150" height="60" rx="9" className="diagram-box-primary" />
            <rect x="416" y="60" width="173" height="60" rx="9" />
            <rect x="212" y="162" width="150" height="56" rx="9" className="diagram-box-lavender" />
            <rect x="416" y="162" width="173" height="56" rx="9" />
            <rect x="212" y="267" width="150" height="60" rx="9" />
            <rect x="416" y="267" width="173" height="60" rx="9" />
          </g>
          <g className="diagram-node-titles" fill="#d0e4d8" fontSize="12">
            <text x="32" y="85">
              React · Vercel
            </text>
            <text x="32" y="292">
              MCP read-only
            </text>
            <text x="230" y="85">
              Rewrite protegido
            </text>
            <text x="434" y="85">
              FastAPI · VPS Docker
            </text>
            <text x="230" y="185">
              Claude Haiku 4.5
            </text>
            <text x="434" y="185">
              PostgreSQL + Qdrant
            </text>
            <text x="230" y="292">
              Herramientas
            </text>
            <text x="434" y="292">
              Sandbox Docker
            </text>
          </g>
          <g fill="#819c8f" fontSize="9">
            <text x="32" y="104">
              TypeScript · Cliente web
            </text>
            <text x="32" y="311">
              Misma API · sin secretos
            </text>
            <text x="230" y="104">
              Mismo origen · header privado
            </text>
            <text x="434" y="104">
              JWT · roles · orquestación
            </text>
            <text x="230" y="203">
              Ciclo nativo y limitado
            </text>
            <text x="434" y="203">
              SQL con TLS · Qdrant local
            </text>
            <text x="230" y="311">
              Registro compartido
            </text>
            <text x="434" y="311">
              Presets · aislamiento
            </text>
          </g>
          <g fill="#658878" fontSize="8">
            <text x="14" y="376">
              SQLite opcional para desarrollo local. Secretos fuera del navegador.
            </text>
            <text x="416" y="376">
              La terminal solo ejecuta presets en su servicio aislado.
            </text>
          </g>
        </svg>
      </div>
      <p>
        El navegador conserva llamadas a <code>/api</code> en el mismo origen. El proxy añade la
        cabecera privada en el servidor; la API concentra permisos, recuperación, persistencia y
        ejecución. El modelo recibe resultados de herramientas, no acceso directo a las bases.
      </p>
    </figure>
  );
}

export default function DocsPage() {
  const [active, setActive] = useState('vision');
  useEffect(() => {
    document.title = 'Humanizar IA — Documentación técnica';
    const initialSection = window.location.hash.slice(1);
    if (sections.some((section) => section.id === initialSection)) {
      const element = document.getElementById(initialSection);
      element?.scrollIntoView({ behavior: 'instant', block: 'start' });
      element?.focus({ preventScroll: true });
      setActive(initialSection);
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) if (entry.isIntersecting) setActive(entry.target.id);
      },
      { rootMargin: '-100px 0px -65% 0px' },
    );
    for (const section of sections) {
      const element = document.getElementById(section.id);
      if (element) observer.observe(element);
    }
    return () => observer.disconnect();
  }, []);

  return (
    <div className="docs-page">
      <a href="#docs-content" className="skip-link">
        Saltar a la documentación
      </a>
      <header className="docs-header">
        <SiteLink href="/" className="docs-brand">
          <Sparkles size={25} strokeWidth={1.4} />
          <strong>
            Humanizar IA<span>.</span>
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
      <div className="docs-layout">
        <aside className="docs-index" aria-label="Índice de documentación">
          <span className="docs-index-label">EN ESTA PÁGINA</span>
          <nav>
            {sections.map((section) => (
              <a
                key={section.id}
                href={`#${section.id}`}
                className={active === section.id ? 'active' : ''}
                aria-current={active === section.id ? 'location' : undefined}
                onClick={() => setActive(section.id)}
              >
                {section.icon}
                <span>{section.label}</span>
              </a>
            ))}
          </nav>
          <div className="docs-index-note">
            <ShieldCheck size={17} />
            <strong>
              El código también debe
              <br />
              explicar sus decisiones.
            </strong>
            <p>
              Esta página describe la implementación y la evidencia disponible. No sustituye una
              auditoría de producción.
            </p>
          </div>
          <a
            className="docs-swagger-link"
            href="/api/docs"
            target="_blank"
            rel="noopener noreferrer"
          >
            <Braces size={15} /> Explorar API
            <ArrowUpRight size={12} />
          </a>
        </aside>
        <main id="docs-content" className="docs-content">
          <section
            className="docs-hero"
            id="vision"
            tabIndex={-1}
            aria-labelledby="docs-hero-title"
          >
            <div className="docs-eyebrow">
              <GitBranch size={13} /> DOCUMENTACIÓN TÉCNICA <span>01 / HUMANIZAR</span>
            </div>
            <h1 id="docs-hero-title">
              La claridad también
              <br />
              está <span>en el código.</span>
            </h1>
            <p className="docs-hero-intro">
              Una conversación sencilla por fuera. Una arquitectura con contratos, fuentes y límites
              claros por dentro. Así está construido Humanizar IA.
            </p>
            <div className="docs-hero-tags">
              <span>
                <Code2 size={12} /> React + TypeScript
              </span>
              <span>
                <Braces size={12} /> FastAPI
              </span>
              <span>
                <Sparkles size={12} /> Claude Haiku
              </span>
              <span>
                <Database size={12} /> PostgreSQL + Qdrant
              </span>
            </div>
            <div className="docs-evidence-heading">
              <span>
                <FileCheck2 size={13} /> EVIDENCIA REGISTRADA
              </span>
              <time dateTime="2026-10-07">7 de octubre de 2026</time>
            </div>
            <div className="docs-metrics">
              <div>
                <span className="docs-metric-number">
                  351<span> / pruebas</span>
                </span>
                <p>En la base de comprobación</p>
                <small>186 API · 77 sandbox/scripts · 28 despliegue · 60 web</small>
              </div>
              <div>
                <span className="docs-metric-title">
                  <Fingerprint size={18} /> Tipos, sin atajos
                </span>
                <p>TypeScript strict · mypy estricto</p>
                <small>Lint, formato, contratos y builds</small>
              </div>
              <div>
                <span className="docs-metric-title">
                  <CheckCheck size={18} /> Evidencia visible
                </span>
                <p>Fuentes y herramientas reales</p>
                <small>Referencias y trazas de ejecución</small>
              </div>
            </div>
            <p className="docs-snapshot-note">
              El inventario y la evidencia están fechados; esta página no ejecuta comprobaciones en
              vivo. El despliegue público también pasó su smoke de extremo a extremo.
            </p>
          </section>
          <Section
            id="arquitectura"
            number="02"
            label="ARQUITECTURA"
            title="Piezas pequeñas. Responsabilidades claras."
          >
            <p>
              Vercel sirve React y dirige <code>/api</code> al backend mediante un rewrite
              protegido. FastAPI y el sandbox se ejecutan en Docker en un VPS. PostgreSQL conserva
              cuentas, sesiones, conversaciones y solicitudes; Qdrant recupera evidencia desde su
              índice local persistente. SQLite sigue disponible para desarrollo local sin base
              remota.
            </p>
            <Architecture />
            <div className="docs-two-columns">
              <div className="docs-info-card">
                <Code2 size={21} />
                <h3>Una web tipada de extremo a extremo</h3>
                <p>
                  React y TypeScript con <code>strict</code>, <code>noUncheckedIndexedAccess</code>{' '}
                  y <code>exactOptionalPropertyTypes</code>. Markdown seguro, sin HTML crudo, y un
                  parser SSE que conserva UTF-8 aunque la red fragmente los eventos.
                </p>
              </div>
              <div className="docs-info-card">
                <Braces size={21} />
                <h3>Una API que tiene el control</h3>
                <p>
                  FastAPI y modelos Pydantic delimitan las entradas y salidas. El registro de
                  herramientas es compartido por el agente y la consola del administrador: ambos
                  prueban el mismo comportamiento.
                </p>
              </div>
            </div>
          </Section>
          <Section
            id="agente"
            number="03"
            label="PROCESO DEL AGENTE"
            title="De una pregunta a una respuesta verificable."
          >
            <p>
              El modo Anthropic utiliza el ciclo nativo de <code>tool_use</code> y{' '}
              <code>tool_result</code> de Claude Haiku 4.5. Cada conversación tiene límites de
              turnos, tokens, tiempo y llamadas a herramientas.
            </p>
            <ol className="docs-process">
              <li>
                <span>01</span>
                <div>
                  <h3>Recuperar el contexto</h3>
                  <p>
                    La API obtiene el historial de la cuenta desde la base de datos y busca
                    fragmentos relevantes en la documentación empresarial.
                  </p>
                </div>
              </li>
              <li>
                <span>02</span>
                <div>
                  <h3>Elegir y ejecutar herramientas</h3>
                  <p>
                    El modelo puede consultar conocimiento, calcular o proponer una solicitud. La
                    API valida los argumentos, comprueba permisos y registra el resultado real.
                  </p>
                </div>
              </li>
              <li>
                <span>03</span>
                <div>
                  <h3>Pedir confirmación cuando hay una acción</h3>
                  <p>
                    Una propuesta de demo o soporte todavía no crea un registro. El usuario revisa
                    los datos y confirma con una acción explícita.
                  </p>
                </div>
              </li>
              <li>
                <span>04</span>
                <div>
                  <h3>Responder con fuentes</h3>
                  <p>
                    Antes de emitir la respuesta, se sanean y ordenan las referencias. Los
                    fragmentos consultados se pueden desplegar; si falta evidencia, el asistente lo
                    indica.
                  </p>
                </div>
              </li>
            </ol>
            <div className="docs-callout">
              <MessageSquare size={19} />
              <div>
                <h3>Avances reales, sin razonamiento interno</h3>
                <p>
                  SSE emite eventos de estado, herramientas y respuesta. El frontend muestra
                  actividad comprobable; no expone ni inventa una cadena de pensamiento. Los errores
                  y las interrupciones se comunican como tales.
                </p>
              </div>
            </div>
          </Section>
          <Section
            id="datos"
            number="04"
            label="CONOCIMIENTO Y PERSISTENCIA"
            title="El contexto se consulta. Las cuentas se respetan."
          >
            <div className="docs-data-grid">
              <article>
                <span className="docs-data-icon">
                  <Layers3 size={21} />
                </span>
                <h3>Qdrant · recuperación vectorial</h3>
                <p>
                  FastEmbed multilingüe produce embeddings semánticos de 384 dimensiones. El índice
                  local persiste entre reinicios. El modo alternativo <code>hash</code> es léxico,
                  determinista y se identifica como tal.
                </p>
              </article>
              <article>
                <span className="docs-data-icon lavender">
                  <Database size={21} />
                </span>
                <h3>PostgreSQL · datos de la aplicación</h3>
                <p>
                  Cuentas, familias de sesiones, conversaciones, mensajes y solicitudes en un schema
                  dedicado <code>lumen</code>, con TLS y verificación del certificado y del
                  hostname. SQLite es la alternativa local. El historial se obtiene por propietario;
                  el servidor ignora el historial que envía el cliente autenticado.
                </p>
              </article>
            </div>
            <p>
              La ingesta admite TXT, Markdown, PDF con texto extraíble, DOCX, CSV, JSON y ZIP. Hay
              límites de tamaño, expansión y procesamiento; los ZIP se leen sin ejecutar su
              contenido ni extraerlo al host.
            </p>
            <div className="docs-inline-note">
              <BookOpen size={16} />
              <p>
                La pestaña <strong>Documentación</strong> de administración contiene fuentes
                empresariales para el agente.{' '}
                <strong>Esta página técnica es pública y está separada de ese conocimiento.</strong>
              </p>
            </div>
            <details className="docs-details">
              <summary>
                Decisiones de persistencia
                <ChevronRight size={15} />
              </summary>
              <p>
                Qdrant local utiliza un único worker de API y un volumen persistente en el VPS.
                PostgreSQL usa un schema exclusivo del proyecto; los secretos de conexión se
                configuran únicamente en el backend. Un cambio de embeddings requiere reconciliar la
                colección; no se mezclan espacios vectoriales incompatibles. Qdrant remoto sigue
                siendo opcional y no forma parte de la verificación registrada.
              </p>
            </details>
          </Section>
          <Section
            id="seguridad"
            number="05"
            label="ACCESO Y SEGURIDAD"
            title="La sesión tiene dueño. La acción tiene permiso."
          >
            <div className="docs-security-list">
              <article>
                <LockKeyhole size={20} />
                <div>
                  <h3>JWT en memoria, contraseñas con Argon2</h3>
                  <p>
                    El token de acceso permanece solo en memoria del navegador. Las contraseñas se
                    almacenan como hashes Argon2; no hay credenciales predeterminadas. En
                    producción, el primer administrador se provisiona por CLI privado antes de
                    publicar; el bootstrap HTTP exige un token privado del operador.
                  </p>
                </div>
              </article>
              <article>
                <Fingerprint size={20} />
                <div>
                  <h3>Refresh rotativo y revocación de familia</h3>
                  <p>
                    La configuración HTTPS utiliza una cookie Secure y HttpOnly. El refresh rota sus
                    credenciales y el logout revoca la familia completa. Refresh y logout requieren
                    un encabezado de verificación; el cliente reintenta una sola vez al recibir un
                    401. Estos atributos se comprobaron desde el navegador en el despliegue público.
                  </p>
                </div>
              </article>
              <article>
                <ShieldCheck size={20} />
                <div>
                  <h3>Roles y propiedad comprobados en el backend</h3>
                  <p>
                    Los clientes acceden a su chat y solicitudes. Administradores gestionan
                    documentación, herramientas y bandeja de clientes. La API exige permisos y
                    propiedad de cada conversación; ocultar un botón no sustituye esas
                    comprobaciones.
                  </p>
                </div>
              </article>
              <article>
                <CheckCheck size={20} />
                <div>
                  <h3>Confirmación explícita e idempotencia</h3>
                  <p>
                    Las acciones de demo y soporte requieren un clic de confirmación. Una clave por
                    usuario y propuesta evita crear dos solicitudes al repetir la misma
                    confirmación.
                  </p>
                </div>
              </article>
            </div>
            <div className="docs-callout docs-callout-lavender">
              <ShieldCheck size={20} />
              <div>
                <h3>La clave del proveedor permanece en el backend</h3>
                <p>
                  La clave de Anthropic se configura exclusivamente en el entorno del backend. No se
                  introduce en la web, no se guarda desde la API y nunca se devuelve al navegador.
                  Cada instalación necesita su propia configuración privada.
                </p>
              </div>
            </div>
          </Section>
          <Section
            id="herramientas"
            number="06"
            label="HERRAMIENTAS E INTEGRACIONES"
            title="Capacidades concretas, con límites concretos."
          >
            <div className="docs-tool-matrix">
              <div>
                <SearchIcon />
                <h3>Conocimiento y recomendación</h3>
                <p>
                  Búsqueda de documentos y recomendación de productos a partir del proceso descrito,
                  con fuentes consultables.
                </p>
              </div>
              <div>
                <Code2 size={19} />
                <h3>Cálculo y solicitudes</h3>
                <p>
                  Calculadora con AST limitado; demos y soporte persistidos tras confirmación;
                  consulta de solicitudes por cuenta.
                </p>
              </div>
              <div>
                <Terminal size={19} />
                <h3>Terminal aislada</h3>
                <p>
                  Solo presets permitidos dentro del sandbox. Sin shell arbitrario, socket Docker,
                  secretos del proveedor ni montajes escribibles del host.
                </p>
              </div>
              <div>
                <Boxes size={19} />
                <h3>MCP sobre la misma identidad</h3>
                <p>
                  Servidor read-only por stdio. La identidad empresarial se consulta por HTTP a la
                  API; no se abre otro escritor de Qdrant.
                </p>
              </div>
            </div>
            <details className="docs-details">
              <summary>
                Qué se ha comprobado de MCP y del sandbox
                <ChevronRight size={15} />
              </summary>
              <p>
                La última base verificó handshake, catálogo MCP y <code>company_info</code> sobre la
                API real. La búsqueda protegida exige sesión: un MCP sin autenticación no tiene
                acceso. En el VPS se comprobaron los contenedores saludables, la red interna y el
                preset real de Python. Streaming, sesiones y persistencia también se verificaron
                desde Vercel, con una llamada autenticada a Haiku.
              </p>
            </details>
          </Section>
          <Section
            id="calidad"
            number="07"
            label="CALIDAD Y EVIDENCIA"
            title="El estándar se demuestra con comprobaciones."
          >
            <p>
              La base cuenta con <strong>351 pruebas aprobadas</strong>, incluidas pruebas reales de
              persistencia PostgreSQL, y comprobaciones de formato, tipos y build. La evidencia
              describe la base registrada; cada cambio posterior debe volver a pasar sus
              comprobaciones.
            </p>
            <div className="docs-quality-table-wrap">
              <table className="docs-quality-table">
                <caption>Inventario y evidencia registrados el 7 de octubre de 2026</caption>
                <thead>
                  <tr>
                    <th scope="col">Capa</th>
                    <th scope="col">Comprobaciones</th>
                    <th scope="col">Pruebas</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th scope="row">API y agente</th>
                    <td>
                      Ruff, formato, mypy estricto, agente, autenticación y persistencia PostgreSQL
                    </td>
                    <td>
                      <strong>186</strong>
                    </td>
                  </tr>
                  <tr>
                    <th scope="row">Sandbox y utilidades</th>
                    <td>Ruff, formato, tipos, límites de ejecución, importación y empaquetado</td>
                    <td>
                      <strong>77</strong>
                    </td>
                  </tr>
                  <tr>
                    <th scope="row">Helpers de despliegue</th>
                    <td>Orígenes, TLS, secretos, bootstrap y configuración reproducible</td>
                    <td>
                      <strong>28</strong>
                    </td>
                  </tr>
                  <tr>
                    <th scope="row">Frontend</th>
                    <td>
                      ESLint con tipos, hooks y accesibilidad; Prettier; TypeScript; Vitest; build
                    </td>
                    <td>
                      <strong>60</strong>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="docs-quality-checks">
              <span>
                <Check size={13} /> 0 vulnerabilidades web en el audit registrado
              </span>
              <span>
                <Check size={13} /> Locks de dependencias
              </span>
              <span>
                <Check size={13} /> Revisión independiente
              </span>
              <span>
                <Check size={13} /> Smoke desktop y móvil
              </span>
            </div>
            <p>
              Las pruebas relevantes cubren UTF-8 fragmentado y errores SSE; refresh y logout;
              confirmaciones permitidas; aislamiento de cuentas, ingesta, citas y presupuestos del
              agente. PostgreSQL tiene pruebas en una base temporal y una conexión productiva con
              TLS verificado. Las rutas de Vercel se compilan sin serializar secretos. El smoke del
              despliegue público comprobó acceso, sesión renovable, historial, fuentes, Swagger y
              documentación, sin errores JavaScript ni overflow móvil. Un reinicio de la API
              conservó el historial y las sesiones.
            </p>
          </Section>
          <Section
            id="estado"
            number="08"
            label="ESTADO Y LÍMITES"
            title="Lo comprobado y lo pendiente, a la vista."
          >
            <div className="docs-status-grid">
              <div className="docs-status-verified">
                <span>
                  <CheckCheck size={17} /> Comprobado en pruebas
                </span>
                <ul>
                  <li>Acceso por cuenta, roles y sesiones revocables.</li>
                  <li>Persistencia PostgreSQL con TLS y recuperación semántica local.</li>
                  <li>Chat con fuentes, solicitudes confirmadas e inbox admin.</li>
                  <li>Identidad MCP y verificaciones de código.</li>
                  <li>Vercel y backend Docker desplegados; cookies HTTPS y sandbox comprobados.</li>
                  <li>
                    Claude Haiku 4.5: llamada autenticada, ejecución real del agente con MCP y
                    recuperación de documentación con fuentes verificadas desde la web pública.
                  </li>
                </ul>
              </div>
              <div className="docs-status-pending">
                <span>
                  <CircleDot size={17} /> Requiere comprobación adicional
                </span>
                <ul>
                  <li>
                    Cada instalación requiere su propia clave de Anthropic en el backend y verificar
                    la conexión.
                  </li>
                  <li>
                    Fedora: instalación real pendiente de disponer del usuario y host SSH del
                    portátil. El helper y el procedimiento están documentados.
                  </li>
                  <li>Qdrant remoto: opcional, fuera de la verificación registrada.</li>
                  <li>PDF escaneado: no incluye OCR.</li>
                </ul>
              </div>
            </div>
            <div className="docs-limit-note">
              <ShieldCheck size={17} />
              <p>
                El modo demo usa respuestas extractivas y lo indica. Los errores de Anthropic no se
                disimulan con un fallback silencioso. Las solicitudes se registran en la plataforma:{' '}
                <strong>
                  no se envían correos, WhatsApp ni reservas de agenda automáticamente.
                </strong>
              </p>
            </div>
          </Section>
          <Section
            id="empezar"
            number="09"
            label="EXPLORAR EL CÓDIGO"
            title="De la arquitectura a la implementación."
          >
            <p>
              El README del repositorio reúne requisitos, variables sin valores sensibles, arranque
              y comprobaciones. La referencia OpenAPI describe los contratos de la API.
            </p>
            <div className="docs-resource-grid">
              <a href="/api/docs" target="_blank" rel="noopener noreferrer">
                <span className="docs-resource-icon">
                  <Braces size={23} />
                </span>
                <div>
                  <h3>Referencia de API</h3>
                  <p>Swagger · Contratos, rutas y esquemas</p>
                </div>
                <ArrowUpRight size={17} />
              </a>
              <a
                href={REPOSITORY_URL}
                target="_blank"
                rel="noopener noreferrer"
                aria-describedby="docs-repository-state"
              >
                <span className="docs-resource-icon lavender">
                  <GitBranch size={22} />
                </span>
                <div>
                  <h3>Código en GitHub</h3>
                  <p>Repositorio público · Consulta la implementación</p>
                </div>
                <ArrowUpRight size={17} />
              </a>
              <a
                href={`${REPOSITORY_URL}#readme`}
                target="_blank"
                rel="noopener noreferrer"
                aria-describedby="docs-repository-state"
              >
                <span className="docs-resource-icon">
                  <BookOpen size={22} />
                </span>
                <div>
                  <h3>README y arranque</h3>
                  <p>Preparación y comandos reproducibles</p>
                </div>
                <ArrowUpRight size={17} />
              </a>
              <a
                href={`${REPOSITORY_URL}/blob/dev/docs/DEPLOYMENT.md`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <span className="docs-resource-icon lavender">
                  <Network size={22} />
                </span>
                <div>
                  <h3>Vercel, VPS y PostgreSQL</h3>
                  <p>Despliegue, persistencia y comprobación</p>
                </div>
                <ArrowUpRight size={17} />
              </a>
              <a
                href={`${REPOSITORY_URL}/blob/dev/docs/FEDORA.md`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <span className="docs-resource-icon">
                  <Terminal size={22} />
                </span>
                <div>
                  <h3>Preparar Fedora</h3>
                  <p>Entorno de desarrollo y dependencias</p>
                </div>
                <ArrowUpRight size={17} />
              </a>
            </div>
            <p className="docs-repository-state" id="docs-repository-state">
              Consulta el repositorio público <code>stevenvo780/humanizar-ai-agent</code> y su
              README para explorar el proyecto y las instrucciones de arranque.
            </p>
            <div className="docs-start-code">
              <div>
                <Terminal size={14} />
                <span>Flujo de trabajo documentado</span>
                <span>Desde el repositorio</span>
              </div>
              <pre>
                <code>
                  make setup{'\n'}make check{'\n'}make dev
                </code>
              </pre>
              <p>
                El README explica la configuración y cuándo se requiere Docker o una conexión del
                proveedor. No incluye claves ni credenciales predeterminadas.
              </p>
            </div>
          </Section>
          <footer className="docs-footer">
            <div>
              <Sparkles size={20} />
              <span>
                Humanizar IA<strong>Información clara. Código que explica sus decisiones.</strong>
              </span>
            </div>
            <SiteLink href="/">
              Volver al asistente
              <ArrowRight size={15} />
            </SiteLink>
          </footer>
        </main>
      </div>
    </div>
  );
}

function SearchIcon() {
  return <Layers3 size={19} />;
}

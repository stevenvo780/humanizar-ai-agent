import {
  ArrowRight,
  BookOpenText,
  Boxes,
  CheckCheck,
  Database,
  FileUp,
  KeyRound,
  Radio,
  Search,
  Terminal,
  UserCog,
  Wrench,
  Accessibility,
} from 'lucide-react';
import type { ReactNode } from 'react';
import { DocsSection } from '../DocsSection';
import { sectionLabel, type SectionId } from '../docsContent';

interface Capability {
  icon: ReactNode;
  title: string;
  text: string;
  section: SectionId;
}

const CAPABILITIES: readonly Capability[] = [
  {
    icon: <Search size={18} />,
    title: 'Respuestas con fuentes',
    text: 'RAG sobre la documentación de la empresa; cita sus fuentes y reconoce cuando no sabe.',
    section: 'agente',
  },
  {
    icon: <Search size={18} />,
    title: 'Endpoint RAG /api/ask',
    text: 'Pregunta → base vectorial → Claude: respuesta citada en una sola llamada HTTP.',
    section: 'agente',
  },
  {
    icon: <Wrench size={18} />,
    title: 'Herramientas reales',
    text: 'Ciclo nativo tool_use con límites de turnos, tokens, tiempo y llamadas.',
    section: 'agente',
  },
  {
    icon: <CheckCheck size={18} />,
    title: 'Confirmación al escribir',
    text: 'Demos y soporte se proponen y solo se registran tras un clic explícito, sin duplicados.',
    section: 'seguridad',
  },
  {
    icon: <Radio size={18} />,
    title: 'Streaming SSE',
    text: 'Estado, herramientas y respuesta en tiempo real, sin inventar razonamiento.',
    section: 'agente',
  },
  {
    icon: <FileUp size={18} />,
    title: 'Carga de documentos',
    text: 'TXT, MD, PDF, DOCX, CSV, JSON y ZIP, con límites de tamaño y expansión.',
    section: 'datos',
  },
  {
    icon: <BookOpenText size={18} />,
    title: 'Lector de documentos',
    text: 'Las fuentes del agente se leen en Markdown seguro o como texto completo.',
    section: 'datos',
  },
  {
    icon: <Database size={18} />,
    title: 'Persistencia',
    text: 'PostgreSQL con TLS verificado o SQLite local; Qdrant persistente para la recuperación.',
    section: 'datos',
  },
  {
    icon: <KeyRound size={18} />,
    title: 'Cuentas y roles',
    text: 'JWT en memoria, Argon2, refresh rotativo y propiedad comprobada en el backend.',
    section: 'seguridad',
  },
  {
    icon: <UserCog size={18} />,
    title: 'Administración de clientes',
    text: 'El admin crea cuentas de clientes y atiende su bandeja de solicitudes.',
    section: 'seguridad',
  },
  {
    icon: <Boxes size={18} />,
    title: 'Servidor MCP',
    text: 'Read-only por stdio, sobre la misma API e identidad que la web.',
    section: 'herramientas',
  },
  {
    icon: <Terminal size={18} />,
    title: 'Sandbox con presets',
    text: 'Terminal aislada en Docker: solo comandos permitidos, sin shell arbitraria.',
    section: 'herramientas',
  },
  {
    icon: <Accessibility size={18} />,
    title: 'Accesible y adaptable',
    text: 'Teclado, lectores de pantalla y diseños de 320 a 1440 px, comprobados.',
    section: 'calidad',
  },
];

export function CapabilitiesSection() {
  return (
    <DocsSection id="capacidades" label="QUÉ TIENE" title="Lo que ya funciona, de un vistazo.">
      <p>
        Cada capacidad está implementada y probada; cada tarjeta enlaza con su explicación
        detallada.
      </p>
      <ul className="docs-capability-grid">
        {CAPABILITIES.map((capability) => (
          <li key={capability.title}>
            <span className="docs-capability-icon">{capability.icon}</span>
            <h3>{capability.title}</h3>
            <p>{capability.text}</p>
            <a href={`#${capability.section}`}>
              {sectionLabel(capability.section)}
              <ArrowRight size={13} />
            </a>
          </li>
        ))}
      </ul>
    </DocsSection>
  );
}

import { CheckCheck, CircleDot, ShieldCheck } from 'lucide-react';
import { DocsSection } from '../DocsSection';
import { ExternalLink } from '../ExternalLink';
import { repositoryFile } from '../docsLinks';

export function StatusSection() {
  return (
    <DocsSection
      id="estado"
      label="ESTADO Y LÍMITES"
      title="Lo comprobado y lo pendiente, a la vista."
    >
      <div className="docs-status-grid">
        <div className="docs-status-verified">
          <span>
            <CheckCheck size={17} /> Comprobado
          </span>
          <ul>
            <li>Acceso por cuenta, roles y sesiones revocables.</li>
            <li>Persistencia PostgreSQL con TLS y recuperación semántica local.</li>
            <li>Chat con fuentes, solicitudes confirmadas e inbox admin.</li>
            <li>Identidad MCP y verificaciones de código.</li>
            <li>
              Producción desplegada: frontend en Vercel y API en Docker, con lectura de documentos y
              gestión de clientes declaradas por HTTPS.
            </li>
            <li>
              Backup coordinado antes de publicar y restauración ensayada en un entorno aislado.
            </li>
            <li>
              Claude Haiku 4.5: llamada autenticada, ejecución real del agente con MCP y
              recuperación de documentación con fuentes verificadas desde la web pública.
            </li>
            <li>Spec Kit 001 completo, de specify a converge, con todas sus tareas cerradas.</li>
            <li>
              Prueba técnica de Softop: <code>softop-rag</code> con sus pruebas automatizadas y la
              verificación con Claude Haiku registrada en su README.
            </li>
            <li>
              Equipo Fedora 44 de presentación con <code>make setup</code> y <code>make check</code>{' '}
              aprobados.
            </li>
          </ul>
        </div>
        <div className="docs-status-pending">
          <span>
            <CircleDot size={17} /> Requiere comprobación adicional
          </span>
          <ul>
            <li>
              Cada instalación requiere su propia clave de Anthropic en el backend y verificar la
              conexión.
            </li>
            <li>
              <code>POST /preguntar</code> integrado en la plataforma: verificar por HTTPS en cada
              publicación, con la clave de Anthropic configurada en el backend.
            </li>
            <li>
              Recorrido manual del lector y de Clientes con la sesión admin de producción; la API ya
              declara ambas capacidades.
            </li>
            <li>
              GitHub Actions está definido; la evidencia registrada procede de ejecuciones locales.
            </li>
            <li>Qdrant remoto: opcional, fuera de la verificación registrada.</li>
            <li>PDF escaneado: no incluye OCR.</li>
          </ul>
        </div>
      </div>
      <p>
        El{' '}
        <ExternalLink href={repositoryFile('docs/OPERATIONS.md')}>
          runbook de operaciones
        </ExternalLink>{' '}
        describe variables por entorno, publicación, verificaciones, copias de seguridad y
        recuperación.
      </p>
      <div className="docs-limit-note">
        <ShieldCheck size={17} />
        <p>
          El modo demo usa respuestas extractivas y lo indica. Los errores de Anthropic no se
          disimulan con un fallback silencioso. Las solicitudes se registran en la plataforma:{' '}
          <strong>no se envían correos, WhatsApp ni reservas de agenda automáticamente.</strong>
        </p>
      </div>
    </DocsSection>
  );
}

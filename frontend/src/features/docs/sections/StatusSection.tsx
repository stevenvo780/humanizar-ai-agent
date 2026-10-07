import { CheckCheck, CircleDot, ShieldCheck } from 'lucide-react';
import { DocsSection } from '../DocsSection';
import { REPOSITORY_URL } from '../docsContent';

export function StatusSection() {
  return (
    <DocsSection
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
              Cada instalación requiere su propia clave de Anthropic en el backend y verificar la
              conexión.
            </li>
            <li>
              Backend auditado, lectura de documentos y gestión de clientes: publicación de la API
              actualizada pendiente de recuperar el acceso SSH al VPS. La interfaz comprueba las
              capacidades del servidor antes de habilitarlas.
            </li>
            <li>
              Fedora: instalación real pendiente de disponer del usuario y host SSH del portátil. La
              carpeta prevista es <code>~/Documentos/repos/SoftopPrueba</code>; el helper y el
              procedimiento están documentados.
            </li>
            <li>Qdrant remoto: opcional, fuera de la verificación registrada.</li>
            <li>PDF escaneado: no incluye OCR.</li>
          </ul>
        </div>
      </div>
      <p>
        El{' '}
        <a
          href={`${REPOSITORY_URL}/blob/dev/docs/OPERATIONS.md`}
          target="_blank"
          rel="noopener noreferrer"
        >
          runbook de operaciones
        </a>{' '}
        describe variables por entorno, publicación, verificaciones, copias de seguridad y
        recuperación. La copia del portátil conserva el nombre de carpeta de este proyecto.
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

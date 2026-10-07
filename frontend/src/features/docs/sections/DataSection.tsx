import { BookOpen, ChevronRight, Database, Layers3 } from 'lucide-react';
import { DocsSection } from '../DocsSection';

export function DataSection() {
  return (
    <DocsSection
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
            FastEmbed multilingüe produce embeddings semánticos de 384 dimensiones. El índice local
            persiste entre reinicios. El modo alternativo <code>hash</code> es léxico, determinista
            y se identifica como tal.
          </p>
        </article>
        <article>
          <span className="docs-data-icon lavender">
            <Database size={21} />
          </span>
          <h3>PostgreSQL · datos de la aplicación</h3>
          <p>
            Cuentas, familias de sesiones, conversaciones, mensajes y solicitudes en un schema
            dedicado <code>lumen</code>, con TLS y verificación del certificado y del hostname.
            SQLite es la alternativa local. El historial se obtiene por propietario; el servidor
            ignora el historial que envía el cliente autenticado.
          </p>
        </article>
      </div>
      <p>
        La ingesta admite TXT, Markdown, PDF con texto extraíble, DOCX, CSV, JSON y ZIP. Hay límites
        de tamaño, expansión y procesamiento; los ZIP se leen sin ejecutar su contenido ni extraerlo
        al host.
      </p>
      <div className="docs-inline-note">
        <BookOpen size={16} />
        <p>
          La sección <strong>Documentación</strong> de administración permite cargar y leer las
          fuentes empresariales del agente en Markdown o como texto. Las nuevas cargas conservan el
          texto completo; las anteriores se reconstruyen desde sus fragmentos con un aviso sobre el
          formato.{' '}
          <strong>Esta página técnica es pública y está separada de ese conocimiento.</strong>
        </p>
      </div>
      <details className="docs-details">
        <summary>
          Decisiones de persistencia
          <ChevronRight size={15} />
        </summary>
        <p>
          Qdrant local utiliza un único worker de API y un volumen persistente en el VPS. PostgreSQL
          usa un schema exclusivo del proyecto; los secretos de conexión se configuran únicamente en
          el backend. Un cambio de embeddings requiere reconciliar la colección; no se mezclan
          espacios vectoriales incompatibles. Qdrant remoto sigue siendo opcional y no forma parte
          de la verificación registrada.
        </p>
      </details>
    </DocsSection>
  );
}

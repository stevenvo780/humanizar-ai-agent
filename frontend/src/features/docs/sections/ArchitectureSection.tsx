import { Braces, Code2 } from 'lucide-react';
import { ArchitectureDiagram } from '../ArchitectureDiagram';
import { DocsSection } from '../DocsSection';

export function ArchitectureSection({ assistant }: { assistant: string }) {
  return (
    <DocsSection
      id="arquitectura"
      label="ARQUITECTURA"
      title="Piezas pequeñas. Responsabilidades claras."
    >
      <p>
        Vercel sirve React y dirige <code>/api</code> al backend mediante un rewrite protegido.
        FastAPI y el sandbox se ejecutan en Docker en un VPS. PostgreSQL conserva cuentas, sesiones,
        conversaciones y solicitudes; Qdrant recupera evidencia desde su índice local persistente.
        SQLite sigue disponible para desarrollo local sin base remota.
      </p>
      <ArchitectureDiagram assistant={assistant} />
      <div className="docs-two-columns">
        <div className="docs-info-card">
          <Code2 size={21} />
          <h3>Una web tipada de extremo a extremo</h3>
          {/* prettier-ignore */}
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
            FastAPI y modelos Pydantic delimitan las entradas y salidas. El registro de herramientas
            es compartido por el agente y la consola del administrador: ambos prueban el mismo
            comportamiento.
          </p>
        </div>
      </div>
    </DocsSection>
  );
}

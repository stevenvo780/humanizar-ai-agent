import { Boxes, ChevronRight, Code2, Layers3, Terminal } from 'lucide-react';
import { DocsSection } from '../DocsSection';

export function ToolsSection() {
  return (
    <DocsSection
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
            Búsqueda de documentos y recomendación de productos a partir del proceso descrito, con
            fuentes consultables.
          </p>
        </div>
        <div>
          <Code2 size={19} />
          <h3>Cálculo y solicitudes</h3>
          <p>
            Calculadora con AST limitado; demos y soporte persistidos tras confirmación; consulta de
            solicitudes por cuenta.
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
            Servidor read-only por stdio. La identidad empresarial se consulta por HTTP a la API; no
            se abre otro escritor de Qdrant.
          </p>
        </div>
      </div>
      <details className="docs-details">
        <summary>
          Qué se ha comprobado de MCP y del sandbox
          <ChevronRight size={15} />
        </summary>
        <p>
          La última base verificó handshake, catálogo MCP y <code>company_info</code> sobre la API
          real. La búsqueda protegida exige sesión: un MCP sin autenticación no tiene acceso. El CLI
          privado prepara una sesión ligada al origen, con renovación acotada; sus credenciales
          permanecen fuera del código y del navegador. En el VPS se comprobaron los contenedores
          saludables, la red interna y el preset real de Python. Streaming, sesiones y persistencia
          también se verificaron desde Vercel, con una llamada autenticada a Haiku.
        </p>
      </details>
    </DocsSection>
  );
}

function SearchIcon() {
  return <Layers3 size={19} />;
}

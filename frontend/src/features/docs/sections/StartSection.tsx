import { ArrowUpRight, BookOpen, Braces, GitBranch, Network, Terminal } from 'lucide-react';
import { DocsSection } from '../DocsSection';
import { REPOSITORY_SLUG, REPOSITORY_URL } from '../docsContent';

export function StartSection() {
  return (
    <DocsSection
      id="empezar"
      number="09"
      label="EXPLORAR EL CÓDIGO"
      title="De la arquitectura a la implementación."
    >
      <p>
        El README del repositorio reúne requisitos, variables sin valores sensibles, arranque y
        comprobaciones. La referencia OpenAPI describe los contratos de la API.
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
        Consulta el repositorio público <code>{REPOSITORY_SLUG}</code> y su README para explorar el
        proyecto y las instrucciones de arranque.
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
    </DocsSection>
  );
}

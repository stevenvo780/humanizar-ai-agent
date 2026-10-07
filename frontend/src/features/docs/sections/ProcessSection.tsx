import { Sparkles, Terminal } from 'lucide-react';
import { DocsSection } from '../DocsSection';
import { ExternalLink } from '../ExternalLink';
import { repositoryFile } from '../docsLinks';

const SPEC_KIT_FLOW = [
  'constitution',
  'specify',
  'clarify',
  'plan',
  'tasks',
  'analyze',
  'implement',
  'converge',
] as const;

const QUALITY_COMMANDS = [
  'make check',
  'python3 scripts/audit-public.py',
  'gitleaks git --redact=100 --no-banner --log-opts=--all .',
].join('\n');

export function ProcessSection() {
  return (
    <DocsSection id="proceso" label="CÓMO SE HIZO" title="Especificado, construido y verificado.">
      <ol className="docs-process">
        <li>
          <span>01</span>
          <div>
            <h3>Especificar antes de programar</h3>
            <p>
              La base se definió con Spec Kit en Claude Code: una constitución con los principios
              del proyecto y la feature 001 recorrida de principio a fin.
            </p>
            <ol className="docs-flow" aria-label="Flujo de Spec Kit">
              {SPEC_KIT_FLOW.map((step) => (
                <li key={step}>
                  <code>{step}</code>
                </li>
              ))}
            </ol>
            <p>
              001 es la base implementada y cerrada. 002 adapta esa base al enunciado de Softop:{' '}
              <code>POST /preguntar</code> con RAG sobre las preguntas frecuentes de su software
              para ópticas, entregado en <code>softop-rag</code> e integrado en esta plataforma.{' '}
              <ExternalLink href={repositoryFile('docs/SPECKIT.md')}>Ver SPECKIT.md</ExternalLink>
            </p>
          </div>
        </li>
        <li>
          <span>02</span>
          <div>
            <h3>Desarrollar con dos trabajadores aislados</h3>
            <p>
              Claude Code con Opus 5.5 fue la herramienta de desarrollo: coordinó, implementó y
              verificó cada cambio. Codex (gpt-6.1-sol) actuó como segundo trabajador en su propio
              git worktree; su trabajo llegó al checkout principal como un parche revisado.
            </p>
          </div>
        </li>
        <li>
          <span>03</span>
          <div>
            <h3>Revisar como un adversario</h3>
            <p>
              Revisiones independientes y verificación adversarial: inyección de instrucciones,
              fallos del proveedor, ZIP cifrados o maliciosos, aislamiento entre cuentas y
              navegación real en Chromium de 320 a 1440 px. Cada hallazgo tiene su corrección y su
              regresión en{' '}
              <ExternalLink href={repositoryFile('docs/QUALITY.md')}>QUALITY.md</ExternalLink>.
            </p>
          </div>
        </li>
        <li>
          <span>04</span>
          <div>
            <h3>Pasar las puertas de calidad</h3>
            <p>
              Ruff, mypy estricto y pytest, incluido PostgreSQL en una base temporal; ESLint con
              tipos y accesibilidad, TypeScript strict, Vitest y build; Gitleaks y auditoría de
              rutas públicas antes de publicar. Los resultados de cada ejecución están en{' '}
              <ExternalLink href={repositoryFile('docs/VALIDATION.md')}>VALIDATION.md</ExternalLink>
              .
            </p>
          </div>
        </li>
        <li>
          <span>05</span>
          <div>
            <h3>Desplegar y ensayar la recuperación</h3>
            <p>
              Vercel sirve el frontend y reenvía <code>/api</code> y <code>/preguntar</code> por el
              mismo origen. FastAPI y el sandbox se ejecutan en Docker en un VPS; PostgreSQL usa TLS
              verificado. Cada publicación parte de un backup coordinado y la restauración se ensayó
              en un entorno aislado.{' '}
              <ExternalLink href={repositoryFile('docs/DEPLOYMENT.md')}>
                Ver DEPLOYMENT.md
              </ExternalLink>
            </p>
          </div>
        </li>
      </ol>
      <div className="docs-start-code">
        <div>
          <Terminal size={14} />
          <span>Puertas de calidad</span>
          <span>Desde el repositorio</span>
        </div>
        <pre>
          <code>{QUALITY_COMMANDS}</code>
        </pre>
        <p>
          <code>make check</code> ejecuta backend, sandbox, helpers de despliegue y web. La
          auditoría de rutas y Gitleaks protegen cada publicación.
        </p>
      </div>
      <div className="docs-callout docs-callout-lavender">
        <Sparkles size={20} />
        <div>
          <h3>Dos modelos, dos papeles</h3>
          <p>
            El agente de esta web responde con Claude Sonnet 5.5 a través del backend; la clave del
            proveedor nunca llega al navegador. Claude Code (Opus 5.5) y Codex son herramientas de
            desarrollo: no intervienen en las conversaciones de los visitantes.
          </p>
        </div>
      </div>
    </DocsSection>
  );
}

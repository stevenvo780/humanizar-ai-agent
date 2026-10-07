import { ArrowUpRight, Braces, ShieldCheck } from 'lucide-react';
import { sections } from './docsContent';

export function DocsIndex({
  active,
  onSelect,
}: {
  active: string;
  onSelect: (section: string) => void;
}) {
  return (
    <aside className="docs-index" aria-label="Índice de documentación">
      <span className="docs-index-label">EN ESTA PÁGINA</span>
      <nav>
        {sections.map((section) => (
          <a
            key={section.id}
            href={`#${section.id}`}
            className={active === section.id ? 'active' : ''}
            aria-current={active === section.id ? 'location' : undefined}
            onClick={() => onSelect(section.id)}
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
      <a className="docs-swagger-link" href="/api/docs" target="_blank" rel="noopener noreferrer">
        <Braces size={15} /> Explorar API
        <ArrowUpRight size={12} />
      </a>
    </aside>
  );
}

import { ArrowUpRight, BookOpen, GitBranch, Globe2, ListChecks } from 'lucide-react';
import type { ReactNode } from 'react';
import { DocsSection } from '../DocsSection';
import { ExternalLink } from '../ExternalLink';
import { resourceGroups, type ResourceIcon } from '../docsLinks';

const GROUP_ICONS: Record<ResourceIcon, ReactNode> = {
  live: <Globe2 size={19} />,
  code: <GitBranch size={19} />,
  docs: <BookOpen size={19} />,
  spec: <ListChecks size={19} />,
};

export function ResourcesSection() {
  return (
    <DocsSection id="recursos" label="RECURSOS" title="Todo el proyecto, a un clic.">
      <p>
        La aplicación publicada, el código, la documentación y los artefactos de especificación. Los
        enlaces externos se abren en una pestaña nueva; los documentos apuntan a la rama{' '}
        <code>dev</code> del repositorio público.
      </p>
      <div className="docs-link-groups">
        {resourceGroups.map((group) => (
          <article
            key={group.id}
            className={`docs-link-group${group.links.length > 3 ? ' wide' : ''}`}
            aria-labelledby={`recursos-${group.id}`}
          >
            <header>
              <span className="docs-link-group-icon">{GROUP_ICONS[group.icon]}</span>
              <div>
                <h3 id={`recursos-${group.id}`}>{group.title}</h3>
                <p>{group.description}</p>
              </div>
            </header>
            <ul>
              {group.links.map((link) => (
                <li key={link.href}>
                  <ExternalLink href={link.href}>
                    <span>
                      <strong>{link.label}</strong>
                      <small>{link.detail}</small>
                    </span>
                    <ArrowUpRight size={15} />
                  </ExternalLink>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </DocsSection>
  );
}

import type { ReactNode } from 'react';
import { sectionNumber, type SectionId } from './docsContent';

export function DocsSection({
  id,
  label,
  title,
  children,
}: {
  id: SectionId;
  label: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="docs-section" id={id} tabIndex={-1} aria-labelledby={`${id}-title`}>
      <div className="docs-section-kicker">
        <span>{sectionNumber(id)}</span>
        {label}
      </div>
      <h2 id={`${id}-title`}>{title}</h2>
      {children}
    </section>
  );
}

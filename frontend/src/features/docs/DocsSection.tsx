import type { ReactNode } from 'react';

export function DocsSection({
  id,
  number,
  label,
  title,
  children,
}: {
  id: string;
  number: string;
  label: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="docs-section" id={id} tabIndex={-1} aria-labelledby={`${id}-title`}>
      <div className="docs-section-kicker">
        <span>{number}</span>
        {label}
      </div>
      <h2 id={`${id}-title`}>{title}</h2>
      {children}
    </section>
  );
}

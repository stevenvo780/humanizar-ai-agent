import type { AnchorHTMLAttributes, ReactNode } from 'react';
import { EXTERNAL_LINK } from './docsLinks';

type ExternalLinkProps = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'target' | 'rel'> & {
  href: string;
  children: ReactNode;
};

/** A link that opens in a new tab, isolated from this page and announced as such. */
export function ExternalLink({ children, ...props }: ExternalLinkProps) {
  return (
    <a {...props} {...EXTERNAL_LINK}>
      {children}
      <span className="sr-only"> (se abre en una pestaña nueva)</span>
    </a>
  );
}

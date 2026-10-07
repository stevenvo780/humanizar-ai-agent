import type { AnchorHTMLAttributes, MouseEvent } from 'react';

export function isDocumentationPath(path: string): boolean {
  return path === '/docs' || path === '/docs/';
}

export function SiteLink({
  href,
  onClick,
  children,
  ...props
}: AnchorHTMLAttributes<HTMLAnchorElement> & { href: '/' | '/docs' }) {
  function navigate(event: MouseEvent<HTMLAnchorElement>): void {
    onClick?.(event);
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.altKey ||
      event.shiftKey ||
      props.target === '_blank'
    )
      return;
    event.preventDefault();
    window.history.pushState(null, '', href);
    window.dispatchEvent(new PopStateEvent('popstate'));
    window.scrollTo({ top: 0, behavior: 'instant' });
  }
  return (
    <a {...props} href={href} onClick={navigate}>
      {children}
    </a>
  );
}

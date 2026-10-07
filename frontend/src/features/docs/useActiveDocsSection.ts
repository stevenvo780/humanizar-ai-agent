import { useEffect, useState } from 'react';
import { sections } from './docsContent';

/** Tracks the visible documentation section and honours an initial `#section` hash. */
export function useActiveDocsSection(): [string, (section: string) => void] {
  const [active, setActive] = useState('vision');
  useEffect(() => {
    const initialSection = window.location.hash.slice(1);
    if (sections.some((section) => section.id === initialSection)) {
      const element = document.getElementById(initialSection);
      element?.scrollIntoView({ behavior: 'instant', block: 'start' });
      element?.focus({ preventScroll: true });
      setActive(initialSection);
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) if (entry.isIntersecting) setActive(entry.target.id);
      },
      { rootMargin: '-100px 0px -65% 0px' },
    );
    for (const section of sections) {
      const element = document.getElementById(section.id);
      if (element) observer.observe(element);
    }
    return () => observer.disconnect();
  }, []);
  return [active, setActive];
}

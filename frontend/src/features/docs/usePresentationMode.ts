import { useCallback, useEffect, useRef, useState, type RefObject } from 'react';
import { prefersReducedMotion, presentationAction, stepIndex } from './presentation';

export interface PresentationMode {
  /** Current slide, or null when the page is read normally. */
  index: number | null;
  start: () => void;
  stop: () => void;
  /** Steps from the bar buttons: focus stays on the pressed button. */
  step: (direction: 'next' | 'previous') => void;
  triggerRef: RefObject<HTMLButtonElement | null>;
}

function showSection(id: string, moveFocus: boolean): void {
  const element = document.getElementById(id);
  if (!element) return;
  element.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' });
  if (moveFocus) element.focus({ preventScroll: true });
  window.history.replaceState(null, '', `#${id}`);
}

/**
 * Presents the documentation one section at a time. Keys are only handled while presenting:
 * ←/→ and PageUp/PageDown move, Home/End jump and Escape returns focus to the trigger.
 */
export function usePresentationMode(
  ids: readonly string[],
  active: string,
  onNavigate: (id: string) => void,
): PresentationMode {
  const [index, setIndex] = useState<number | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const go = useCallback(
    (target: number, moveFocus: boolean) => {
      const id = ids[target];
      if (id === undefined) return;
      setIndex(target);
      showSection(id, moveFocus);
      onNavigate(id);
    },
    [ids, onNavigate],
  );
  const start = useCallback(() => {
    go(Math.max(ids.indexOf(active), 0), true);
  }, [active, go, ids]);
  const stop = useCallback(() => {
    setIndex(null);
    triggerRef.current?.focus();
  }, []);
  const step = useCallback(
    (direction: 'next' | 'previous') => {
      if (index !== null) go(stepIndex(direction, index, ids.length), false);
    },
    [go, ids.length, index],
  );

  useEffect(() => {
    if (index === null) return;
    const current = index;
    function onKeyDown(event: KeyboardEvent): void {
      const action = presentationAction(event);
      if (action === null) return;
      event.preventDefault();
      if (action === 'exit') stop();
      else go(stepIndex(action, current, ids.length), true);
    }
    // In-page links (index, capability cards) keep the counter on the section they open.
    function onHashChange(): void {
      const target = ids.indexOf(window.location.hash.slice(1));
      if (target >= 0) setIndex(target);
    }
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('hashchange', onHashChange);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('hashchange', onHashChange);
    };
  }, [go, ids, index, stop]);

  return { index, start, stop, step, triggerRef };
}

import { useEffect } from 'react';
import type { RefObject } from 'react';

const FOCUSABLE =
  'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])';

export function useDialogFocus(
  container: RefObject<HTMLElement | null>,
  open: boolean,
  onClose: () => void,
  restoreTarget?: RefObject<HTMLElement | null>,
): void {
  useEffect(() => {
    if (!open) return;
    const previous = restoreTarget?.current ?? document.activeElement;
    const candidates = () =>
      Array.from(container.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []).filter(
        (element) => element.getClientRects().length > 0 && !element.closest('[inert]'),
      );
    candidates()[0]?.focus({ preventScroll: true });
    function keydown(event: KeyboardEvent): void {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== 'Tab') return;
      const elements = candidates();
      const first = elements[0];
      const last = elements.at(-1);
      if (!first || !last) {
        event.preventDefault();
        return;
      }
      if (!container.current?.contains(document.activeElement)) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus({ preventScroll: true });
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus({ preventScroll: true });
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus({ preventScroll: true });
      }
    }
    document.addEventListener('keydown', keydown);
    return () => {
      document.removeEventListener('keydown', keydown);
      if (previous instanceof HTMLElement && previous.isConnected && !previous.closest('[inert]'))
        previous.focus({ preventScroll: true });
    };
  }, [container, open, onClose, restoreTarget]);
}

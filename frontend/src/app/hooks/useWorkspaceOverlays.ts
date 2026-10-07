import { useCallback, useRef, useState, useSyncExternalStore } from 'react';
import { useDialogFocus } from '../../shared/hooks/useDialogFocus';

const MOBILE_NAVIGATION = '(max-width: 760px)';

function subscribeMobileNavigation(listener: () => void): () => void {
  const query = window.matchMedia(MOBILE_NAVIGATION);
  query.addEventListener('change', listener);
  return () => query.removeEventListener('change', listener);
}

function mobileNavigationSnapshot(): boolean {
  return window.matchMedia(MOBILE_NAVIGATION).matches;
}

/** Mobile navigation drawer and help dialog: open state, focus trapping and restore targets. */
export function useWorkspaceOverlays() {
  const [mobileMenu, setMobileMenu] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const helpRef = useRef<HTMLElement>(null);
  const navigationRef = useRef<HTMLElement>(null);
  const navigationToggleRef = useRef<HTMLButtonElement>(null);
  const closeNavigation = useCallback(() => setMobileMenu(false), []);
  const closeHelp = useCallback(() => setShowHelp(false), []);
  const subscribeNavigation = useCallback(
    (listener: () => void) =>
      subscribeMobileNavigation(() => {
        closeNavigation();
        listener();
      }),
    [closeNavigation],
  );
  const isMobile = useSyncExternalStore(subscribeNavigation, mobileNavigationSnapshot);
  const drawerOpen = isMobile && mobileMenu;
  useDialogFocus(navigationRef, drawerOpen, closeNavigation, navigationToggleRef);
  useDialogFocus(helpRef, showHelp, closeHelp, isMobile ? navigationToggleRef : undefined);

  function openNavigation(): void {
    setMobileMenu(true);
  }
  function openHelp(): void {
    closeNavigation();
    setShowHelp(true);
  }

  return {
    isMobile,
    drawerOpen,
    showHelp,
    helpRef,
    navigationRef,
    navigationToggleRef,
    openNavigation,
    closeNavigation,
    openHelp,
    closeHelp,
  };
}

/** Pure keyboard logic for the documentation presentation mode. */
export type PresentationAction = 'next' | 'previous' | 'first' | 'last' | 'exit';

export interface PresentationKey {
  key: string;
  altKey: boolean;
  ctrlKey: boolean;
  metaKey: boolean;
  defaultPrevented: boolean;
  isComposing?: boolean;
  target: EventTarget | null;
}

const KEY_ACTIONS: Readonly<Record<string, PresentationAction>> = {
  ArrowRight: 'next',
  PageDown: 'next',
  ArrowLeft: 'previous',
  PageUp: 'previous',
  Home: 'first',
  End: 'last',
  Escape: 'exit',
};

/** True for elements where arrow keys and Escape belong to the user, not to the slides. */
export function isTypingTarget(target: unknown): boolean {
  if (typeof target !== 'object' || target === null) return false;
  const element = target as { tagName?: unknown; isContentEditable?: unknown };
  if (element.isContentEditable === true) return true;
  const tag = typeof element.tagName === 'string' ? element.tagName.toUpperCase() : '';
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
}

export function presentationAction(event: PresentationKey): PresentationAction | null {
  if (event.defaultPrevented || event.isComposing === true) return null;
  if (event.altKey || event.ctrlKey || event.metaKey) return null;
  if (isTypingTarget(event.target)) return null;
  return KEY_ACTIONS[event.key] ?? null;
}

/** Next index for a navigation action, clamped to the slides; never wraps around. */
export function stepIndex(
  action: Exclude<PresentationAction, 'exit'>,
  current: number,
  total: number,
): number {
  if (total <= 0) return 0;
  const last = total - 1;
  const from = Math.min(Math.max(current, 0), last);
  if (action === 'first') return 0;
  if (action === 'last') return last;
  return Math.min(Math.max(from + (action === 'next' ? 1 : -1), 0), last);
}

export function presentationStatus(index: number, total: number, label: string): string {
  return `Sección ${index + 1} de ${total}: ${label}`;
}

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

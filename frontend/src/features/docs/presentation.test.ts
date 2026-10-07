import { describe, expect, it } from 'vitest';
import {
  isTypingTarget,
  presentationAction,
  presentationStatus,
  stepIndex,
  type PresentationKey,
} from './presentation';

function key(name: string, overrides: Partial<PresentationKey> = {}): PresentationKey {
  return {
    key: name,
    altKey: false,
    ctrlKey: false,
    metaKey: false,
    defaultPrevented: false,
    target: null,
    ...overrides,
  };
}

describe('presentation keyboard actions', () => {
  it('maps arrows, page keys, Home/End and Escape', () => {
    expect(presentationAction(key('ArrowRight'))).toBe('next');
    expect(presentationAction(key('PageDown'))).toBe('next');
    expect(presentationAction(key('ArrowLeft'))).toBe('previous');
    expect(presentationAction(key('PageUp'))).toBe('previous');
    expect(presentationAction(key('Home'))).toBe('first');
    expect(presentationAction(key('End'))).toBe('last');
    expect(presentationAction(key('Escape'))).toBe('exit');
  });

  it('leaves other keys, shortcuts and handled events to the browser', () => {
    expect(presentationAction(key('ArrowDown'))).toBeNull();
    expect(presentationAction(key(' '))).toBeNull();
    expect(presentationAction(key('ArrowRight', { altKey: true }))).toBeNull();
    expect(presentationAction(key('ArrowLeft', { metaKey: true }))).toBeNull();
    expect(presentationAction(key('PageDown', { ctrlKey: true }))).toBeNull();
    expect(presentationAction(key('ArrowRight', { defaultPrevented: true }))).toBeNull();
    expect(presentationAction(key('ArrowRight', { isComposing: true }))).toBeNull();
  });

  it('never hijacks keys while the user is typing', () => {
    const fields = ['INPUT', 'TEXTAREA', 'SELECT', 'input'].map(
      (tagName) => ({ tagName }) as unknown as EventTarget,
    );
    for (const target of fields) {
      expect(presentationAction(key('ArrowRight', { target }))).toBeNull();
      expect(presentationAction(key('Escape', { target }))).toBeNull();
    }
    const editable = { tagName: 'DIV', isContentEditable: true } as unknown as EventTarget;
    expect(presentationAction(key('ArrowLeft', { target: editable }))).toBeNull();
    const section = { tagName: 'SECTION', isContentEditable: false } as unknown as EventTarget;
    expect(presentationAction(key('ArrowRight', { target: section }))).toBe('next');
  });

  it('recognises typing targets defensively', () => {
    expect(isTypingTarget(null)).toBe(false);
    expect(isTypingTarget('INPUT')).toBe(false);
    expect(isTypingTarget({ tagName: 'BUTTON' })).toBe(false);
    expect(isTypingTarget({ tagName: 'textarea' })).toBe(true);
  });
});

describe('presentation navigation', () => {
  it('moves one section at a time and clamps at both ends', () => {
    expect(stepIndex('next', 0, 12)).toBe(1);
    expect(stepIndex('previous', 5, 12)).toBe(4);
    expect(stepIndex('previous', 0, 12)).toBe(0);
    expect(stepIndex('next', 11, 12)).toBe(11);
  });

  it('jumps to the first and last sections', () => {
    expect(stepIndex('first', 7, 12)).toBe(0);
    expect(stepIndex('last', 2, 12)).toBe(11);
  });

  it('stays valid for out-of-range indexes and empty decks', () => {
    expect(stepIndex('next', 40, 12)).toBe(11);
    expect(stepIndex('previous', -3, 12)).toBe(0);
    expect(stepIndex('next', 0, 0)).toBe(0);
    expect(stepIndex('last', 0, 1)).toBe(0);
  });

  it('describes the position for screen readers as n of total', () => {
    expect(presentationStatus(2, 12, 'Qué tiene')).toBe('Sección 3 de 12: Qué tiene');
  });
});

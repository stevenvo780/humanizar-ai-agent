import { Check, Copy } from 'lucide-react';
import { useEffect, useState } from 'react';

type CopyState = 'idle' | 'copied' | 'failed';

const LABELS: Record<CopyState, string> = {
  idle: 'Copiar',
  copied: 'Copiado',
  failed: 'Selecciona el texto para copiarlo',
};

/** Copies a fixed text to the clipboard and announces the result to assistive technology. */
export function CopyButton({ text, label }: { text: string; label: string }) {
  const [state, setState] = useState<CopyState>('idle');
  useEffect(() => {
    if (state === 'idle') return;
    const timer = window.setTimeout(() => setState('idle'), 2500);
    return () => window.clearTimeout(timer);
  }, [state]);

  async function copy(): Promise<void> {
    try {
      // The Clipboard API is missing outside secure contexts; the call then throws.
      await navigator.clipboard.writeText(text);
      setState('copied');
    } catch {
      setState('failed');
    }
  }

  return (
    <>
      {/* The status comes first: compact layouts hide a header's last span. */}
      <span className="sr-only" role="status" aria-live="polite">
        {state === 'idle' ? '' : LABELS[state]}
      </span>
      <button
        type="button"
        className="docs-copy-button"
        aria-label={`${LABELS.idle} ${label}`}
        onClick={() => void copy()}
      >
        {state === 'copied' ? <Check size={13} /> : <Copy size={13} />}
        <span aria-hidden="true">{state === 'copied' ? LABELS.copied : LABELS.idle}</span>
      </button>
    </>
  );
}

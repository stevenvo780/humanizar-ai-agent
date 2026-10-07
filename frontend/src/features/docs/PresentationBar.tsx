import { ChevronLeft, ChevronRight, X } from 'lucide-react';

export function PresentationBar({
  index,
  total,
  label,
  onStep,
  onExit,
}: {
  index: number;
  total: number;
  label: string;
  onStep: (direction: 'next' | 'previous') => void;
  onExit: () => void;
}) {
  const first = index <= 0;
  const last = index >= total - 1;
  return (
    <div className="docs-presentation-bar" role="group" aria-label="Controles de presentación">
      <button
        type="button"
        aria-label="Sección anterior"
        aria-disabled={first}
        onClick={() => {
          if (!first) onStep('previous');
        }}
      >
        <ChevronLeft size={18} />
      </button>
      <span className="docs-presentation-count" aria-hidden="true">
        <strong>{index + 1}</strong> / {total}
      </span>
      <span className="docs-presentation-label" aria-hidden="true">
        {label}
      </span>
      <button
        type="button"
        aria-label="Sección siguiente"
        aria-disabled={last}
        onClick={() => {
          if (!last) onStep('next');
        }}
      >
        <ChevronRight size={18} />
      </button>
      <span className="docs-presentation-hint" aria-hidden="true">
        <kbd>←</kbd> <kbd>→</kbd> navegar
      </span>
      <button type="button" className="docs-presentation-exit" onClick={onExit}>
        <X size={15} /> Salir <kbd aria-hidden="true">Esc</kbd>
      </button>
    </div>
  );
}

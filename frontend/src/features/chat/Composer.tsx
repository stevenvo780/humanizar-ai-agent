import { useEffect, useRef } from 'react';
import type { KeyboardEvent, SyntheticEvent } from 'react';
import { ArrowUp, BookOpen, ChevronDown, ShieldCheck, Sparkles, Square } from 'lucide-react';
import type { Config } from '../../shared/api/types';

export function Composer({
  draft,
  setDraft,
  onSend,
  busy,
  onStop,
  online,
  config,
  conversation,
}: {
  draft: string;
  setDraft: (text: string) => void;
  onSend: (text: string) => Promise<void>;
  busy: boolean;
  onStop: () => void;
  online: boolean;
  config: Config | null;
  conversation: boolean;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 130)}px`;
    }
  }, [draft]);
  function submit(event: SyntheticEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (draft.trim() && !busy && online) {
      void onSend(draft);
    }
  }
  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>): void {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      if (draft.trim() && !busy && online) void onSend(draft);
    }
  }
  return (
    <div className={`composer-area ${conversation ? 'conversation-composer' : ''}`}>
      <form className="composer" onSubmit={submit}>
        <label className="sr-only" htmlFor="chat-message">
          Tu mensaje para {config?.assistant_name ?? 'el asistente'}
        </label>
        <textarea
          id="chat-message"
          ref={textareaRef}
          rows={1}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={keyDown}
          placeholder="Pregunta por productos, servicios o cómo podemos ayudarte…"
          maxLength={10000}
          disabled={!online}
        />
        <div className="composer-bottom">
          <span className="composer-context">
            <span>
              <BookOpen size={13} /> Información de {config?.company_name ?? 'la empresa'}
            </span>
            <ChevronDown size={12} />
          </span>
          <div className="composer-actions">
            <span className="keyboard-hint">↵ para enviar</span>
            {busy ? (
              <button
                type="button"
                className="send-button stop-button"
                onClick={onStop}
                aria-label="Detener respuesta"
              >
                <Square size={14} fill="currentColor" />
              </button>
            ) : (
              <button
                className="send-button"
                type="submit"
                aria-label="Enviar mensaje"
                disabled={!draft.trim() || !online}
              >
                <ArrowUp size={19} />
              </button>
            )}
          </div>
        </div>
      </form>
      <div className="composer-footnote">
        <ShieldCheck size={11} />
        <span>
          {!config
            ? 'Conectando con el asistente…'
            : config.mode === 'demo'
              ? 'Modo demo · Respuestas de demostración, sin llamadas a Claude.'
              : 'El asistente puede cometer errores. Consulta las fuentes de cada respuesta.'}
        </span>
        <span className="composer-powered">
          Hecho para pensar contigo <Sparkles size={10} />
        </span>
      </div>
    </div>
  );
}

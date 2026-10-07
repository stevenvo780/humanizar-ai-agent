import { BookOpen, ChevronDown, Terminal } from 'lucide-react';
import type { ChatMessage } from '../../shared/api/types';
import { BrandMark } from '../../shared/ui/BrandMark';
import { plural } from '../../shared/utils/plural';
import { ChatMarkdown } from '../documents/DocumentMarkdown';
import { SourceCard } from './SourceCard';
import { Trace } from './Trace';

export function ChatMessageItem({
  message,
  userName,
  assistant,
  company,
  streamStatus,
}: {
  message: ChatMessage;
  userName: string;
  assistant: string;
  company: string;
  streamStatus: string;
}) {
  return (
    <article className={`message message-${message.role}`}>
      <div className="message-avatar">
        {message.role === 'assistant' ? <BrandMark small /> : userName.slice(0, 1).toUpperCase()}
      </div>
      <div className="message-content">
        <div className="message-byline">
          <strong>{message.role === 'assistant' ? assistant : userName}</strong>
          {message.role === 'assistant' && <span>Asistente de {company}</span>}
        </div>
        {message.content ? (
          <ChatMarkdown content={message.content} />
        ) : (
          !message.error && (
            <div className="thinking">
              <span />
              <span />
              <span />
              <p>{streamStatus || 'Preparando una respuesta…'}</p>
            </div>
          )
        )}
        {message.error && (
          <div className="message-error" role="alert">
            {message.error}
          </div>
        )}
        {message.sources.length > 0 && (
          <div className="message-sources">
            <span>
              <BookOpen size={12} />
              {plural(message.sources.length, 'fuente consultada', 'fuentes consultadas')}
            </span>
            {message.sources.map((source, index) => (
              <SourceCard key={`${source.chunk_id}-${index}`} source={source} index={index} />
            ))}
          </div>
        )}
        {message.trace.length > 0 && (
          <details className="message-tools">
            <summary>
              <Terminal size={12} />
              {plural(message.trace.length, 'herramienta ejecutada', 'herramientas ejecutadas')}
              <ChevronDown size={12} />
            </summary>
            {message.trace.map((trace) => (
              <Trace key={trace.id} trace={trace} />
            ))}
          </details>
        )}
      </div>
    </article>
  );
}

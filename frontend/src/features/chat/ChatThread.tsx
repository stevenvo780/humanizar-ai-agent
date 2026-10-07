import type { RefObject } from 'react';
import { MessageSquare } from 'lucide-react';
import type { ChatMessage } from '../../shared/api/types';
import { ChatMessageItem } from './ChatMessageItem';

export function ChatThread({
  title,
  messages,
  busy,
  streamStatus,
  userName,
  assistant,
  company,
  endRef,
}: {
  title: string | undefined;
  messages: ChatMessage[];
  busy: boolean;
  streamStatus: string;
  userName: string;
  assistant: string;
  company: string;
  endRef: RefObject<HTMLDivElement | null>;
}) {
  return (
    <section className="conversation" aria-label="Conversación" aria-busy={busy}>
      <div className="conversation-heading">
        <span>
          <MessageSquare size={14} />
          {title}
        </span>
        <span className="local-label">Historial de tu cuenta</span>
      </div>
      {messages.map((message) => (
        <ChatMessageItem
          key={message.id}
          message={message}
          userName={userName}
          assistant={assistant}
          company={company}
          streamStatus={streamStatus}
        />
      ))}
      <div ref={endRef} />
    </section>
  );
}

import { Clock3, MessageSquare, X } from 'lucide-react';
import type { Conversation } from '../../shared/api/types';

export function RecentConversations({
  conversations,
  activeId,
  busy,
  onOpen,
  onRemove,
}: {
  conversations: Conversation[];
  activeId: string | null;
  busy: boolean;
  onOpen: (id: string) => void;
  onRemove: (id: string) => Promise<void>;
}) {
  return (
    <>
      <div className="recent-heading">
        <span className="sidebar-section-label">CONVERSACIONES</span>
        <Clock3 size={12} />
      </div>
      <div className="recent-list">
        {conversations.slice(0, 7).map((item) => (
          <div className={`recent-item ${activeId === item.id ? 'selected' : ''}`} key={item.id}>
            <button
              disabled={busy}
              onClick={() => {
                onOpen(item.id);
              }}
            >
              <MessageSquare size={14} />
              <span>{item.title}</span>
            </button>
            <button
              className="remove-chat"
              disabled={busy}
              aria-label={`Eliminar conversación ${item.title}`}
              onClick={() => void onRemove(item.id)}
            >
              <X size={12} />
            </button>
          </div>
        ))}
        {conversations.length === 0 && (
          <p className="recent-empty">
            Estamos para ayudarte.
            <br />
            Las conversaciones se guardan
            <br />
            en tu cuenta.
          </p>
        )}
      </div>
    </>
  );
}

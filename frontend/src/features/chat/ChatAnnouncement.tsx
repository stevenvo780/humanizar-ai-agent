import type { ChatResponse } from '../../shared/api/types';

export function completedChatAnnouncement(response: ChatResponse, assistant: string): string {
  return `Respuesta de ${assistant} completada. ${response.answer}`;
}

export function ChatAnnouncement({ message }: { message: string }) {
  return (
    <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
      {message}
    </div>
  );
}

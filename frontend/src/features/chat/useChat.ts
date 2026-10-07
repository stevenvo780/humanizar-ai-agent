import { useEffect, useRef, useState } from 'react';
import { api, errorMessage, streamChat } from '../../shared/api/api';
import type { ChatMessage, Conversation } from '../../shared/api/types';
import { createId } from '../../shared/utils/id';
import { completedChatAnnouncement } from './ChatAnnouncement';

const EMPTY_MESSAGES: ChatMessage[] = [];

interface ChatOptions {
  userId: string;
  online: boolean;
  assistant: string;
  onOffline: () => void;
}

/** Account conversation history plus the streaming chat request lifecycle. */
export function useChat({ userId, online, assistant, onOffline }: ChatOptions) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [streamStatus, setStreamStatus] = useState('');
  const [announcement, setAnnouncement] = useState('');
  const [storageError, setStorageError] = useState('');
  const abortRef = useRef<AbortController | null>(null);
  const busyRef = useRef(false);
  const messagesEnd = useRef<HTMLDivElement>(null);
  const active = conversations.find((item) => item.id === activeId);
  const messages = active?.messages ?? EMPTY_MESSAGES;
  const selected = [...messages].reverse().find((item) => item.role === 'assistant');

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);
  useEffect(() => {
    let current = true;
    setHistoryLoading(true);
    setConversations([]);
    setActiveId(null);
    void api
      .conversations()
      .then((result) => {
        if (current) {
          setConversations(result.conversations);
          setStorageError('');
        }
      })
      .catch((err: unknown) => {
        if (current)
          setStorageError(`No pudimos cargar el historial de tu cuenta. ${errorMessage(err)}`);
      })
      .finally(() => {
        if (current) setHistoryLoading(false);
      });
    return () => {
      current = false;
    };
  }, [userId]);
  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: busy ? 'instant' : 'smooth', block: 'end' });
  }, [messages, busy]);

  /** Clears the active conversation; returns false while a response is streaming. */
  function startNewConversation(): boolean {
    if (busyRef.current) return false;
    setActiveId(null);
    setDraft('');
    return true;
  }
  async function removeConversation(id: string): Promise<void> {
    try {
      await api.deleteConversation(id);
      setConversations((current) => current.filter((chat) => chat.id !== id));
      if (activeId === id) setActiveId(null);
    } catch (err) {
      setStorageError(errorMessage(err));
    }
  }
  function stop(): void {
    abortRef.current?.abort();
  }
  function updateMessage(
    conversationId: string,
    messageId: string,
    update: (message: ChatMessage) => ChatMessage,
  ): void {
    setConversations((current) =>
      current.map((item) =>
        item.id === conversationId
          ? {
              ...item,
              messages: item.messages.map((message) =>
                message.id === messageId ? update(message) : message,
              ),
            }
          : item,
      ),
    );
  }

  async function send(text: string): Promise<void> {
    if (!text.trim() || busyRef.current || !online || historyLoading) return;
    const message = text.trim();
    const conversationId = activeId ?? createId();
    const assistantId = createId();
    const userMessage: ChatMessage = {
      id: createId(),
      role: 'user',
      content: message,
      sources: [],
      trace: [],
    };
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      sources: [],
      trace: [],
    };
    const history: { role: 'user' | 'assistant'; content: string }[] = [];
    let historyCharacters = 0;
    for (const item of [...messages].reverse()) {
      if (!item.content || item.error) continue;
      if (history.length >= 40 || historyCharacters + item.content.length > 32000) break;
      history.unshift({ role: item.role, content: item.content });
      historyCharacters += item.content.length;
    }
    setConversations((current) =>
      activeId
        ? current.map((item) =>
            item.id === conversationId
              ? {
                  ...item,
                  messages: [...item.messages, userMessage, assistantMessage],
                  updatedAt: Date.now(),
                }
              : item,
          )
        : [
            {
              id: conversationId,
              title: message.slice(0, 44),
              messages: [userMessage, assistantMessage],
              updatedAt: Date.now(),
            },
            ...current,
          ].slice(0, 20),
    );
    setActiveId(conversationId);
    setDraft('');
    setBusy(true);
    setAnnouncement('');
    busyRef.current = true;
    setStreamStatus('Buscando el contexto adecuado…');
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await streamChat(
        message,
        history,
        active?.sessionId ?? conversationId,
        controller.signal,
        (event) => {
          if (event.type === 'status') setStreamStatus(event.message);
          if (event.type === 'token')
            updateMessage(conversationId, assistantId, (item) => ({
              ...item,
              content: item.content + event.text,
            }));
          if (event.type === 'tool')
            updateMessage(conversationId, assistantId, (item) => ({
              ...item,
              trace: [...item.trace.filter((trace) => trace.id !== event.trace.id), event.trace],
            }));
          if (event.type === 'done') {
            setAnnouncement(completedChatAnnouncement(event.response, assistant));
            updateMessage(conversationId, assistantId, (item) => ({
              ...item,
              content: event.response.answer,
              sources: event.response.sources,
              trace: event.response.trace,
            }));
            setConversations((current) =>
              current.map((item) =>
                item.id === conversationId
                  ? { ...item, sessionId: event.response.session_id }
                  : item,
              ),
            );
          }
        },
      );
    } catch (err) {
      updateMessage(conversationId, assistantId, (item) => ({
        ...item,
        error: controller.signal.aborted
          ? 'Respuesta detenida. Puedes enviar otro mensaje.'
          : errorMessage(err),
      }));
      if (!controller.signal.aborted) {
        try {
          await api.health();
        } catch {
          onOffline();
        }
      }
    } finally {
      setBusy(false);
      busyRef.current = false;
      setStreamStatus('');
      abortRef.current = null;
    }
  }

  return {
    conversations,
    historyLoading,
    activeId,
    selectConversation: setActiveId,
    active,
    messages,
    selected,
    draft,
    setDraft,
    busy,
    streamStatus,
    announcement,
    storageError,
    messagesEnd,
    send,
    stop,
    startNewConversation,
    removeConversation,
  };
}

export type ChatController = ReturnType<typeof useChat>;

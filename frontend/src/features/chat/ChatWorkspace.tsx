import type { Config } from '../../shared/api/types';
import type { QuickPrompt } from '../../shared/config/company';
import { ChatThread } from './ChatThread';
import { Composer } from './Composer';
import type { ChatController } from './useChat';
import { Welcome } from './Welcome';

/** Assistant section: welcome prompts or the active thread, followed by the composer. */
export function ChatWorkspace({
  chat,
  online,
  config,
  assistant,
  company,
  humanizar,
  prompts,
  userName,
}: {
  chat: ChatController;
  online: boolean;
  config: Config | null;
  assistant: string;
  company: string;
  humanizar: boolean;
  prompts: QuickPrompt[];
  userName: string;
}) {
  const { messages, busy, historyLoading } = chat;
  return (
    <>
      {messages.length === 0 ? (
        <Welcome
          assistant={assistant}
          company={company}
          humanizar={humanizar}
          prompts={prompts}
          disabled={!online || busy || historyLoading}
          onPrompt={chat.send}
        />
      ) : (
        <ChatThread
          title={chat.active?.title}
          messages={messages}
          busy={busy}
          streamStatus={chat.streamStatus}
          userName={userName}
          assistant={assistant}
          company={company}
          endRef={chat.messagesEnd}
        />
      )}
      <Composer
        draft={chat.draft}
        setDraft={chat.setDraft}
        onSend={chat.send}
        busy={busy}
        onStop={chat.stop}
        online={online && !historyLoading}
        config={config}
        conversation={messages.length > 0}
      />
    </>
  );
}

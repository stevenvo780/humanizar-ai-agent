import type { ReactNode } from 'react';
import { ArrowUpRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function safeDocumentUrl(value: string): string {
  try {
    const url = new URL(value);
    return ['https:', 'http:', 'mailto:'].includes(url.protocol) ? url.href : '';
  } catch {
    return '';
  }
}

/** Only explicit link destinations survive; image sources are always dropped. */
function safeUrlTransform(value: string, key: string): string {
  return key === 'href' ? safeDocumentUrl(value) : '';
}

function safeComponents(linkSuffix?: ReactNode): Components {
  return {
    a: ({ href, children }) =>
      href ? (
        <a href={href} target="_blank" rel="noopener noreferrer">
          {children}
          {linkSuffix}
        </a>
      ) : (
        <span>{children}</span>
      ),
    // Never render <img>: a remote image would load without a click (tracking or exfiltration).
    img: ({ alt }) => (
      <span className="document-image-note">Imagen omitida{alt ? `: ${alt}` : ''}.</span>
    ),
    table: ({ children }) => (
      <div className="document-table-scroll">
        <table>{children}</table>
      </div>
    ),
  };
}

const DOCUMENT_COMPONENTS = safeComponents();
const CHAT_COMPONENTS = safeComponents(<ArrowUpRight size={12} aria-hidden="true" />);

function SafeMarkdown({
  content,
  className,
  components,
}: {
  content: string;
  className: string;
  components: Components;
}) {
  return (
    <div className={className}>
      <ReactMarkdown
        skipHtml
        remarkPlugins={[remarkGfm]}
        urlTransform={safeUrlTransform}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

export function DocumentMarkdown({ content }: { content: string }) {
  return (
    <SafeMarkdown
      content={content}
      className="markdown document-markdown"
      components={DOCUMENT_COMPONENTS}
    />
  );
}

/** Model output is untrusted: same safe rendering as documents, with GFM tables. */
export function ChatMarkdown({ content }: { content: string }) {
  return (
    <SafeMarkdown
      content={content}
      className="markdown chat-markdown"
      components={CHAT_COMPONENTS}
    />
  );
}

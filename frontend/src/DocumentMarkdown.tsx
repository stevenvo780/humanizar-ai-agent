import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function safeDocumentUrl(value: string): string {
  try {
    const url = new URL(value);
    return ['https:', 'http:', 'mailto:'].includes(url.protocol) ? url.href : '';
  } catch {
    return '';
  }
}

export function DocumentMarkdown({ content }: { content: string }) {
  return (
    <div className="markdown document-markdown">
      <ReactMarkdown
        skipHtml
        remarkPlugins={[remarkGfm]}
        urlTransform={(value, key) => (key === 'href' ? safeDocumentUrl(value) : '')}
        components={{
          a: ({ href, children }) =>
            href ? (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            ) : (
              <span>{children}</span>
            ),
          img: ({ alt }) => (
            <span className="document-image-note">Imagen omitida{alt ? `: ${alt}` : ''}.</span>
          ),
          table: ({ children }) => (
            <div className="document-table-scroll">
              <table>{children}</table>
            </div>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

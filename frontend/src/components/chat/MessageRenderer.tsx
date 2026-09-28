import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { CodeBlock } from './CodeBlock';
import './message.css';

interface MessageRendererProps {
  content: string;
  className?: string;
}

/**
 * Preprocesses raw text to normalize LaTeX equation delimiters so remark-math and KaTeX
 * parse both standard Markdown ($...$, $$...$$) and LaTeX brackets (\[...\], \(...\)).
 */
function preprocessMathDelimiters(text: string): string {
  if (!text) return '';

  // 1. Strip all keyboard emojis, emoticons, and Unicode pictographs
  let processed = text.replace(
    /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F600}-\u{1F64F}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{200D}]|[\u{FE0F}]|[\u{1FA00}-\u{1FAFF}]|[\u{1F000}-\u{1F02F}]/gu,
    ''
  );

  // 2. Models sometimes escape Markdown punctuation while serializing a response.
  // Normalize those escapes before remark parses the document.
  processed = processed
    .replace(/\\\\([*_`#>\[\]()])/g, '$1')
    .replace(/\\\\\\\\([A-Za-z])/g, '\\\\$1');

  // 3. Normalize accidental headings in chat turns so bubbles retain uniform body typography
  processed = processed.replace(/^#{1,6}\s+/gm, '');

  // 4. Strip asterisks (*, **) to eliminate vocal 'star star' and visual clutter
  processed = processed.replace(/\*{1,3}([^*]+)\*{1,3}/g, '$1').replace(/\*{1,3}/g, '');

  // 5. Normalize inline smashed list items (e.g. "theory. - Masashi Sugiyama" or "Japan: - Shunichi")
  // into structured Markdown bullet lines
  processed = processed.replace(/([.:;])\s*-\s+([A-Za-z0-9])/g, '$1\n\n- $2');

  // 6. Normalize display equations: \[ ... \] -> $$ ... $$
  processed = processed.replace(/\\\[([\s\S]*?)\\\]/g, (_match, eq) => {
    return `\n\n$$\n${eq.trim()}\n$$\n\n`;
  });

  // 7. Normalize inline equations: \( ... \) -> $ ... $
  processed = processed.replace(/\\\(([\s\S]*?)\\\)/g, (_match, eq) => {
    return `$${eq.trim()}$`;
  });

  return processed.trim();
}

export const MessageRenderer: React.FC<MessageRendererProps> = ({
  content,
  className = '',
}) => {
  const processedContent = useMemo(() => {
    return preprocessMathDelimiters(content);
  }, [content]);

  return (
    <div className={`message-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { output: 'htmlAndMathml', strict: false }]]}
        components={{
          // Fenced and inline code rendering
          code({ className: codeClass, children, ...props }) {
            const match = /language-(\w+)/.exec(codeClass || '');
            const rawCode = String(children);
            const isFenced = Boolean(match) || rawCode.includes('\n');

            if (isFenced) {
              const language = match ? match[1] : '';
              return (
                <CodeBlock
                  language={language}
                  code={rawCode}
                />
              );
            }

            return (
              <code className={codeClass} {...props}>
                {children}
              </code>
            );
          },

          // Transparent pre wrapper since CodeBlock manages its own container
          pre({ children }) {
            return <>{children}</>;
          },

          // Safe external hyperlinks
          a({ href, children, ...props }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                {...props}
              >
                {children}
              </a>
            );
          },

          // Responsive image rendering
          img({ src, alt, ...props }) {
            return (
              <img
                src={src}
                alt={alt ?? ''}
                loading="lazy"
                {...props}
              />
            );
          },

          // Responsive table wrapper for horizontal scroll
          table({ children, ...props }) {
            return (
              <div className="message-table-wrapper">
                <table {...props}>{children}</table>
              </div>
            );
          },
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
};

export default MessageRenderer;


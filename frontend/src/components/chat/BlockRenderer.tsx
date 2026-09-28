import React, { useState } from 'react';
import { 
  Wrench, 
  ExternalLink, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Download,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { MessageBlock } from '@/types';
import { CodeBlock } from './CodeBlock';

interface BlockRendererProps {
  block: MessageBlock;
}

export const BlockRenderer: React.FC<BlockRendererProps> = ({ block }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  switch (block.type) {
    case 'code':
      return (
        <CodeBlock
          code={block.code}
          language={block.language}
          title={block.title}
        />
      );

    case 'tool': {
      const isRunning = block.status === 'running';
      const isSuccess = block.status === 'success';
      const isError = block.status === 'error';

      return (
        <div className="my-2.5 rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] p-3 shadow-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-[var(--color-surface-muted)] border border-[var(--color-hairline)] flex items-center justify-center text-[var(--color-action)]">
                {isRunning ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--color-action)]" />
                ) : (
                  <Wrench className="w-3.5 h-3.5" />
                )}
              </div>
              <div>
                <div className="font-mono text-[12px] font-bold text-[var(--color-ink)] uppercase">
                  {block.tool}
                </div>
                <div className="text-[11px] text-[var(--color-muted)] flex items-center gap-1 mt-0.5">
                  {isSuccess && <CheckCircle2 className="w-3 h-3 text-[var(--color-success)]" />}
                  {isError && <AlertCircle className="w-3 h-3 text-[var(--color-danger)]" />}
                  <span>
                    {isRunning ? 'Executing action...' : isSuccess ? 'Action completed' : 'Action failed'}
                  </span>
                  {block.durationMs && (
                    <span className="font-mono text-[10px]">· {block.durationMs}ms</span>
                  )}
                </div>
              </div>
            </div>

            {(block.input || block.output) && (
              <button
                type="button"
                onClick={() => setIsExpanded((prev) => !prev)}
                className="flex items-center gap-1 text-[11px] font-mono text-[var(--color-link)] hover:underline cursor-pointer px-2 py-1 rounded hover:bg-[var(--color-surface-muted)]"
              >
                <span>{isExpanded ? 'Hide payload' : 'Details'}</span>
                {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
            )}
          </div>

          {isExpanded && (
            <div className="mt-2.5 pt-2.5 border-t border-[var(--color-hairline)] flex flex-col gap-2 font-mono text-[11.5px]">
              {block.input && (
                <div className="p-2 rounded bg-[var(--color-surface-muted)]/60 border border-[var(--color-hairline)]">
                  <div className="text-[10px] uppercase font-bold text-[var(--color-muted)] mb-1">Parameters</div>
                  <pre className="overflow-x-auto m-0 p-0 text-[var(--color-body)]">{JSON.stringify(block.input, null, 2)}</pre>
                </div>
              )}
              {block.output && (
                <div className="p-2 rounded bg-[var(--color-surface-muted)]/60 border border-[var(--color-hairline)]">
                  <div className="text-[10px] uppercase font-bold text-[var(--color-muted)] mb-1">Result</div>
                  <pre className="overflow-x-auto m-0 p-0 text-[var(--color-body)]">{typeof block.output === 'string' ? block.output : JSON.stringify(block.output, null, 2)}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      );
    }

    case 'citation':
      return (
        <a
          href={block.url}
          target="_blank"
          rel="noopener noreferrer"
          className="my-2 block rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] p-3 hover:border-[var(--color-muted)] shadow-xs transition-all group"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="text-[12.5px] font-semibold text-[var(--color-ink)] group-hover:text-[var(--color-link)] flex items-center gap-1.5 truncate">
                <span>{block.title || block.url}</span>
                <ExternalLink className="w-3 h-3 text-[var(--color-muted)] group-hover:text-[var(--color-link)] shrink-0" />
              </div>
              {block.snippet && (
                <p className="text-[12px] text-[var(--color-muted)] mt-1 line-clamp-2 leading-relaxed">
                  {block.snippet}
                </p>
              )}
            </div>
          </div>
        </a>
      );

    case 'file':
      return (
        <div className="my-2.5 flex items-center justify-between rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] p-3 shadow-xs">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-[var(--color-surface-muted)] border border-[var(--color-hairline)] flex items-center justify-center text-[var(--color-action)] shrink-0">
              <FileText className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="text-[13px] font-semibold text-[var(--color-ink)] truncate">
                {block.name}
              </div>
              <div className="font-mono text-[11px] text-[var(--color-muted)]">
                {block.size ? `${(block.size / 1024).toFixed(1)} KB` : block.mimeType || 'Document'}
              </div>
            </div>
          </div>
          <a
            href={block.url}
            download={block.name}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-[var(--color-surface-muted)] hover:bg-[var(--color-hairline)] text-[var(--color-ink)] text-[11.5px] font-medium transition-colors shrink-0"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download</span>
          </a>
        </div>
      );

    case 'image':
      return (
        <div className="my-3 rounded-xl overflow-hidden border border-[var(--color-hairline)] bg-[var(--color-surface)] shadow-xs">
          <img
            src={block.url}
            alt={block.alt || 'Assistant visual attachment'}
            loading="lazy"
            className="w-full h-auto object-cover max-h-[360px]"
          />
          {block.caption && (
            <div className="px-3 py-2 text-[11.5px] text-[var(--color-muted)] border-t border-[var(--color-hairline)] bg-[var(--color-surface-muted)]/40 font-sans">
              {block.caption}
            </div>
          )}
        </div>
      );

    case 'link_preview':
      return (
        <a
          href={block.url}
          target="_blank"
          rel="noopener noreferrer"
          className="my-2.5 flex flex-col sm:flex-row gap-3 rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] p-3 hover:border-[var(--color-muted)] shadow-xs transition-all group"
        >
          {block.image && (
            <img
              src={block.image}
              alt=""
              className="w-full sm:w-24 h-24 rounded-lg object-cover border border-[var(--color-hairline)] shrink-0"
            />
          )}
          <div className="min-w-0 flex flex-col justify-center">
            <div className="text-[13px] font-semibold text-[var(--color-ink)] group-hover:text-[var(--color-link)] flex items-center gap-1.5">
              <span className="truncate">{block.title || block.url}</span>
              <ExternalLink className="w-3 h-3 text-[var(--color-muted)] shrink-0" />
            </div>
            {block.description && (
              <p className="text-[12px] text-[var(--color-muted)] mt-1 line-clamp-2 leading-relaxed">
                {block.description}
              </p>
            )}
            <span className="text-[11px] font-mono text-[var(--color-faint)] mt-1 truncate">
              {new URL(block.url).hostname}
            </span>
          </div>
        </a>
      );

    case 'text':
    default:
      return null;
  }
};

export default BlockRenderer;


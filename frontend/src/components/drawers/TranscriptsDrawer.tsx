import React, { useEffect, useRef } from 'react';
import { X, Trash2, MessageSquare, Bot, User } from 'lucide-react';
import { TranscriptEntry } from '@/types';
import { MessageRenderer } from '../chat';

interface TranscriptsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  transcripts: TranscriptEntry[];
  onClear: () => void;
}

export const TranscriptsDrawer: React.FC<TranscriptsDrawerProps> = ({
  isOpen,
  onClose,
  transcripts,
  onClear,
}) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (isOpen && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [isOpen, transcripts.length]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* 1. Calm Backdrop Scrim */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/25 transition-opacity duration-200"
        aria-hidden="true"
      />

      {/* 2. Slide-Over Panel */}
      <aside
        role="dialog"
        aria-label="Session transcript log"
        className="relative w-full sm:w-[480px] h-full bg-[var(--color-surface)] border-l border-[var(--color-hairline)] shadow-xl z-10 p-5 flex flex-col gap-4 animate-in slide-in-from-right duration-200"
      >
        {/* Drawer Header */}
        <div className="flex justify-between items-center pb-3 border-b border-[var(--color-hairline)] shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-md bg-[var(--color-surface-muted)] border border-[var(--color-hairline)] flex items-center justify-center text-[var(--color-muted)]">
              <MessageSquare className="w-4 h-4" />
            </div>
            <div>
              <div className="font-['DM_Serif_Display'] text-[17px] text-[var(--color-ink)] leading-none">
                Session log
              </div>
              <div className="font-mono text-[11px] text-[var(--color-muted)] mt-0.5">
                {transcripts.length} {transcripts.length === 1 ? 'entry' : 'entries'} recorded
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClear}
              disabled={transcripts.length === 0}
              title="Clear transcript log"
              className="px-2.5 py-1 rounded-md border border-[var(--color-hairline)] text-[var(--color-muted)] hover:text-[var(--color-danger)] hover:bg-[#fcf0f0] text-[12px] font-medium flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
            <button
              onClick={onClose}
              title="Close log"
              aria-label="Close log"
              className="w-8 h-8 rounded-md hover:bg-[var(--color-surface-muted)] text-[var(--color-muted)] hover:text-[var(--color-ink)] flex items-center justify-center transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Drawer Feed */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto flex flex-col gap-3 pr-1">
          {transcripts.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 text-[var(--color-muted)] gap-2">
              <MessageSquare className="w-8 h-8 text-[var(--color-faint)]" />
              <p className="text-[13px] font-medium text-[var(--color-ink)]">
                No dialogue logs yet
              </p>
              <p className="text-[12px] text-[var(--color-muted)]">
                Spoken dialogue and text inputs from the active session will appear here.
              </p>
            </div>
          ) : (
            transcripts.map((entry) => {
              const isUser = entry.role === 'user';
              return (
                <div
                  key={entry.id}
                  className={`rounded-lg p-3.5 flex flex-col gap-1.5 border border-[var(--color-hairline)] ${
                    isUser
                      ? 'bg-[var(--color-surface-muted)]/50 ml-3'
                      : 'bg-[var(--color-surface)] mr-3'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-1.5 text-[11px] font-medium">
                      {isUser ? (
                        <User className="w-3.5 h-3.5 text-[var(--color-action)]" />
                      ) : (
                        <Bot className="w-3.5 h-3.5 text-[var(--color-link)]" />
                      )}
                      <span className={isUser ? 'text-[var(--color-action)]' : 'text-[var(--color-link)]'}>
                        {isUser ? 'You' : 'Assistant'}
                      </span>
                    </div>
                    <span className="font-mono text-[10px] text-[var(--color-muted)]">
                      {entry.timestamp}
                    </span>
                  </div>

                  <div className="text-[13px] leading-relaxed text-[var(--color-ink)]">
                    {isUser ? (
                      <div className="whitespace-pre-wrap">{entry.content}</div>
                    ) : (
                      <MessageRenderer content={entry.content} />
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </aside>
    </div>
  );
};

export default TranscriptsDrawer;

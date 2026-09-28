import React from 'react';
import { TranscriptEntry, MessageBlock } from '@/types';
import { MessageRenderer } from './MessageRenderer';
import { BlockRenderer } from './BlockRenderer';

interface MessageProps {
  entry: TranscriptEntry;
  className?: string;
}

export const Message: React.FC<MessageProps> = ({ entry, className = '' }) => {
  const isUser = entry.role === 'user';
  const displayContent = entry.display?.content || entry.content;
  const blocks: MessageBlock[] = entry.blocks || [];

  return (
    <article className={`w-full flex flex-col gap-2 ${className}`}>
      {/* 1. Core Markdown & Mathematics Content */}
      {isUser ? (
        <div className="text-[13.5px] leading-relaxed whitespace-pre-wrap font-sans">
          {displayContent}
        </div>
      ) : (
        <MessageRenderer content={displayContent} />
      )}

      {/* 2. Structured Rich Blocks (Tools, Files, Citations, Images) */}
      {blocks.length > 0 && (
        <div className="flex flex-col gap-2 mt-1">
          {blocks.map((block, idx) => (
            <BlockRenderer key={idx} block={block} />
          ))}
        </div>
      )}
    </article>
  );
};

export default Message;


import React from 'react';
import { X, Trash2, MessageSquare } from 'lucide-react';
import { TranscriptEntry } from '@/types';

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
  return (
    <aside
      className={`fixed top-5 bottom-6 right-7 w-[380px] glass-drawer rounded-3xl p-5 flex flex-col gap-4 z-20 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] ${
        isOpen ? 'translate-x-0 opacity-100 pointer-events-auto' : 'translate-x-[calc(100%+40px)] opacity-0 pointer-events-none'
      }`}
    >
      {/* Drawer Header */}
      <div className="flex justify-between items-center pb-3 border-b border-white/10">
        <div className="font-['Syne'] text-[14px] font-extrabold tracking-wider uppercase text-white flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-[#00F0FF]" />
          <span>Session Log</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={onClear}
            title="Clear Log"
            className="w-7 h-7 rounded-full bg-white/5 border border-white/10 text-slate-300 flex items-center justify-center hover:bg-white/15 transition-all cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full bg-white/5 border border-white/10 text-slate-300 flex items-center justify-center hover:bg-white/15 transition-all cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Drawer Content Feed */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-2.5 pr-1">
        {transcripts.length === 0 ? (
          <div className="text-center py-8 text-slate-500 font-['JetBrains_Mono'] text-[11px]">
            SESSION LOG IS EMPTY
          </div>
        ) : (
          transcripts.map((entry) => {
            const isUser = entry.role === 'user';
            return (
              <div
                key={entry.id}
                className="bg-[#040914]/60 border border-white/6 rounded-xl p-3 flex flex-col gap-1"
              >
                <div className="flex justify-between font-['JetBrains_Mono'] text-[10px] text-slate-500">
                  <span className={isUser ? 'text-[#A855F7] font-bold' : 'text-[#00F0FF] font-bold'}>
                    {isUser ? 'OPERATOR' : 'AETHERIS'}
                  </span>
                  <span>{entry.timestamp}</span>
                </div>
                <div className="text-[12.5px] leading-relaxed text-slate-200">{entry.content}</div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};

import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, ChevronDown, Terminal, Send, X } from 'lucide-react';
import { SessionState } from '@/types';

interface ControllerDeckProps {
  state: SessionState;
  selectedVoice: string;
  onVoiceChange: (voice: string) => void;
  onToggleSession: () => void;
  onInjectText: (text: string) => void;
}

const VOICE_OPTIONS = [
  { id: 'aura-2-thalia-en', label: 'Thalia (Natural)' },
  { id: 'aura-2-orion-en', label: 'Orion (Executive)' },
  { id: 'aura-2-arcas-en', label: 'Arcas (Deep)' },
  { id: 'aura-2-perseus-en', label: 'Perseus (Dynamic)' },
  { id: 'aura-2-zeus-en', label: 'Zeus (Resonant)' },
  { id: 'aura-asteria-en', label: 'Asteria (Classic)' },
];

export const ControllerDeck: React.FC<ControllerDeckProps> = ({
  state,
  selectedVoice,
  onVoiceChange,
  onToggleSession,
  onInjectText,
}) => {
  const [inputText, setInputText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const isConnected = state !== 'DISCONNECTED';

  const handleSend = () => {
    if (!inputText.trim()) return;
    onInjectText(inputText.trim());
    setInputText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '38px';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea height as user types
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = '38px';
      if (textareaRef.current.scrollHeight > 38) {
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 100)}px`;
      }
    }
  }, [inputText]);

  return (
    <div className="w-full max-w-3xl mx-auto flex items-end gap-2.5 p-2 rounded-2xl bg-[#0c1220]/90 backdrop-blur-2xl border border-white/12 shadow-[0_16px_45px_rgba(0,0,0,0.6)] focus-within:border-[#10B981]/50 transition-all">
      {/* 1. Hardware Mic Button */}
      <button
        onClick={onToggleSession}
        className={`h-10 px-4 rounded-xl font-['Space_Grotesk'] text-[12.5px] font-bold tracking-wide flex items-center justify-center gap-2 transition-all duration-300 cursor-pointer flex-shrink-0 ${
          isConnected
            ? 'bg-red-500/90 text-white hover:bg-red-500 shadow-[0_0_20px_rgba(239,68,68,0.4)]'
            : 'bg-[#10B981] text-zinc-950 hover:bg-[#34D399] shadow-[0_0_20px_rgba(16,185,129,0.35)]'
        }`}
      >
        {isConnected ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
        <span className="hidden sm:inline">{isConnected ? 'Disconnect' : 'Start Voice'}</span>
      </button>

      {/* 2. Text Input Area (Expands gracefully, default 38px) */}
      <div className="flex-1 relative flex items-center bg-[#070b14]/80 border border-white/8 rounded-xl px-3 focus-within:border-[#00F0FF]/40 transition-all min-h-[38px]">
        <Terminal className="w-4 h-4 text-zinc-500 mr-2 flex-shrink-0" />
        <textarea
          ref={textareaRef}
          rows={1}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!isConnected}
          placeholder={
            isConnected
              ? 'Type a message (or speak naturally)...'
              : 'Start Voice to begin voice reasoning...'
          }
          className="w-full bg-transparent py-2 text-white text-[13.5px] font-['Plus_Jakarta_Sans'] outline-none placeholder:text-zinc-500 resize-none h-[38px] max-h-[100px] disabled:opacity-40 disabled:cursor-not-allowed leading-relaxed"
        />

        {inputText.trim() && (
          <button
            onClick={() => setInputText('')}
            title="Clear text"
            className="p-1 text-zinc-400 hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* 3. Voice Model Selector */}
      <div className="relative flex items-center flex-shrink-0">
        <select
          value={selectedVoice}
          onChange={(e) => onVoiceChange(e.target.value)}
          className="h-10 bg-[#070b14]/80 border border-white/8 rounded-xl py-2 pl-3 pr-7 text-zinc-300 font-['Space_Grotesk'] text-[12px] font-medium outline-none cursor-pointer appearance-none hover:border-white/15 focus:border-[#10B981] transition-all"
        >
          {VOICE_OPTIONS.map((v) => (
            <option key={v.id} value={v.id} className="bg-[#0e1424] text-white">
              {v.label}
            </option>
          ))}
        </select>
        <ChevronDown className="w-3.5 h-3.5 absolute right-2 text-zinc-400 pointer-events-none" />
      </div>

      {/* 4. Send Button */}
      <button
        onClick={handleSend}
        disabled={!isConnected || !inputText.trim()}
        className="h-10 w-10 rounded-xl bg-[#10B981] hover:bg-[#34D399] text-zinc-950 flex items-center justify-center transition-all shadow-[0_0_15px_rgba(16,185,129,0.3)] disabled:opacity-25 disabled:cursor-not-allowed disabled:shadow-none cursor-pointer flex-shrink-0"
      >
        <Send className="w-4 h-4" />
      </button>
    </div>
  );
};

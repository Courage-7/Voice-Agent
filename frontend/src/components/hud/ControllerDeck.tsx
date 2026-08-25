import React, { useState } from 'react';
import { Mic, MicOff, ChevronDown, Terminal, Send } from 'lucide-react';
import { SessionState } from '@/types';

interface ControllerDeckProps {
  state: SessionState;
  selectedVoice: string;
  onVoiceChange: (voice: string) => void;
  onToggleSession: () => void;
  onInjectText: (text: string) => void;
}

const VOICE_OPTIONS = [
  { id: 'aura-2-thalia-en', label: 'Thalia (Natural Companion)' },
  { id: 'aura-2-orion-en', label: 'Orion (Executive)' },
  { id: 'aura-2-arcas-en', label: 'Arcas (Deep Voice)' },
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
  const isConnected = state !== 'DISCONNECTED';

  const handleSend = () => {
    if (!inputText.trim()) return;
    onInjectText(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSend();
  };

  return (
    <div className="flex items-center gap-3 w-full shinra-pill rounded-xl p-2">
      {/* Physical Mic Button */}
      <button
        onClick={onToggleSession}
        className={`h-11 px-5 rounded-lg font-['Space_Grotesk'] text-[13px] font-bold tracking-wide flex items-center justify-center gap-2 transition-all duration-200 cursor-pointer flex-shrink-0 ${
          isConnected
            ? 'bg-red-600/90 text-white hover:bg-red-500 shadow-[0_0_20px_rgba(220,38,38,0.4)]'
            : 'bg-[#10B981] text-black hover:bg-[#34D399] shadow-[0_0_20px_rgba(16,185,129,0.35)]'
        }`}
      >
        {isConnected ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
        <span>{isConnected ? 'Disconnect' : 'Start Voice'}</span>
      </button>

      {/* Voice Model Selector */}
      <div className="relative flex items-center flex-shrink-0">
        <select
          value={selectedVoice}
          onChange={(e) => onVoiceChange(e.target.value)}
          className="bg-[#09090b] border border-white/10 rounded-lg py-2.5 pl-3 pr-8 text-zinc-300 font-['Space_Grotesk'] text-[12px] font-medium outline-none cursor-pointer appearance-none hover:border-white/20 focus:border-[#10B981] transition-all"
        >
          {VOICE_OPTIONS.map((v) => (
            <option key={v.id} value={v.id} className="bg-[#121215] text-white">
              {v.label}
            </option>
          ))}
        </select>
        <ChevronDown className="w-3.5 h-3.5 absolute right-2.5 text-zinc-400 pointer-events-none" />
      </div>

      {/* Inline Text Query Injection */}
      <div className="relative flex-1 flex items-center">
        <Terminal className="w-4 h-4 absolute left-3 text-zinc-500 pointer-events-none" />
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!isConnected}
          placeholder={isConnected ? 'Type query or instruction to SHINRA...' : 'Connect voice session to enable text queries...'}
          className="w-full bg-[#09090b] border border-white/10 rounded-lg py-2.5 pl-9 pr-3 text-white text-[13px] font-['Plus_Jakarta_Sans'] outline-none placeholder:text-zinc-600 focus:border-[#10B981] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        />
      </div>

      {/* Send Button */}
      <button
        onClick={handleSend}
        disabled={!isConnected || !inputText.trim()}
        className="h-10 px-4 rounded-lg bg-white/5 border border-white/10 text-white font-['Space_Grotesk'] text-[12px] font-semibold flex items-center gap-1.5 hover:bg-[#10B981]/15 hover:border-[#10B981] hover:text-[#10B981] transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
      >
        <span>Send</span>
        <Send className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};

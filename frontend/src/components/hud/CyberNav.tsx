import React from 'react';
import { Activity, Clock, MessageSquare } from 'lucide-react';
import { SessionState } from '@/types';

interface CyberNavProps {
  state: SessionState;
  latencyMs: number | null;
  turnsCount: number;
  onToggleTranscripts: () => void;
}

const STATE_CONFIG: Record<SessionState, { badge: string; dot: string; label: string }> = {
  DISCONNECTED: { badge: 'border-white/10 text-zinc-400', dot: 'bg-zinc-600', label: 'STANDBY' },
  CONNECTED: { badge: 'border-[#10B981]/40 text-[#10B981] bg-[#10B981]/10', dot: 'bg-[#10B981]', label: 'CONNECTED' },
  LISTENING: { badge: 'border-[#10B981] text-[#10B981] bg-[#10B981]/15', dot: 'bg-[#10B981]', label: 'LISTENING' },
  USER_SPEAKING: { badge: 'border-emerald-400 text-emerald-300 bg-emerald-950/40', dot: 'bg-emerald-400', label: 'USER SPEAKING' },
  THINKING: { badge: 'border-amber-400/50 text-amber-300 bg-amber-950/30', dot: 'bg-amber-400', label: 'THINKING' },
  SPEAKING: { badge: 'border-[#10B981] text-[#10B981] bg-[#10B981]/20', dot: 'bg-[#10B981]', label: 'SPEAKING' },
  ERROR: { badge: 'border-red-500/50 text-red-300 bg-red-950/30', dot: 'bg-red-500', label: 'ERROR' },
};

export const CyberNav: React.FC<CyberNavProps> = ({
  state,
  latencyMs,
  turnsCount,
  onToggleTranscripts,
}) => {
  const currentConfig = STATE_CONFIG[state] || STATE_CONFIG.DISCONNECTED;

  return (
    <header className="flex justify-between items-center px-6 py-3 shinra-pill rounded-xl">
      {/* Brand Title */}
      <div className="flex items-center gap-3">
        <div className="w-7 h-7 rounded-lg bg-[#10B981] flex items-center justify-center text-black font-['Syne'] font-extrabold text-[14px] shadow-[0_0_16px_rgba(16,185,129,0.4)]">
          S
        </div>
        <div className="flex flex-col">
          <span className="font-['Syne'] text-[15px] font-extrabold tracking-wider text-white flex items-center gap-2">
            SHINRA <span className="text-[10px] text-zinc-400 font-['JetBrains_Mono'] font-normal border border-white/10 px-1.5 py-0.5 rounded">VOICE MATRIX</span>
          </span>
        </div>
      </div>

      {/* Telemetry Chips */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 font-['JetBrains_Mono'] text-[11px] text-zinc-400 bg-[#09090b] px-3 py-1.5 rounded-lg border border-white/6">
          <Clock className="w-3 h-3 text-[#10B981]" />
          <span>LATENCY:</span>
          <span className="text-white font-semibold">{latencyMs !== null ? `${latencyMs} ms` : '-- ms'}</span>
        </div>

        <div className="flex items-center gap-2 font-['JetBrains_Mono'] text-[11px] text-zinc-400 bg-[#09090b] px-3 py-1.5 rounded-lg border border-white/6">
          <Activity className="w-3 h-3 text-[#10B981]" />
          <span>AUDIO:</span>
          <span className="text-white font-semibold">16kHz PCM</span>
        </div>

        <div className="flex items-center gap-2 font-['JetBrains_Mono'] text-[11px] text-zinc-400 bg-[#09090b] px-3 py-1.5 rounded-lg border border-white/6">
          <span>TURNS:</span>
          <span className="text-white font-semibold">{turnsCount}</span>
        </div>
      </div>

      {/* State Badge & Session Log Trigger */}
      <div className="flex items-center gap-3">
        <div className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-['JetBrains_Mono'] text-[11px] font-semibold tracking-wider uppercase border transition-all duration-300 ${currentConfig.badge}`}>
          <span className={`relative w-2 h-2 rounded-full ${currentConfig.dot}`} />
          <span>{currentConfig.label}</span>
        </div>

        <button
          onClick={onToggleTranscripts}
          title="Toggle Session History"
          className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 text-zinc-300 flex items-center justify-center hover:bg-white/15 hover:text-white transition-all cursor-pointer"
        >
          <MessageSquare className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};

import React from 'react';
import { Activity, Clock, MessageSquare, LayoutTemplate, Radio, Sparkles, Blocks } from 'lucide-react';
import { SessionState } from '@/types';
import { ShinraLogo } from '../layout/ShinraLogo';

export type NavViewMode = 'hero' | 'matrix' | 'connectors';

interface CyberNavProps {
  state: SessionState;
  latencyMs: number | null;
  turnsCount: number;
  viewMode: NavViewMode;
  findingsCount: number;
  connectorsCount?: number;
  onToggleView: (mode: NavViewMode) => void;
  onToggleTranscripts: () => void;
  onToggleIntelligence: () => void;
}

const STATE_CONFIG: Record<SessionState, { badge: string; dot: string; label: string }> = {
  DISCONNECTED: { badge: 'border-white/10 text-zinc-400', dot: 'bg-zinc-600', label: 'STANDBY' },
  CONNECTED: { badge: 'border-[#10B981]/40 text-[#10B981] bg-[#10B981]/10', dot: 'bg-[#10B981]', label: 'CONNECTED' },
  LISTENING: { badge: 'border-[#00F0FF] text-[#00F0FF] bg-[#00F0FF]/15', dot: 'bg-[#00F0FF]', label: 'LISTENING' },
  USER_SPEAKING: { badge: 'border-emerald-400 text-emerald-300 bg-emerald-950/40', dot: 'bg-emerald-400', label: 'USER SPEAKING' },
  THINKING: { badge: 'border-purple-400/50 text-purple-300 bg-purple-950/30', dot: 'bg-purple-400', label: 'THINKING' },
  SPEAKING: { badge: 'border-[#10B981] text-[#10B981] bg-[#10B981]/20', dot: 'bg-[#10B981]', label: 'SPEAKING' },
  MUTED: { badge: 'border-amber-500/50 text-amber-300 bg-amber-950/30', dot: 'bg-amber-500', label: 'MUTED' },
  ERROR: { badge: 'border-red-500/50 text-red-300 bg-red-950/30', dot: 'bg-red-500', label: 'ERROR' },
};

export const CyberNav: React.FC<CyberNavProps> = ({
  state,
  latencyMs,
  turnsCount,
  viewMode,
  findingsCount,
  connectorsCount = 0,
  onToggleView,
  onToggleTranscripts,
  onToggleIntelligence,
}) => {
  const currentConfig = STATE_CONFIG[state] || STATE_CONFIG.DISCONNECTED;

  return (
    <header className="w-full max-w-5xl mx-auto flex items-center justify-between px-3.5 py-1.5 shinra-pill rounded-2xl h-13 flex-shrink-0 z-30 shadow-[0_12px_36px_rgba(0,0,0,0.6)] border border-white/12">
      {/* 1. Brand Logo & Name */}
      <div className="flex items-center gap-2.5">
        <button
          onClick={() => onToggleView('hero')}
          className="flex items-center gap-2 cursor-pointer group bg-transparent border-0 p-0"
          title="Shinra Overview"
        >
          <ShinraLogo size={28} />
          <span className="font-['Syne'] text-[15px] font-extrabold tracking-wider text-white hidden sm:inline">
            SHINRA
          </span>
        </button>
      </div>

      {/* 2. Centered Navigation Tabs */}
      <nav className="flex items-center bg-[#070b14]/90 p-1 rounded-xl border border-white/10 shadow-inner">
        <button
          onClick={() => onToggleView('matrix')}
          className={`px-3 py-1.5 rounded-lg text-[11.5px] font-['Space_Grotesk'] font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
            viewMode === 'matrix'
              ? 'bg-[#10B981] text-zinc-950 shadow-[0_0_16px_rgba(16,185,129,0.35)]'
              : 'text-zinc-400 hover:text-white'
          }`}
        >
          <Radio className="w-3.5 h-3.5" />
          <span>Voice Matrix</span>
        </button>

        <button
          onClick={() => onToggleView('connectors')}
          className={`px-3 py-1.5 rounded-lg text-[11.5px] font-['Space_Grotesk'] font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
            viewMode === 'connectors'
              ? 'bg-[#10B981] text-zinc-950 shadow-[0_0_16px_rgba(16,185,129,0.35)]'
              : 'text-zinc-400 hover:text-white'
          }`}
        >
          <Blocks className="w-3.5 h-3.5" />
          <span>Connectors</span>
          {connectorsCount > 0 && (
            <span className={`w-4 h-4 rounded-full text-[9px] font-['JetBrains_Mono'] flex items-center justify-center font-bold ${
              viewMode === 'connectors' ? 'bg-zinc-950 text-[#10B981]' : 'bg-white/10 text-white'
            }`}>
              {connectorsCount}
            </span>
          )}
        </button>

        <button
          onClick={() => onToggleView('hero')}
          className={`px-3 py-1.5 rounded-lg text-[11.5px] font-['Space_Grotesk'] font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
            viewMode === 'hero'
              ? 'bg-[#10B981] text-zinc-950 shadow-[0_0_16px_rgba(16,185,129,0.35)]'
              : 'text-zinc-400 hover:text-white'
          }`}
        >
          <LayoutTemplate className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Overview</span>
        </button>
      </nav>

      {/* 3. Right Telemetry & Status Controls */}
      <div className="flex items-center gap-2">
        {/* Telemetry Indicator */}
        <div className="hidden lg:flex items-center gap-2 text-[10.5px] font-['JetBrains_Mono'] text-zinc-400">
          <div className="flex items-center gap-1 bg-[#070b14]/60 px-2 py-1 rounded-md border border-white/6">
            <Clock className="w-3 h-3 text-[#10B981]" />
            <span>{latencyMs !== null ? `${latencyMs}ms` : '<480ms'}</span>
          </div>
          <div className="flex items-center gap-1 bg-[#070b14]/60 px-2 py-1 rounded-md border border-white/6">
            <Activity className="w-3 h-3 text-[#00F0FF]" />
            <span>HD</span>
          </div>
          <div className="flex items-center gap-1 bg-[#070b14]/60 px-2 py-1 rounded-md border border-white/6">
            <span>#{turnsCount}</span>
          </div>
        </div>

        {/* Live Status Badge */}
        <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-['JetBrains_Mono'] text-[10px] font-bold tracking-wider uppercase border ${currentConfig.badge}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${currentConfig.dot}`} />
          <span>{currentConfig.label}</span>
        </div>

        {/* Tools & Findings Drawer Trigger */}
        <button
          onClick={onToggleIntelligence}
          title="Open Intelligence & Tools Hub"
          className="h-8 px-2.5 rounded-lg bg-white/5 border border-white/10 hover:border-[#00F0FF]/40 text-zinc-300 hover:text-white flex items-center gap-1.5 transition-all cursor-pointer text-[11px] font-['Space_Grotesk'] font-semibold"
        >
          <Sparkles className="w-3.5 h-3.5 text-[#00F0FF]" />
          <span className="hidden xl:inline">Hub</span>
          {findingsCount > 0 && (
            <span className="w-4 h-4 rounded-full bg-[#00F0FF]/20 text-[#00F0FF] text-[9px] font-['JetBrains_Mono'] flex items-center justify-center font-bold">
              {findingsCount}
            </span>
          )}
        </button>

        {/* Session Log Drawer Trigger */}
        <button
          onClick={onToggleTranscripts}
          title="Open Session Log"
          className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 hover:border-[#10B981]/40 text-zinc-300 hover:text-white flex items-center justify-center transition-all cursor-pointer"
        >
          <MessageSquare className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};


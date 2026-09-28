import React, { useState } from 'react';
import { 
  Mic, 
  ShieldCheck, 
  Blocks, 
  ArrowRight,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Calendar,
  Mail,
  Search,
  Database,
  Volume2
} from 'lucide-react';
import { FluidWaveformCanvas } from '../visualizer/FluidWaveformCanvas';
import { useAuth } from '@/context/AuthContext';

interface GatewayHeroPageProps {
  onEnterStudio: () => void;
  onOpenConnectors: () => void;
  onOpenSkills: () => void;
}

const FLOATING_PROMPTS = [
  {
    icon: Calendar,
    text: "What's on my schedule today?",
    pillClass: "animate-float-slow top-0 -left-6 sm:-left-16",
    tag: "Calendar",
  },
  {
    icon: Mail,
    text: "Summarize unread priority emails",
    pillClass: "animate-float-reverse top-4 -right-6 sm:-right-16",
    tag: "Gmail",
  },
  {
    icon: Search,
    text: "Search latest AI breakthroughs with Tavily",
    pillClass: "animate-float-reverse -bottom-4 -left-4 sm:-left-12",
    tag: "Research",
  },
  {
    icon: Database,
    text: "Inspect PostgreSQL database tables",
    pillClass: "animate-float-slow -bottom-2 -right-4 sm:-right-12",
    tag: "Database",
  },
];

export const GatewayHeroPage: React.FC<GatewayHeroPageProps> = ({
  onEnterStudio,
  onOpenConnectors,
  onOpenSkills,
}) => {
  const [showTechDetails, setShowTechDetails] = useState(false);
  const [isOrbHovered, setIsOrbHovered] = useState(false);
  const { isAuthenticated, openLoginModal } = useAuth();

  const handleStart = () => {
    if (!isAuthenticated) {
      openLoginModal();
      return;
    }
    onEnterStudio();
  };

  return (
    <div className="w-full min-h-full flex flex-col items-center justify-between px-4 sm:px-6 lg:px-8 py-8 sm:py-12 pb-28">
      
      {/* 1. Main Direct Voice Entry Hero */}
      <div className="w-full max-w-3xl mx-auto flex flex-col items-center text-center my-auto py-2 sm:py-6">
        
        {/* Animated Live Status Pill */}
        <div className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-[var(--color-surface)] border border-[var(--color-hairline)] shadow-xs mb-6 hover:border-[var(--color-muted)] transition-all">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--color-success)] opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[var(--color-success)]" />
          </span>
          <span className="text-[12px] font-medium text-[var(--color-body)] flex items-center gap-1.5">
            <span>Conversational Agent Ready</span>
            <span className="text-[var(--color-muted)]">·</span>
            <span className="font-mono text-[11px] text-[var(--color-muted)]">Deepgram duplex 16kHz</span>
          </span>
          {/* Mini fluctuating equalizer */}
          <div className="flex items-center gap-0.5 h-3 pl-1 border-l border-[var(--color-hairline)]" aria-hidden="true">
            <span className="w-0.5 bg-[var(--color-action)] rounded-full eq-active-1 inline-block" />
            <span className="w-0.5 bg-[var(--color-action)] rounded-full eq-active-2 inline-block" />
            <span className="w-0.5 bg-[var(--color-action)] rounded-full eq-active-3 inline-block" />
            <span className="w-0.5 bg-[var(--color-action)] rounded-full eq-active-4 inline-block" />
          </div>
        </div>

        {/* Dynamic & Engaging Headline */}
        <h1 className="font-['DM_Serif_Display'] text-4xl sm:text-6xl lg:text-7xl text-[var(--color-ink)] leading-[1.08] tracking-tight mb-4">
          Speak naturally. <br className="hidden sm:inline" />
          <span className="italic text-[var(--color-action)] font-normal">Take action</span> instantly.
        </h1>

        {/* Descriptive Subtitle */}
        <p className="text-[16px] sm:text-[19px] text-[var(--color-body)] max-w-2xl mx-auto leading-relaxed mb-10 font-normal font-sans">
          Duplex voice assistant connected to your workspace tools, email, calendar, and codebase. Speak commands naturally — actions that modify data always ask for verbal confirmation.
        </p>

        {/* 2. Living Acoustic Voice Orb Centerpiece */}
        <div className="relative w-full max-w-lg mx-auto flex items-center justify-center my-6 sm:my-8">
          
          {/* Floating Suggestion Capsules surrounding the Voice Core */}
          <div className="absolute inset-0 pointer-events-none hidden md:block">
            {FLOATING_PROMPTS.map((prompt, idx) => {
              const Icon = prompt.icon;
              return (
                <div
                  key={idx}
                  onClick={handleStart}
                  className={`absolute pointer-events-auto cursor-pointer p-2 sm:px-3 sm:py-1.5 rounded-full bg-[var(--color-surface)] border border-[var(--color-hairline)] shadow-sm hover:shadow-md hover:border-[var(--color-action)] hover:scale-105 transition-all flex items-center gap-2 group ${prompt.pillClass}`}
                  title={`Try saying: "${prompt.text}"`}
                >
                  <div className="w-5 h-5 rounded-full bg-[var(--color-surface-muted)] flex items-center justify-center text-[var(--color-action)] shrink-0">
                    <Icon className="w-3 h-3" />
                  </div>
                  <span className="text-[11.5px] font-medium text-[var(--color-body)] group-hover:text-[var(--color-ink)] truncate max-w-[170px] sm:max-w-[210px]">
                    "{prompt.text}"
                  </span>
                </div>
              );
            })}
          </div>

          {/* Central Pulsating Voice Sphere Container */}
          <div 
            onClick={handleStart}
            onMouseEnter={() => setIsOrbHovered(true)}
            onMouseLeave={() => setIsOrbHovered(false)}
            className="relative flex items-center justify-center p-8 sm:p-12 cursor-pointer group"
            role="button"
            tabIndex={0}
            title="Click to start voice session"
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleStart();
              }
            }}
          >
            {/* Concentric Expanding Acoustic Resonance Rings */}
            <div className="absolute w-44 h-44 sm:w-56 sm:h-56 rounded-full border border-[var(--color-action)]/25 animate-ring-expand pointer-events-none" />
            <div className="absolute w-56 h-56 sm:w-72 sm:h-72 rounded-full border border-[var(--color-action)]/15 animate-ring-expand-delayed pointer-events-none" />
            <div className="absolute w-68 h-68 sm:w-88 sm:h-88 rounded-full border border-[var(--color-action)]/10 animate-ring-expand pointer-events-none" />

            {/* Glowing Orb Sphere */}
            <div className={`relative w-28 h-28 sm:w-36 sm:h-36 rounded-full bg-gradient-to-tr from-[#974631] via-[#b95740] to-[#e07153] flex flex-col items-center justify-center text-white shadow-xl transition-all duration-300 group-hover:scale-105 ${isOrbHovered ? 'shadow-[0_0_50px_rgba(185,87,64,0.5)]' : 'shadow-[0_0_35px_rgba(185,87,64,0.3)] animate-acoustic-pulse'}`}>
              
              {/* Internal subtle shimmering sheen */}
              <div className="absolute inset-1 rounded-full bg-gradient-to-b from-white/20 to-transparent pointer-events-none" />

              {/* Dynamic Center Icon & Soundwave */}
              <div className="relative flex flex-col items-center justify-center gap-1 z-10">
                <Mic className="w-8 h-8 sm:w-10 sm:h-10 text-white transition-transform duration-200 group-hover:scale-110" />
                
                {/* Micro Equalizer Frequency Bars */}
                <div className="flex items-center gap-1 h-4 mt-0.5" aria-hidden="true">
                  <span className="w-1 bg-white/90 rounded-full eq-active-1 inline-block" />
                  <span className="w-1 bg-white/90 rounded-full eq-active-3 inline-block" />
                  <span className="w-1 bg-white/90 rounded-full eq-active-5 inline-block" />
                  <span className="w-1 bg-white/90 rounded-full eq-active-2 inline-block" />
                  <span className="w-1 bg-white/90 rounded-full eq-active-4 inline-block" />
                </div>
              </div>

            </div>

          </div>

        </div>

        {/* Live Audio Stream Canvas Preview */}
        <div 
          onClick={handleStart}
          className="w-full max-w-md h-16 sm:h-20 mb-6 rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] p-2 flex flex-col items-center justify-center cursor-pointer hover:border-[var(--color-action)] transition-colors shadow-xs group"
          title="Click to start voice session"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              handleStart();
            }
          }}
        >
          <div className="w-full h-10">
            <FluidWaveformCanvas state="CONNECTED" audioRMS={0.12} />
          </div>
          <span className="text-[11px] font-mono text-[var(--color-muted)] group-hover:text-[var(--color-action)] transition-colors flex items-center gap-1.5">
            <Volume2 className="w-3 h-3" />
            <span>Interactive waveform active · Click to speak</span>
          </span>
        </div>

        {/* Primary CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <button
            onClick={handleStart}
            type="button"
            className="min-h-[48px] px-8 py-3 rounded-lg bg-[var(--color-action)] hover:bg-[var(--color-action-active)] text-white text-[15px] font-medium flex items-center justify-center gap-2.5 shadow-md hover:shadow-lg cursor-pointer focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-[var(--color-focus)] transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <Mic className="w-5 h-5 animate-pulse" />
            <span>{isAuthenticated ? 'Start voice session' : 'Sign in to start'}</span>
          </button>

          <button
            onClick={onOpenConnectors}
            type="button"
            className="min-h-[48px] px-6 py-3 rounded-lg border border-[var(--color-hairline)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-muted)] text-[14px] text-[var(--color-ink)] font-medium flex items-center justify-center gap-2 shadow-xs cursor-pointer transition-colors"
          >
            <Blocks className="w-4 h-4 text-[var(--color-muted)]" />
            <span>View 17 integrations</span>
          </button>
        </div>

      </div>

      {/* 3. Capability Showcase Bands with Smooth Hover Motion */}
      <div className="w-full max-w-4xl mx-auto grid grid-cols-1 sm:grid-cols-3 gap-3.5 pt-8 pb-4 border-t border-[var(--color-hairline)]">
        
        {/* Capability 1 */}
        <div className="p-4 rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] hover:border-[var(--color-muted)] hover:-translate-y-0.5 transition-all shadow-xs flex flex-col justify-between group">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="w-8 h-8 rounded-lg bg-[#eef4f8] text-[var(--color-link)] flex items-center justify-center">
                <Blocks className="w-4 h-4" />
              </div>
              <span className="text-[10.5px] font-mono text-[var(--color-muted)] uppercase tracking-wider bg-[var(--color-surface-muted)] px-2 py-0.5 rounded">
                17 Services
              </span>
            </div>
            <div className="text-[14px] font-semibold text-[var(--color-ink)] mb-1">
              Connected Workspace
            </div>
            <p className="text-[12.5px] text-[var(--color-body)] leading-relaxed">
              Read and inspect email, calendars, Postgres databases, and repositories directly via voice.
            </p>
          </div>
          <button
            onClick={onOpenConnectors}
            className="mt-4 text-[12px] font-medium text-[var(--color-link)] group-hover:underline flex items-center gap-1.5 text-left cursor-pointer"
          >
            <span>Manage integrations</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </div>

        {/* Capability 2 */}
        <div className="p-4 rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] hover:border-[var(--color-muted)] hover:-translate-y-0.5 transition-all shadow-xs flex flex-col justify-between group">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="w-8 h-8 rounded-lg bg-[#eef6f0] text-[var(--color-success)] flex items-center justify-center">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <span className="text-[10.5px] font-mono text-[var(--color-success)] uppercase tracking-wider bg-[#eef6f0] px-2 py-0.5 rounded">
                Guaranteed Safe
              </span>
            </div>
            <div className="text-[14px] font-semibold text-[var(--color-ink)] mb-1">
              Confirmation First
            </div>
            <p className="text-[12.5px] text-[var(--color-body)] leading-relaxed">
              Mutating actions like sending emails or booking appointments require explicit verbal approval.
            </p>
          </div>
          <button
            onClick={onOpenSkills}
            className="mt-4 text-[12px] font-medium text-[var(--color-link)] group-hover:underline flex items-center gap-1.5 text-left cursor-pointer"
          >
            <span>Review skills & security</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </div>

        {/* Capability 3 */}
        <div className="p-4 rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] hover:border-[var(--color-muted)] hover:-translate-y-0.5 transition-all shadow-xs flex flex-col justify-between group">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="w-8 h-8 rounded-lg bg-[#fcf1ee] text-[var(--color-action)] flex items-center justify-center">
                <Sparkles className="w-4 h-4" />
              </div>
              <span className="text-[10.5px] font-mono text-[var(--color-action)] uppercase tracking-wider bg-[#fcf1ee] px-2 py-0.5 rounded">
                Low Latency
              </span>
            </div>
            <div className="text-[14px] font-semibold text-[var(--color-ink)] mb-1">
              Live Duplex Streaming
            </div>
            <p className="text-[12.5px] text-[var(--color-body)] leading-relaxed">
              Real-time WebRTC/WebSocket audio pipeline with natural barge-in and human conversational cadence.
            </p>
          </div>
          <button
            onClick={() => setShowTechDetails((prev) => !prev)}
            className="mt-4 text-[12px] font-medium text-[var(--color-link)] group-hover:underline flex items-center gap-1.5 text-left cursor-pointer"
          >
            <span>{showTechDetails ? 'Hide technical details' : 'Architecture details'}</span>
            {showTechDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

      </div>

      {/* 4. Optional Technical Architecture Disclosure */}
      {showTechDetails && (
        <div className="w-full max-w-4xl mx-auto mt-3 p-4 rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] text-left animate-in fade-in duration-200">
          <div className="text-[13px] font-semibold text-[var(--color-ink)] mb-2 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[var(--color-action)]" />
            <span>System architecture & audio pipeline</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-[12px]">
            <div className="p-3 rounded-lg bg-[var(--color-surface-muted)]/50 border border-[var(--color-hairline)]">
              <div className="text-[11px] font-mono text-[var(--color-muted)] uppercase">Speech input</div>
              <div className="font-semibold text-[var(--color-ink)] mt-0.5">16kHz PCM duplex streaming</div>
              <div className="text-[11px] text-[var(--color-body)] mt-1">Direct microphone stream over WebSocket</div>
            </div>
            <div className="p-3 rounded-lg bg-[var(--color-surface-muted)]/50 border border-[var(--color-hairline)]">
              <div className="text-[11px] font-mono text-[var(--color-muted)] uppercase">Voice synthesis</div>
              <div className="font-semibold text-[var(--color-ink)] mt-0.5">Deepgram Aura 2</div>
              <div className="text-[11px] text-[var(--color-body)] mt-1">Sub-second conversational voice response</div>
            </div>
            <div className="p-3 rounded-lg bg-[var(--color-surface-muted)]/50 border border-[var(--color-hairline)]">
              <div className="text-[11px] font-mono text-[var(--color-muted)] uppercase">Agent engine</div>
              <div className="font-semibold text-[var(--color-ink)] mt-0.5">LangGraph & Groq</div>
              <div className="text-[11px] text-[var(--color-body)] mt-1">Multi-tool state machine with memory</div>
            </div>
            <div className="p-3 rounded-lg bg-[var(--color-surface-muted)]/50 border border-[var(--color-hairline)]">
              <div className="text-[11px] font-mono text-[var(--color-muted)] uppercase">Security boundary</div>
              <div className="font-semibold text-[var(--color-ink)] mt-0.5">Verbal approval gate</div>
              <div className="text-[11px] text-[var(--color-body)] mt-1">Explicit confirmation before writes</div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default GatewayHeroPage;

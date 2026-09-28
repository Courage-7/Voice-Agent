import React from 'react';
import { ArrowRight, Zap, ShieldCheck, Cpu, Mic, Layers, Activity, Volume2, Play } from 'lucide-react';
import { ShinraLogo } from '../layout/ShinraLogo';

interface HeroSectionProps {
  onEnterMatrix: () => void;
  onStartDirectVoice?: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onEnterMatrix, onStartDirectVoice }) => {
  return (
    <div className="relative w-full h-full flex flex-col justify-between p-4 sm:p-6 lg:p-8 overflow-hidden aurora-bg select-none">
      {/* 1. Atmospheric Ambient Glow Lights */}
      <div className="absolute -top-24 left-1/4 w-[550px] h-[350px] bg-gradient-to-br from-[#10B981]/20 to-[#00F0FF]/15 rounded-full blur-[130px] pointer-events-none animate-aurora" />
      <div className="absolute top-1/2 -right-24 w-[500px] h-[350px] bg-gradient-to-bl from-[#8B5CF6]/15 to-[#00F0FF]/12 rounded-full blur-[140px] pointer-events-none animate-aurora" />

      {/* 2. Top Header Brand Bar */}
      <header className="w-full max-w-5xl mx-auto flex justify-between items-center z-10">
        <div className="flex items-center gap-2.5">
          <ShinraLogo size={32} />
          <div className="flex items-center gap-2">
            <span className="font-['Syne'] text-[18px] font-extrabold tracking-wider text-white">
              SHINRA
            </span>
            <span className="px-2 py-0.5 rounded-full bg-[#10B981]/15 border border-[#10B981]/30 font-['JetBrains_Mono'] text-[9.5px] text-[#34D399] font-bold">
              v2.0 LPU
            </span>
          </div>
        </div>

        {/* Live System Beacon */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 backdrop-blur-md">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#10B981] opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#10B981]" />
          </span>
          <span className="font-['JetBrains_Mono'] text-[10px] text-zinc-300 font-medium">
            STREAMING READY · &lt; 480MS TTFA
          </span>
        </div>
      </header>

      {/* 3. Main Center Hero Presentation */}
      <div className="w-full max-w-4xl mx-auto flex flex-col items-center text-center my-auto py-3 z-10">
        {/* Animated Badge Pill */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-gradient-to-r from-[#10B981]/15 via-[#00F0FF]/15 to-[#8B5CF6]/15 border border-white/12 mb-3 backdrop-blur-xl shadow-lg">
          <Zap className="w-3.5 h-3.5 text-[#00F0FF]" />
          <span className="font-['Space_Grotesk'] text-[11px] font-bold text-transparent bg-clip-text bg-gradient-to-r from-white via-zinc-200 to-zinc-400 tracking-wider uppercase">
            Full-Duplex Conversational Intelligence
          </span>
        </div>

        {/* Hero Title */}
        <h1 className="font-['Syne'] text-[34px] sm:text-[46px] lg:text-[54px] font-extrabold tracking-tight text-white leading-[1.08] mb-3">
          Voice Intelligence.{' '}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00F0FF] via-[#10B981] to-[#A855F7] drop-shadow-[0_0_35px_rgba(16,185,129,0.4)]">
            At the Speed of Thought.
          </span>
        </h1>

        {/* Subtitle */}
        <p className="font-['Plus_Jakarta_Sans'] text-[14px] sm:text-[16px] text-zinc-300 max-w-2xl leading-relaxed mb-5 font-normal">
          Talk naturally with zero awkward pauses. Shinra combines Deepgram full-duplex speech, Groq LPU reasoning, and 17 live workspace tools in a focused, clutter-free voice interface.
        </p>

        {/* Animated Wave Equalizer Strip */}
        <div className="flex items-center gap-1.5 mb-5 h-7 px-3.5 py-1 rounded-full bg-white/5 border border-white/10 backdrop-blur-lg">
          <Volume2 className="w-3.5 h-3.5 text-[#10B981] mr-1.5" />
          <span className="w-1 bg-[#10B981] rounded-full eq-bar-1" />
          <span className="w-1 bg-[#00F0FF] rounded-full eq-bar-2" />
          <span className="w-1 bg-[#34D399] rounded-full eq-bar-3" />
          <span className="w-1 bg-[#8B5CF6] rounded-full eq-bar-4" />
          <span className="w-1 bg-[#10B981] rounded-full eq-bar-5" />
          <span className="w-1 bg-[#00F0FF] rounded-full eq-bar-2" />
          <span className="w-1 bg-[#34D399] rounded-full eq-bar-1" />
          <span className="font-['JetBrains_Mono'] text-[10.5px] text-zinc-300 ml-2.5 font-medium">
            24kHz Neural Audio Active
          </span>
        </div>

        {/* Primary Call to Action Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={onEnterMatrix}
            className="group px-7 py-3 rounded-xl bg-gradient-to-r from-[#10B981] via-[#059669] to-[#047857] hover:from-[#34D399] hover:to-[#10B981] text-zinc-950 font-['Space_Grotesk'] text-[14px] font-extrabold tracking-wide flex items-center gap-2.5 transition-all duration-300 shadow-[0_0_30px_rgba(16,185,129,0.45)] hover:scale-[1.02] cursor-pointer"
          >
            <Mic className="w-4 h-4 text-zinc-950" />
            <span>Launch Voice Matrix</span>
            <ArrowRight className="w-3.5 h-3.5 transition-transform duration-300 group-hover:translate-x-1" />
          </button>

          {onStartDirectVoice && (
            <button
              onClick={onStartDirectVoice}
              className="px-5 py-3 rounded-xl bg-white/8 hover:bg-white/14 border border-white/12 text-white font-['Space_Grotesk'] text-[13px] font-bold flex items-center gap-2 transition-all backdrop-blur-xl hover:border-[#10B981]/50 cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 text-[#10B981]" />
              <span>Start Speaking Now</span>
            </button>
          )}
        </div>
      </div>

      {/* 4. Compact Glassmorphic Capability Pillars */}
      <div className="w-full max-w-5xl mx-auto grid grid-cols-2 lg:grid-cols-4 gap-3 z-10">
        {/* Card 1: Sub-500ms TTFA */}
        <div className="shinra-card rounded-xl p-3 flex flex-col gap-1.5 hover:border-[#10B981]/50 transition-all">
          <div className="flex items-center justify-between">
            <div className="w-6 h-6 rounded-lg bg-[#10B981]/15 flex items-center justify-center text-[#10B981]">
              <Activity className="w-3.5 h-3.5" />
            </div>
            <span className="font-['JetBrains_Mono'] text-[9px] text-zinc-400 font-bold uppercase">
              Latency
            </span>
          </div>
          <div className="font-['Space_Grotesk'] text-[16px] font-bold text-white tracking-tight">
            &lt; 480ms TTFA
          </div>
          <p className="font-['Plus_Jakarta_Sans'] text-[11px] text-zinc-400 leading-snug">
            Acoustic VAD with instant barge-in interruption.
          </p>
        </div>

        {/* Card 2: Groq LPU Reasoning */}
        <div className="shinra-card rounded-xl p-3 flex flex-col gap-1.5 hover:border-[#00F0FF]/50 transition-all">
          <div className="flex items-center justify-between">
            <div className="w-6 h-6 rounded-lg bg-[#00F0FF]/15 flex items-center justify-center text-[#00F0FF]">
              <Cpu className="w-3.5 h-3.5" />
            </div>
            <span className="font-['JetBrains_Mono'] text-[9px] text-zinc-400 font-bold uppercase">
              Reasoning
            </span>
          </div>
          <div className="font-['Space_Grotesk'] text-[16px] font-bold text-white tracking-tight">
            Groq LPU Engine
          </div>
          <p className="font-['Plus_Jakarta_Sans'] text-[11px] text-zinc-400 leading-snug">
            Fast LLM reasoning with real-time audio synthesis.
          </p>
        </div>

        {/* Card 3: 17 Connected Tools */}
        <div className="shinra-card rounded-xl p-3 flex flex-col gap-1.5 hover:border-[#8B5CF6]/50 transition-all">
          <div className="flex items-center justify-between">
            <div className="w-6 h-6 rounded-lg bg-[#8B5CF6]/15 flex items-center justify-center text-[#8B5CF6]">
              <Layers className="w-3.5 h-3.5" />
            </div>
            <span className="font-['JetBrains_Mono'] text-[9px] text-zinc-400 font-bold uppercase">
              Tools
            </span>
          </div>
          <div className="font-['Space_Grotesk'] text-[16px] font-bold text-white tracking-tight">
            17 Workspace Tools
          </div>
          <p className="font-['Plus_Jakarta_Sans'] text-[11px] text-zinc-400 leading-snug">
            Gmail, Calendar, Sheets, Docs, and deep research.
          </p>
        </div>

        {/* Card 4: Verbal Safety Policy */}
        <div className="shinra-card rounded-xl p-3 flex flex-col gap-1.5 hover:border-[#F59E0B]/50 transition-all">
          <div className="flex items-center justify-between">
            <div className="w-6 h-6 rounded-lg bg-[#F59E0B]/15 flex items-center justify-center text-[#F59E0B]">
              <ShieldCheck className="w-3.5 h-3.5" />
            </div>
            <span className="font-['JetBrains_Mono'] text-[9px] text-zinc-400 font-bold uppercase">
              Safety
            </span>
          </div>
          <div className="font-['Space_Grotesk'] text-[16px] font-bold text-white tracking-tight">
            Verbal Verification
          </div>
          <p className="font-['Plus_Jakarta_Sans'] text-[11px] text-zinc-400 leading-snug">
            Explicit confirmation before mutating workspace data.
          </p>
        </div>
      </div>
    </div>
  );
};

import React, { useState, useRef, useEffect } from 'react';
import { 
  Mic, 
  MicOff, 
  ChevronDown, 
  Send, 
  Wrench, 
  CheckCircle2, 
  FileText, 
  Activity, 
  ArrowRight 
} from 'lucide-react';
import { FluidWaveformCanvas } from '../visualizer/FluidWaveformCanvas';
import { Message } from '../chat';
import { SessionState, ToolTrace, TranscriptEntry, FindingItem } from '@/types';

export interface VoiceStudioPageProps {
  state: SessionState;
  audioRMS: number;
  subtitle: string;
  selectedVoice: string;
  activeTool: ToolTrace | null;
  transcriptCount: number;
  activityCount: number;
  transcripts?: TranscriptEntry[];
  findings?: FindingItem[];
  recentTools?: ToolTrace[];
  noiseProfile?: 'balanced' | 'noisy' | 'quiet';
  isMicMuted?: boolean;
  onNoiseProfileChange?: (profile: 'balanced' | 'noisy' | 'quiet') => void;
  onToggleMicMute?: () => void;
  onVoiceChange: (voice: string) => void;
  onToggleSession: () => void;
  onInjectText: (text: string) => void;
  onOpenTranscripts: () => void;
  onOpenActivity: () => void;
  onClearTranscripts?: () => void;
}

const VOICE_OPTIONS = [
  { id: 'aura-2-thalia-en', label: 'Thalia (Natural & Empathetic)' },
  { id: 'aura-2-orion-en', label: 'Orion (Executive & Crisp)' },
  { id: 'aura-2-arcas-en', label: 'Arcas (Deep & Authoritative)' },
  { id: 'aura-2-perseus-en', label: 'Perseus (Dynamic & Engaging)' },
  { id: 'aura-2-zeus-en', label: 'Zeus (Resonant & Calm)' },
  { id: 'aura-asteria-en', label: 'Asteria (Classic Studio)' },
];

const STATE_CONFIG: Record<SessionState, { text: string; dot: string; labelColor: string; surfaceBorder: string }> = {
  DISCONNECTED: { 
    text: 'Ready', 
    dot: 'bg-[var(--color-muted)]', 
    labelColor: 'text-[var(--color-muted)]',
    surfaceBorder: 'border-[var(--color-hairline)]'
  },
  CONNECTED: { 
    text: 'Connected', 
    dot: 'bg-[var(--color-success)]', 
    labelColor: 'text-[var(--color-success)]',
    surfaceBorder: 'border-[var(--color-success)]/30'
  },
  LISTENING: { 
    text: 'Listening', 
    dot: 'bg-[var(--color-action)] animate-pulse', 
    labelColor: 'text-[var(--color-action)]',
    surfaceBorder: 'border-[var(--color-action)]/30'
  },
  USER_SPEAKING: { 
    text: 'You are speaking', 
    dot: 'bg-[var(--color-action)] animate-pulse', 
    labelColor: 'text-[var(--color-action)]',
    surfaceBorder: 'border-[var(--color-action)]/40'
  },
  THINKING: { 
    text: 'Thinking', 
    dot: 'bg-[var(--color-warning)] animate-pulse', 
    labelColor: 'text-[var(--color-warning)]',
    surfaceBorder: 'border-[var(--color-warning)]/30'
  },
  SPEAKING: { 
    text: 'Assistant speaking', 
    dot: 'bg-[var(--color-link)] animate-pulse', 
    labelColor: 'text-[var(--color-link)]',
    surfaceBorder: 'border-[var(--color-link)]/30'
  },
  MUTED: { 
    text: 'Muted', 
    dot: 'bg-amber-500', 
    labelColor: 'text-amber-700',
    surfaceBorder: 'border-amber-500/30'
  },
  ERROR: { 
    text: 'Offline', 
    dot: 'bg-[var(--color-danger)]', 
    labelColor: 'text-[var(--color-danger)]',
    surfaceBorder: 'border-[var(--color-danger)]/30'
  },
};

export const VoiceStudioPage: React.FC<VoiceStudioPageProps> = ({
  state,
  audioRMS,
  subtitle,
  selectedVoice,
  activeTool,
  transcriptCount,
  activityCount,
  transcripts = [],
  findings = [],
  recentTools: _recentTools = [],
  noiseProfile = 'balanced',
  isMicMuted = false,
  onNoiseProfileChange,
  onToggleMicMute,
  onVoiceChange,
  onToggleSession,
  onInjectText,
  onOpenTranscripts,
  onOpenActivity,
}) => {
  const [inputText, setInputText] = useState('');
  const transcriptScrollRef = useRef<HTMLDivElement | null>(null);
  const isConnected = state !== 'DISCONNECTED';
  const isUserSpeaking = state === 'USER_SPEAKING';
  const isAgentSpeaking = state === 'SPEAKING';
  const isThinking = state === 'THINKING';
  const isMuted = state === 'MUTED' || isMicMuted;

  // Single source of truth for status display: if muted, always render MUTED state
  const effectiveState: SessionState = isMuted && isConnected && state !== 'SPEAKING' ? 'MUTED' : state;
  const currentStatus = STATE_CONFIG[effectiveState] || STATE_CONFIG.DISCONNECTED;

  useEffect(() => {
    if (transcriptScrollRef.current) {
      transcriptScrollRef.current.scrollTop = transcriptScrollRef.current.scrollHeight;
    }
  }, [transcripts, subtitle]);

  const handleSend = () => {
    if (!inputText.trim()) return;
    onInjectText(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  };

  const latestFinding = findings.length > 0 ? findings[0] : null;
  // A mute card communicates microphone state, not the current assistant turn.
  // Keeping this separate prevents an in-flight assistant response appearing
  // under the "Mic Muted" label.
  const liveDialogue = isMicMuted
    ? 'Microphone is muted. Click "Muted" above to speak.'
    : subtitle || (isConnected
      ? 'Listening... Speak naturally or enter text below.'
      : 'Assistant is ready. Click "Start voice" to begin.');

  return (
    <div className="w-full max-w-[1200px] mx-auto h-full flex flex-col px-4 sm:px-6 lg:px-8 py-4 overflow-hidden">
      
      {/* 1. Page Header & Session State Summary */}
      <div className="flex items-center justify-between gap-4 pb-3 border-b border-[var(--color-hairline)] shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="font-['DM_Serif_Display'] text-2xl sm:text-3xl text-[var(--color-ink)] leading-none">
            Voice workspace
          </h1>
          <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-[var(--color-surface-muted)] text-[12px] font-medium text-[var(--color-body)] border border-[var(--color-hairline)]">
            <span className={`w-2 h-2 rounded-full ${currentStatus.dot}`} aria-hidden="true" />
            <span>{currentStatus.text}</span>
          </div>
        </div>

        {/* Voice Selection & Secondary Actions */}
        <div className="flex items-center gap-2">
          <div className="relative flex items-center">
            <label htmlFor="voice-select" className="sr-only">Select voice</label>
            <select
              id="voice-select"
              value={selectedVoice}
              onChange={(e) => onVoiceChange(e.target.value)}
              className="h-9 bg-[var(--color-surface)] border border-[var(--color-hairline)] rounded-md py-1.5 pl-3 pr-8 text-[12px] text-[var(--color-body)] font-medium outline-none cursor-pointer appearance-none hover:border-[var(--color-muted)] focus:border-[var(--color-focus)] focus:ring-1 focus:ring-[var(--color-focus)] transition-colors"
            >
              {VOICE_OPTIONS.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 absolute right-2.5 text-[var(--color-muted)] pointer-events-none" />
          </div>

          <button
            type="button"
            onClick={onOpenTranscripts}
            className="hidden sm:flex items-center gap-1.5 h-9 px-3 rounded-md border border-[var(--color-hairline)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-muted)] text-[12px] text-[var(--color-body)] font-medium transition-colors cursor-pointer"
            title="Open complete transcripts log"
          >
            <FileText className="w-3.5 h-3.5 text-[var(--color-muted)]" />
            <span>Transcripts</span>
            {transcriptCount > 0 && (
              <span className="font-mono text-[11px] text-[var(--color-muted)]">({transcriptCount})</span>
            )}
          </button>

          <button
            type="button"
            onClick={onOpenActivity}
            className="hidden sm:flex items-center gap-1.5 h-9 px-3 rounded-md border border-[var(--color-hairline)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-muted)] text-[12px] text-[var(--color-body)] font-medium transition-colors cursor-pointer"
            title="Open tool activity drawer"
          >
            <Activity className="w-3.5 h-3.5 text-[var(--color-muted)]" />
            <span>Activity</span>
            {activityCount > 0 && (
              <span className="font-mono text-[11px] text-[var(--color-muted)]">({activityCount})</span>
            )}
          </button>
        </div>
      </div>

      {/* 2. Main Two-Column Operations Layout: Left = Audio Console & Input, Right = Live Transcript & Results */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 py-3 min-h-0 overflow-hidden">
        
        {/* Left Column (5 cols on lg): High-Contrast Audio Console & Primary Session Control */}
        <div className="lg:col-span-5 flex flex-col gap-3 min-h-0">
          
          {/* Active Voice Console Card */}
          <div className="relative rounded-2xl bg-[var(--color-surface)] border border-[var(--color-hairline)] p-5 sm:p-6 flex flex-col items-center justify-between text-center overflow-hidden shrink-0 shadow-sm transition-all hover:border-[var(--color-muted)]/50">
            
            {/* Top State Indicator inside console */}
            <div className="w-full flex items-center justify-between pb-3 border-b border-[var(--color-hairline)] gap-2 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[var(--color-action)]" />
                <span className="text-[12px] font-mono font-bold uppercase tracking-wider text-[var(--color-ink)]">
                  Live Voice Console
                </span>
              </div>
              <div className="flex items-center gap-2">
                {onNoiseProfileChange && (
                  <div className="relative flex items-center">
                    <label htmlFor="noise-profile-select" className="sr-only">Noise Profile</label>
                    <select
                      id="noise-profile-select"
                      value={noiseProfile || 'balanced'}
                      onChange={(e) => onNoiseProfileChange(e.target.value as 'balanced' | 'noisy' | 'quiet')}
                      className="h-7 bg-[var(--color-surface-muted)] border border-[var(--color-hairline)] rounded-md px-2 pr-6 text-[11px] text-[var(--color-body)] font-medium outline-none cursor-pointer appearance-none hover:border-[var(--color-muted)] transition-colors"
                      title="Adjust noise rejection sensitivity for your environment"
                    >
                      <option value="balanced">Filter: Balanced</option>
                      <option value="noisy">Filter: High (Noisy Room)</option>
                      <option value="quiet">Filter: Low (Quiet Studio)</option>
                    </select>
                    <ChevronDown className="w-3 h-3 absolute right-1.5 text-[var(--color-muted)] pointer-events-none" />
                  </div>
                )}
                <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[var(--color-surface-muted)] text-[11px] font-medium text-[var(--color-body)] border border-[var(--color-hairline)]">
                  <span className={`w-1.5 h-1.5 rounded-full ${currentStatus.dot}`} />
                  <span>{currentStatus.text}</span>
                </div>
              </div>
            </div>

            {/* Restrained Waveform Level Meter */}
            <div className="w-full py-2 my-2 rounded-xl bg-[var(--color-surface-muted)]/40 border border-[var(--color-hairline)] flex items-center justify-center">
              <FluidWaveformCanvas state={state} audioRMS={isMicMuted ? 0 : audioRMS} />
            </div>

            {/* Primary Session Control (Large, literal action button & Mute Toggle) */}
            <div className="py-2 flex flex-col items-center gap-2">
              <div className="flex items-center gap-2 sm:gap-3 flex-wrap justify-center">
                <button
                  onClick={onToggleSession}
                  type="button"
                  aria-label={isConnected ? 'Stop voice' : 'Start voice'}
                  className={`min-h-[50px] px-7 rounded-xl font-semibold text-[14.5px] flex items-center justify-center gap-2.5 transition-all cursor-pointer shadow-md focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-[var(--color-focus)] ${
                    isConnected
                      ? 'bg-[#fef2f2] hover:bg-[#fee2e2] text-[#991b1b] border border-[#f87171]/50 hover:shadow-lg'
                      : 'bg-[var(--color-action)] hover:bg-[var(--color-action-active)] text-white hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0'
                  }`}
                >
                  {isConnected ? (
                    <>
                      <MicOff className="w-4.5 h-4.5 text-[#dc2626]" />
                      <span>Stop voice</span>
                    </>
                  ) : (
                    <>
                      <Mic className="w-4.5 h-4.5 text-white" />
                      <span>Start voice</span>
                    </>
                  )}
                </button>

                {isConnected && onToggleMicMute && (
                  <button
                    onClick={onToggleMicMute}
                    type="button"
                    aria-label={isMicMuted ? 'Unmute microphone' : 'Mute microphone'}
                    className={`min-h-[50px] px-4 rounded-xl font-semibold text-[13px] flex items-center justify-center gap-2 border transition-all cursor-pointer shadow-xs ${
                      isMicMuted
                        ? 'bg-[#fee2e2] text-[#991b1b] border-[#f87171] hover:bg-[#fecaca]'
                        : 'bg-[var(--color-surface-muted)] text-[var(--color-ink)] border-[var(--color-hairline)] hover:bg-[var(--color-surface)]'
                    }`}
                    title={isMicMuted ? 'Microphone is muted. Click to speak.' : 'Click to mute your microphone'}
                  >
                    {isMicMuted ? (
                      <>
                        <MicOff className="w-4 h-4 text-[#dc2626]" />
                        <span>Muted</span>
                      </>
                    ) : (
                      <>
                        <Mic className="w-4 h-4 text-[var(--color-action)]" />
                        <span>Mute Mic</span>
                      </>
                    )}
                  </button>
                )}
              </div>
              <p className="text-[12px] text-[var(--color-muted)] font-medium">
                {isConnected 
                  ? (isMicMuted ? 'Microphone is muted — assistant cannot hear you' : 'Press to end live audio session') 
                  : 'Press to activate microphone and speech'}
              </p>
            </div>

            {/* Current Spoken Exchange / Live Dialogue Ribbon */}
            <div className="w-full mt-2 p-3.5 rounded-xl bg-[var(--color-surface-muted)]/70 border border-[var(--color-hairline)] text-left">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-wider">
                  {isMicMuted ? (
                    <span className="text-[#dc2626] font-bold flex items-center gap-1">
                      <MicOff className="w-3 h-3" /> Mic Muted
                    </span>
                  ) : isUserSpeaking ? (
                    <span className="text-[var(--color-action)] font-bold">You speaking</span>
                  ) : isAgentSpeaking ? (
                    <span className="text-[var(--color-link)] font-bold">Assistant speaking</span>
                  ) : (
                    <span className="text-[var(--color-muted)] font-semibold">Live Speech & Status</span>
                  )}
                </div>
                {noiseProfile && noiseProfile !== 'balanced' && (
                  <span className="text-[10px] font-mono uppercase tracking-wider text-[var(--color-muted)]">
                    {noiseProfile === 'noisy' ? 'High Filter Active' : 'Low Threshold'}
                  </span>
                )}
              </div>
              <p className="text-[13.5px] leading-relaxed text-[var(--color-ink)] font-medium line-clamp-3">
                {liveDialogue}
              </p>
            </div>
          </div>

          {/* Active Tool Task Banner / Progress Card */}
          {(activeTool || isThinking) && (
            <div className="rounded-lg p-3.5 border border-[var(--color-hairline)] bg-[var(--color-surface)] flex items-start gap-3 shadow-xs">
              <div className="w-7 h-7 rounded-md bg-[#fdf6ea] border border-[#f2debe] flex items-center justify-center shrink-0 text-[var(--color-warning)] mt-0.5">
                <Wrench className="w-3.5 h-3.5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[12px] font-semibold text-[var(--color-ink)]">
                  {activeTool ? 'Running connected service action' : 'Thinking and planning'}
                </div>
                <div className="text-[12px] text-[var(--color-body)] mt-0.5 font-mono truncate">
                  {activeTool ? `Tool: ${activeTool.name}` : 'Searching relevant memory and context...'}
                </div>
              </div>
            </div>
          )}

          {/* Text Command / Injection Input Bar */}
          <div className="rounded-lg border border-[var(--color-hairline)] bg-[var(--color-surface)] p-2 flex items-center gap-2 shadow-xs mt-auto">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!isConnected}
              placeholder={isConnected ? 'Type a command or message...' : 'Start voice session to send text...'}
              className="flex-1 bg-transparent px-2.5 py-1.5 text-[13px] text-[var(--color-ink)] outline-none placeholder:text-[var(--color-muted)] disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              onClick={handleSend}
              disabled={!inputText.trim() || !isConnected}
              type="button"
              aria-label="Send message"
              className="min-h-[36px] min-w-[36px] px-3 rounded-md bg-[var(--color-action)] hover:bg-[var(--color-action-active)] disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center justify-center transition-colors cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>

        </div>

        {/* Right Column (7 cols on lg): Spoken Dialogue Feed & Active Results */}
        <div className="lg:col-span-7 flex flex-col gap-3 min-h-0">
          
          {/* Transcript Dialogue Feed Card */}
          <div className="flex-1 rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] flex flex-col overflow-hidden shadow-xs min-h-[220px]">
            <div className="px-4 py-2.5 border-b border-[var(--color-hairline)] flex items-center justify-between bg-[var(--color-surface-muted)]/30">
              <span className="text-[13px] font-semibold text-[var(--color-ink)]">
                Spoken exchange transcript
              </span>
              <span className="text-[11px] font-mono text-[var(--color-muted)]">
                {transcripts.length} {transcripts.length === 1 ? 'turn' : 'turns'}
              </span>
            </div>

            {/* Scrollable Conversation Stream */}
            <div 
              ref={transcriptScrollRef}
              className="flex-1 p-4 overflow-y-auto flex flex-col gap-3.5"
            >
              {transcripts.length === 0 ? (
                <div className="h-full min-h-[140px] flex flex-col items-center justify-center text-center p-6 text-[var(--color-muted)]">
                  <Mic className="w-8 h-8 mb-2 text-[var(--color-faint)]" />
                  <p className="text-[14px] font-medium text-[var(--color-body)]">No spoken dialogue yet</p>
                  <p className="text-[12px] mt-1 max-w-sm text-[var(--color-muted)]">
                    Click "Start voice" on the left to speak with the assistant. Audio and tool execution transcripts will appear here in real time.
                  </p>
                </div>
              ) : (
                transcripts.map((entry) => {
                  const isUser = entry.role === 'user';
                  return (
                    <div 
                      key={entry.id}
                      className={`flex flex-col gap-1 max-w-[88%] ${isUser ? 'self-end items-end' : 'self-start items-start'}`}
                    >
                      <div className="flex items-center gap-1.5 text-[11px] font-mono text-[var(--color-muted)]">
                        <span>{isUser ? 'You' : 'Assistant'}</span>
                        <span>·</span>
                        <span>{new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        <span>{(() => { const d = new Date(entry.timestamp); return isNaN(d.getTime()) ? '' : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); })()}</span>
                      </div>
                      <div 
                        className={`p-3 rounded-lg text-[13.5px] leading-relaxed ${
                          isUser
                            ? 'bg-[var(--color-surface-muted)] text-[var(--color-ink)] border border-[var(--color-hairline)]'
                            : 'bg-white text-[var(--color-ink)] border border-[var(--color-hairline)]'
                        }`}
                      >
                        <Message entry={entry} />
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Recent Result / Tool Finding Card */}
          {latestFinding && (
            <div className="rounded-lg border border-[var(--color-hairline)] bg-[var(--color-surface)] p-3.5 shadow-xs shrink-0">
              <div className="flex items-center justify-between pb-1.5 border-b border-[var(--color-hairline)] mb-2">
                <div className="flex items-center gap-1.5 text-[12px] font-semibold text-[var(--color-ink)]">
                  <CheckCircle2 className="w-4 h-4 text-[var(--color-success)]" />
                  <span>Task outcome: {latestFinding.title}</span>
                </div>
                <span className="text-[11px] font-mono text-[var(--color-muted)]">
                  {new Date(latestFinding.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  {(() => { const d = new Date(latestFinding.timestamp); return isNaN(d.getTime()) ? '' : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); })()}
                </span>
              </div>
              <p className="text-[13px] text-[var(--color-body)] leading-relaxed">
                {latestFinding.summary}
              </p>
              {latestFinding.details && Object.keys(latestFinding.details).length > 0 && (
                <div className="mt-2 pt-2 border-t border-[var(--color-hairline)] flex justify-end">
                  <button
                    onClick={onOpenActivity}
                    className="text-[12px] font-medium text-[var(--color-link)] hover:underline flex items-center gap-1 cursor-pointer"
                  >
                    <span>View details</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              )}
            </div>
          )}

        </div>

      </div>

    </div>
  );
};

export default VoiceStudioPage;

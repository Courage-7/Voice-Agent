import { useState, useRef, useCallback, useEffect } from 'react';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import { MessageBlock, SessionState, TranscriptEntry, ToolTrace, FindingItem } from '@/types';

export type NoiseProfile = 'balanced' | 'noisy' | 'quiet';

// ─── Utilities ────────────────────────────────────────────────────────────────

function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  const buf = new Uint32Array(2);
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    crypto.getRandomValues(buf);
    return `${Date.now()}-${buf[0].toString(36)}${buf[1].toString(36)}`;
  }
  return `${Date.now()}`;
}

export function sanitizeDialogueText(text: string): string {
  if (!text) return '';
  return text
    .replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F600}-\u{1F64F}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{200D}]|[\u{FE0F}]|[\u{1FA00}-\u{1FAFF}]|[\u{1F000}-\u{1F02F}]/gu, '')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*{1,3}/g, '')
    .replace(/[ \t]{2,}/g, ' ')
    .trim();
}

/** Preprocess markdown content for visual display, preserving all headings, bolding, lists, and code blocks. */
export function sanitizeDisplayText(text: string): string {
  if (!text) return '';
  return text
    .replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F600}-\u{1F64F}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{200D}]|[\u{FE0F}]|[\u{1FA00}-\u{1FAFF}]|[\u{1F000}-\u{1F02F}]/gu, '')
    .trim();
}

/** Determine smart separator between two streamed chunks. */
function chunkSeparator(existing: string, incoming: string): string {
  const isBulletOrList = /^[-*•]\s+|^\d+\.\s+/.test(incoming.trim());
  const prevEndsWithBreak = /[:\n]$/.test(existing.trim());
  return (isBulletOrList || prevEndsWithBreak) ? '\n\n' : ' ';
}

// ─── AudioWorklet (inline, avoids network fetch) ─────────────────────────────

const AUDIO_RECORDER_WORKLET = `
class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Float32Array(1024);
    this.bytesWritten = 0;
  }
  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;
    const channel = input[0];
    for (let i = 0; i < channel.length; i++) {
      this.buffer[this.bytesWritten++] = channel[i];
      if (this.bytesWritten >= 1024) {
        this.port.postMessage(this.buffer);
        this.buffer = new Float32Array(1024);
        this.bytesWritten = 0;
      }
    }
    return true;
  }
}
registerProcessor('pcm-capture-processor', PcmCaptureProcessor);
`;

// ─── Turn accumulator ─────────────────────────────────────────────────────────
// Kept in a ref so all callbacks always read the live value with no closure staleness.

interface TurnAccumulator {
  /** Stable UUID for the current assistant turn — set once when the turn opens. */
  id: string;
  /** Whether an assistant turn is currently open. */
  open: boolean;
  /** Sequence number: increments with each ConversationText event for this turn. */
  seq: number;
  /** The seen ConversationText message IDs (for idempotency if server retries). */
  seenMsgIds: Set<string>;
}

function freshAccumulator(): TurnAccumulator {
  return { id: '', open: false, seq: 0, seenMsgIds: new Set() };
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useVoiceAgent() {
  const { getAuthHeaders } = useAuth();
  // ── React state (UI-visible) ────────────────────────────────────────────────
  const [state, setState] = useState<SessionState>('DISCONNECTED');
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [findings, setFindings] = useState<FindingItem[]>([]);
  const [recentTools, setRecentTools] = useState<ToolTrace[]>([]);
  const [currentSubtitle, setCurrentSubtitle] = useState<string>(
    'Voice assistant standing by. Activate to initiate session.'
  );
  const [activeTool, setActiveTool] = useState<ToolTrace | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [turnsCount, setTurnsCount] = useState<number>(0);
  const [audioRMS, setAudioRMS] = useState<number>(0);
  const [noiseProfile, setNoiseProfile] = useState<NoiseProfile>('balanced');
  const [isMicMuted, setIsMicMuted] = useState<boolean>(false);

  // ── Refs: always-current, no closure staleness ─────────────────────────────
  const stateRef = useRef<SessionState>('DISCONNECTED');
  const isMicMutedRef = useRef<boolean>(false);
  isMicMutedRef.current = isMicMuted;
  const noiseProfileRef = useRef<NoiseProfile>('balanced');
  noiseProfileRef.current = noiseProfile;

  // Streaming turn accumulator — THE single source of truth for "which turn is open"
  const turnRef = useRef<TurnAccumulator>(freshAccumulator());

  // Audio refs
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<AudioNode | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const nextPlayTimeRef = useRef<number>(0);
  const activeSourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const isAudioPlayingRef = useRef<boolean>(false);
  const playbackSuppressedRef = useRef<boolean>(false);
  const agentStartedSpeakingTimeRef = useRef<number>(0);

  // VAD refs
  const noiseFloorRef = useRef<number>(0.015);
  const consecutiveSpeechFramesRef = useRef<number>(0);
  const recentSpeechRmsRef = useRef<number>(0);

  // Stable handler ref: ws.onmessage points here; we overwrite .current on every render
  // so it always calls the latest version of handleControlMessage without re-binding ws.
  const wsHandlerRef = useRef<((msg: any) => void) | null>(null);

  // ── State helpers ───────────────────────────────────────────────────────────

  const updateState = useCallback((newState: SessionState) => {
    setState(newState);
    stateRef.current = newState;
  }, []);

  // ── Audio playback ──────────────────────────────────────────────────────────

  const stopAllAudioPlayback = useCallback(() => {
    activeSourcesRef.current.forEach((source) => {
      try { source.stop(); source.disconnect(); } catch {}
    });
    activeSourcesRef.current = [];
    isAudioPlayingRef.current = false;
    if (playbackContextRef.current) {
      nextPlayTimeRef.current = playbackContextRef.current.currentTime;
    }
    setAudioRMS(0);
  }, []);

  const playSynthesizedAudio = useCallback((buffer: ArrayBuffer) => {
    if (isMicMutedRef.current || stateRef.current !== 'USER_SPEAKING') {
      playbackSuppressedRef.current = false;
    }
    if (playbackSuppressedRef.current || !playbackContextRef.current) return;

    const pcm16 = new Int16Array(buffer);
    const float32 = new Float32Array(pcm16.length);
    let sumSq = 0.0;
    for (let i = 0; i < pcm16.length; i++) {
      const val = pcm16[i] / 32768.0;
      float32[i] = val;
      sumSq += val * val;
    }

    isAudioPlayingRef.current = true;
    if (stateRef.current !== 'SPEAKING') {
      updateState('SPEAKING');
      agentStartedSpeakingTimeRef.current = performance.now();
    }
    setAudioRMS(Math.min(1.0, Math.sqrt(sumSq / pcm16.length) * 7.0));

    const audioBuf = playbackContextRef.current.createBuffer(1, float32.length, 24000);
    audioBuf.getChannelData(0).set(float32);

    const source = playbackContextRef.current.createBufferSource();
    source.buffer = audioBuf;
    source.connect(playbackContextRef.current.destination);

    const now = playbackContextRef.current.currentTime;
    const startTime = Math.max(now, nextPlayTimeRef.current);
    source.start(startTime);
    nextPlayTimeRef.current = startTime + audioBuf.duration;

    activeSourcesRef.current.push(source);
    source.onended = () => {
      const idx = activeSourcesRef.current.indexOf(source);
      if (idx > -1) activeSourcesRef.current.splice(idx, 1);
      if (activeSourcesRef.current.length === 0) {
        isAudioPlayingRef.current = false;
        setAudioRMS(0);
        if (stateRef.current === 'SPEAKING') {
          updateState(isMicMutedRef.current ? 'MUTED' : 'LISTENING');
        }
      }
    };
  }, [updateState]);

  // ── Transcript accumulation ─────────────────────────────────────────────────
  //
  // Protocol:
  //   • One assistant TURN = one stable UUID (turnRef.id).
  //   • Turn opens on first ConversationText(role=assistant) and stays open until
  //     ConversationText(role=user) or an explicit session reset.
  //   • AgentAudioDone is a TTS segment boundary — it does NOT close the turn.
  //     Multiple TTS segments can belong to the same LLM turn.
  //   • All setTranscripts calls use functional updaters that receive `prev` from
  //     React so no captured mutable state is used inside the updater.
  //   • display.content is ACCUMULATED (same logic as content) — not replaced.

  /**
   * Open a new assistant turn if one is not already open, returning the stable turn ID.
   * Thread-safe: checks and sets turnRef atomically before any async boundary.
   */
  const openAssistantTurn = useCallback((): string => {
    if (!turnRef.current.open) {
      turnRef.current = {
        id: generateUUID(),
        open: true,
        seq: 0,
        seenMsgIds: new Set(),
      };
      setTurnsCount((c) => c + 1);
    }
    return turnRef.current.id;
  }, []);

  /**
   * Close the current assistant turn (called only on user message or session reset).
   */
  const closeAssistantTurn = useCallback(() => {
    turnRef.current = freshAccumulator();
  }, []);

  /**
   * Append or create a user message. Closes any open assistant turn first.
   */
  const appendUserMessage = useCallback((text: string) => {
    closeAssistantTurn();
    const userText = sanitizeDialogueText(text) || text;
    setCurrentSubtitle(userText);
    setTranscripts((prev) => {
      const last = prev[prev.length - 1];
      // Idempotency: skip if last entry is identical (optimistic-inject vs WS echo)
      if (last && last.role === 'user' && last.content.trim().toLowerCase() === userText.trim().toLowerCase()) {
        return prev;
      }
      return [...prev, { id: generateUUID(), role: 'user', content: userText, timestamp: new Date().toISOString() }];
    });
  }, [closeAssistantTurn]);

  /**
   * Append an assistant chunk to the stable turn entry.
   * Uses functional setTranscripts so no mutable state is captured.
   */
  const appendAssistantChunk = useCallback((
    rawContent: string,
    rawDisplay?: string,
    rawSpeech?: string,
    blocks?: MessageBlock[],
    msgId?: string,
  ) => {
    // Idempotency: skip duplicate message IDs (server retry / double-delivery)
    if (msgId) {
      if (turnRef.current.seenMsgIds.has(msgId)) return;
      turnRef.current.seenMsgIds.add(msgId);
    }

    const turnId = openAssistantTurn();
    turnRef.current.seq += 1;
    const seq = turnRef.current.seq;

    const cleanContent = sanitizeDialogueText(rawContent);
    const cleanDisplay = rawDisplay ? sanitizeDisplayText(rawDisplay) : undefined;
    const cleanSpeech  = rawSpeech  ? sanitizeDialogueText(rawSpeech)  : undefined;

    // Update subtitle with latest speech text
    setCurrentSubtitle(cleanSpeech || cleanContent || rawContent);

    setTranscripts((prev) => {
      const last = prev[prev.length - 1];

      if (last && last.role === 'assistant' && last.id === turnId) {
        // ── Append to existing turn entry ────────────────────────────────────
        const sep = chunkSeparator(last.content, cleanContent);

        // Content
        let updatedContent: string;
        if (!last.content) {
          updatedContent = cleanContent;
        } else if (cleanContent.startsWith(last.content)) {
          updatedContent = cleanContent;
        } else if (last.content.endsWith(cleanContent)) {
          updatedContent = last.content;
        } else {
          updatedContent = `${last.content}${sep}${cleanContent}`.trim();
        }

        // Display markdown (rich formatting, headings, bullets, code)
        const existingDisplay = last.display?.content || '';
        let updatedDisplay = last.display;
        if (cleanDisplay) {
          let finalDisplayContent: string;
          if (!existingDisplay) {
            finalDisplayContent = cleanDisplay;
          } else if (cleanDisplay.startsWith(existingDisplay)) {
            // Snapshot streaming (full markdown received so far)
            finalDisplayContent = cleanDisplay;
          } else if (existingDisplay.endsWith(cleanDisplay)) {
            finalDisplayContent = existingDisplay;
          } else {
            finalDisplayContent = `${existingDisplay}${sep}${cleanDisplay}`.trim();
          }
          updatedDisplay = {
            format: 'markdown' as const,
            content: finalDisplayContent,
          };
        }

        // Speech audio text
        let updatedSpeech = last.speech;
        if (cleanSpeech) {
          const existingSpeech = last.speech?.text || '';
          let finalSpeech: string;
          if (!existingSpeech) {
            finalSpeech = cleanSpeech;
          } else if (cleanSpeech.startsWith(existingSpeech)) {
            finalSpeech = cleanSpeech;
          } else {
            finalSpeech = `${existingSpeech} ${cleanSpeech}`.trim();
          }
          updatedSpeech = { text: finalSpeech };
        }

        return [
          ...prev.slice(0, -1),
          {
            ...last,
            content: updatedContent,
            display: updatedDisplay,
            speech: updatedSpeech,
            blocks: blocks || last.blocks,
          },
        ];
      }

      // ── Create new turn entry (first chunk of this turn) ──────────────────
      // Guard: if there's already a non-matching assistant entry at the end with
      // seq > 1, something is wrong — log and still create (safe fallback).
      if (last && last.role === 'assistant' && last.id !== turnId && seq > 1) {
        console.warn('[useVoiceAgent] Turn ID mismatch at seq', seq, '— creating new entry as fallback.');
      }

      return [
        ...prev,
        {
          id: turnId,
          role: 'assistant',
          content: cleanContent,
          timestamp: new Date().toISOString(),
          display: cleanDisplay ? { format: 'markdown' as const, content: cleanDisplay } : undefined,
          speech: cleanSpeech ? { text: cleanSpeech } : undefined,
          blocks,
        },
      ];
    });
  }, [openAssistantTurn]);

  // ── Mic mute ────────────────────────────────────────────────────────────────

  const toggleMicMute = useCallback(() => {
    setIsMicMuted((prev) => {
      const next = !prev;
      isMicMutedRef.current = next;
      if (next) {
        if (stateRef.current !== 'SPEAKING' && stateRef.current !== 'THINKING') {
          updateState('MUTED');
        }
        consecutiveSpeechFramesRef.current = 0;
        playbackSuppressedRef.current = false;
        setAudioRMS(0);
      } else {
        if (stateRef.current === 'MUTED') {
          updateState('LISTENING');
        }
      }
      toast.info(next ? 'Microphone Muted' : 'Microphone Unmuted', {
        description: next
          ? 'Voice input is paused. The assistant will not hear audio.'
          : 'Voice input is active.',
      });
      return next;
    });
  }, [updateState]);

  // ── Tool findings ───────────────────────────────────────────────────────────

  const appendFindingFromTool = useCallback((name: string, params: Record<string, any>) => {
    let type: FindingItem['type'] = 'workspace';
    let title = name.toUpperCase().replaceAll('_', ' ');

    if (name.includes('email') || name.includes('mail')) {
      type = 'email'; title = 'Email Extraction & Dispatch';
    } else if (name.includes('calendar') || name.includes('event')) {
      type = 'calendar'; title = 'Calendar Event & Scheduling';
    } else if (name.includes('search')) {
      type = 'search'; title = 'Web Intelligence Synthesis';
    }

    const safeParams: Record<string, any> =
      typeof params === 'string'
        ? (() => { try { return JSON.parse(params); } catch { return { query: params }; } })()
        : params || {};

    // Build a human-readable summary — never dump raw parameter counts
    let summary: string;
    if (safeParams.query)          summary = `Query: "${String(safeParams.query).slice(0, 100)}"`;
    else if (safeParams.title)     summary = `Title: "${String(safeParams.title).slice(0, 100)}"`;
    else if (safeParams.recipient) summary = `Recipient: ${String(safeParams.recipient).slice(0, 80)}`;
    else if (safeParams.subject)   summary = `Subject: "${String(safeParams.subject).slice(0, 100)}"`;
    else                           summary = `Ran ${name.replaceAll('_', ' ')}`;

    setFindings((prev) => [{
      id: generateUUID(), type, title, summary,
      details: safeParams, timestamp: new Date().toISOString(),
    }, ...prev]);
  }, []);

  // ── Session management ──────────────────────────────────────────────────────

  const stopSession = useCallback(() => {
    updateState('DISCONNECTED');
    playbackSuppressedRef.current = false;
    setAudioRMS(0);
    setActiveTool(null);
    closeAssistantTurn();
    stopAllAudioPlayback();

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
  }, [closeAssistantTurn, stopAllAudioPlayback, updateState]);

  // ── WebSocket event handlers ────────────────────────────────────────────────
  //
  // IMPORTANT: These are defined as plain functions (not useCallback) assigned
  // into wsHandlerRef.current on every render. ws.onmessage calls wsHandlerRef.current(msg)
  // so it always invokes the latest version — no stale closure ever.

  const handleConversationText = (msg: any) => {
    setActiveTool(null);

    const displayContent = msg.display_markdown || msg.display?.content;
    const speechText     = msg.speech_text || msg.speech?.text;
    const content        = speechText || displayContent || msg.content || '';
    const blocks         = Array.isArray(msg.blocks) ? msg.blocks : undefined;
    const msgId          = msg.message_id || msg.id;

    // Interim STT: only update subtitle, never commit to history
    if (msg.role === 'user' && msg.is_final === false) {
      if (content) setCurrentSubtitle(content);
      return;
    }

    if (!content || content.startsWith('Hi, please greet me')) return;

    if (msg.role === 'user') {
      appendUserMessage(content);
      updateState('THINKING');
    } else {
      // role === 'assistant' (or missing)
      appendAssistantChunk(content, displayContent, speechText, blocks, msgId);
      playbackSuppressedRef.current = false;
      updateState('SPEAKING');
    }
  };

  const handleFunctionCall = (msg: any) => {
    const fns = msg.functions || [{ name: msg.function_name || msg.name, arguments: msg.input || msg.parameters }];
    if (fns.length > 0) {
      let rawArgs = fns[0].arguments || {};
      if (typeof rawArgs === 'string') {
        try { rawArgs = JSON.parse(rawArgs); } catch { rawArgs = { query: rawArgs }; }
      }
      const trace: ToolTrace = { name: fns[0].name || 'Tool', params: rawArgs, timestamp: Date.now() };
      setActiveTool(trace);
      setRecentTools((prev) => [trace, ...prev.slice(0, 20)]);
      appendFindingFromTool(trace.name, rawArgs);
    }
  };

  const handleControlMessage = (msg: any) => {
    switch (msg.type) {
      case 'SessionStateChange': {
        const stateUpper = msg.state.toUpperCase();
        updateState(stateUpper);
        if (stateUpper === 'DISCONNECTED') stopSession();
        break;
      }
      case 'ConversationText':
        handleConversationText(msg);
        break;
      case 'FunctionCallRequest':
        handleFunctionCall(msg);
        break;
      case 'UserStartedSpeaking': {
        const isAgentActive = isAudioPlayingRef.current || activeSourcesRef.current.length > 0;
        if (isAgentActive) {
          // Guard: only interrupt if local audio energy is genuinely speech, not noise
          const bargeThreshold = noiseProfileRef.current === 'noisy' ? 0.09 : 0.065;
          if (recentSpeechRmsRef.current > bargeThreshold || consecutiveSpeechFramesRef.current >= 2) {
            updateState('USER_SPEAKING');
            stopAllAudioPlayback();
            playbackSuppressedRef.current = true;
          }
        } else {
          updateState('USER_SPEAKING');
        }
        break;
      }
      case 'AgentThinking':
        updateState('THINKING');
        playbackSuppressedRef.current = false;
        break;
      case 'AgentStartedSpeaking':
        updateState('SPEAKING');
        playbackSuppressedRef.current = false;
        agentStartedSpeakingTimeRef.current = performance.now();
        break;
      case 'AgentAudioDone':
        // ── TTS segment boundary — NOT a conversation turn boundary ──────────
        // Do NOT close the assistant turn here. The LLM turn may continue with
        // additional ConversationText + audio segments. The turn closes only when
        // a user ConversationText arrives or the session resets.
        if (activeSourcesRef.current.length === 0) {
          updateState(isMicMutedRef.current ? 'MUTED' : 'LISTENING');
          isAudioPlayingRef.current = false;
        }
        playbackSuppressedRef.current = false;
        setActiveTool(null);
        break;
      case 'LatencyReport': {
        const rawLat = msg.latency_ms ?? (msg.total_latency
          ? (msg.total_latency < 10 ? msg.total_latency * 1000 : msg.total_latency)
          : null);
        if (rawLat !== null && rawLat !== undefined) {
          setLatencyMs(Math.round(rawLat));
        }
        break;
      }
      default:
        break;
    }
  };

  // Always keep wsHandlerRef pointing at the latest handleControlMessage
  wsHandlerRef.current = handleControlMessage;

  // ── Microphone ──────────────────────────────────────────────────────────────

  const startMicrophone = useCallback(async () => {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    audioContextRef.current = new AudioCtx({ sampleRate: 16000 });
    if (audioContextRef.current.state === 'suspended') {
      await audioContextRef.current.resume();
    }

    micStreamRef.current = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });

    const src = audioContextRef.current.createMediaStreamSource(micStreamRef.current);
    const muteGain = audioContextRef.current.createGain();
    muteGain.gain.value = 0;

    const processAudioData = (input: Float32Array) => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) return;

      // Mute guard
      if (isMicMutedRef.current) {
        const silent = new Int16Array(input.length);
        wsRef.current.send(silent.buffer);
        setAudioRMS(0);
        if (stateRef.current !== 'MUTED' && stateRef.current !== 'SPEAKING' && stateRef.current !== 'THINKING') {
          updateState('MUTED');
          playbackSuppressedRef.current = false;
        }
        return;
      }

      const pcm16 = new Int16Array(input.length);
      let sumSq = 0.0;
      for (let i = 0; i < input.length; i++) {
        const s = Math.max(-1, Math.min(1, input[i]));
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        sumSq += s * s;
      }

      const inputRMS = Math.sqrt(sumSq / input.length);
      recentSpeechRmsRef.current = inputRMS;

      // Adaptive noise floor
      if (inputRMS < noiseFloorRef.current * 1.5) {
        noiseFloorRef.current = noiseFloorRef.current * 0.97 + inputRMS * 0.03;
      } else {
        noiseFloorRef.current = noiseFloorRef.current * 0.995 + inputRMS * 0.005;
      }
      noiseFloorRef.current = Math.max(0.008, Math.min(0.05, noiseFloorRef.current));

      // Dynamic thresholds
      const profile = noiseProfileRef.current;
      const baseMult  = profile === 'noisy' ? 2.6 : profile === 'quiet' ? 1.8 : 2.2;
      const bargeMult = profile === 'noisy' ? 4.5 : profile === 'quiet' ? 2.8 : 3.6;
      const minSpeech = profile === 'noisy' ? 0.065 : profile === 'quiet' ? 0.035 : 0.048;
      const minBarge  = profile === 'noisy' ? 0.12  : profile === 'quiet' ? 0.065 : 0.09;
      // requiredFrames: 1 AudioWorklet frame = 1024 samples @ 16kHz ≈ 64ms
      // quiet=25 (~1.6s), balanced=35 (~2.2s), noisy=45 (~2.9s)
      const requiredFrames = profile === 'noisy' ? 45 : profile === 'quiet' ? 25 : 35;

      const speechThreshold = Math.max(minSpeech, noiseFloorRef.current * baseMult);
      const bargeThreshold  = Math.max(minBarge,  noiseFloorRef.current * bargeMult);

      const isAgentActive = isAudioPlayingRef.current || activeSourcesRef.current.length > 0 || stateRef.current === 'SPEAKING';
      const now = performance.now();
      const inWarmupGrace = (now - agentStartedSpeakingTimeRef.current) < 350;

      if (isAgentActive && !inWarmupGrace) {
        if (inputRMS > bargeThreshold) {
          consecutiveSpeechFramesRef.current += 1;
          if (consecutiveSpeechFramesRef.current >= requiredFrames) {
            stopAllAudioPlayback();
            playbackSuppressedRef.current = true;
            updateState('USER_SPEAKING');
            consecutiveSpeechFramesRef.current = 0;
          }
        } else {
          consecutiveSpeechFramesRef.current = Math.max(0, consecutiveSpeechFramesRef.current - 1);
        }
      } else if (!isAgentActive) {
        if (inputRMS > speechThreshold) {
          consecutiveSpeechFramesRef.current += 1;
          if (consecutiveSpeechFramesRef.current >= 2 && stateRef.current !== 'USER_SPEAKING') {
            updateState('USER_SPEAKING');
          }
        } else {
          consecutiveSpeechFramesRef.current = Math.max(0, consecutiveSpeechFramesRef.current - 1);
          if (consecutiveSpeechFramesRef.current === 0 && stateRef.current === 'USER_SPEAKING') {
            updateState('LISTENING');
            playbackSuppressedRef.current = false;
          }
        }
      }

      if (stateRef.current === 'USER_SPEAKING') {
        setAudioRMS(Math.min(1.0, inputRMS * 8.0));
      }

      // Silence gating
      const isNoiseHiss = !isAgentActive && inputRMS < (noiseFloorRef.current * 1.15) && inputRMS < 0.022;
      if (isNoiseHiss) pcm16.fill(0);

      wsRef.current.send(pcm16.buffer);
    };

    if (audioContextRef.current.audioWorklet) {
      try {
        const blob = new Blob([AUDIO_RECORDER_WORKLET], { type: 'application/javascript' });
        const workletUrl = URL.createObjectURL(blob);
        await audioContextRef.current.audioWorklet.addModule(workletUrl);
        URL.revokeObjectURL(workletUrl);

        const workletNode = new AudioWorkletNode(audioContextRef.current, 'pcm-capture-processor');
        workletNode.port.onmessage = (e: MessageEvent<Float32Array>) => processAudioData(e.data);
        src.connect(workletNode);
        workletNode.connect(muteGain);
        muteGain.connect(audioContextRef.current.destination);
        processorRef.current = workletNode;
        return;
      } catch (err) {
        console.warn('AudioWorklet registration failed, falling back to script processor:', err);
      }
    }

    const legacyCtx = audioContextRef.current as any;
    const legacyProcessor: any = legacyCtx.createScriptProcessor?.(1024, 1, 1);
    if (legacyProcessor) {
      legacyProcessor.onaudioprocess = (e: any) => processAudioData(e.inputBuffer.getChannelData(0));
      src.connect(legacyProcessor);
      legacyProcessor.connect(muteGain);
      muteGain.connect(audioContextRef.current.destination);
      processorRef.current = legacyProcessor;
    }
  }, [stopAllAudioPlayback, updateState]);

  // ── Session start ───────────────────────────────────────────────────────────

  const startSession = useCallback(async (voiceModel: string) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      playbackContextRef.current ??= new AudioCtx({ sampleRate: 24000 });
      if (playbackContextRef.current.state === 'suspended') {
        await playbackContextRef.current.resume();
      }
      nextPlayTimeRef.current = playbackContextRef.current.currentTime;
      playbackSuppressedRef.current = false;
      closeAssistantTurn();

      const authHeaders = await getAuthHeaders();
      const headers = {
        ...authHeaders,
        'Content-Type': 'application/json',
      };

      const res = await fetch('/api/voice/sessions', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({ persona: 'companion', voice_model: voiceModel }),
      });

      if (res.status === 401) {
        toast.error('Authentication Required', { description: 'Please sign in with your email to start a voice session.' });
        stopSession();
        return;
      }
      if (!res.ok) {
        toast.error('Session Initialization Failed', { description: `Server returned HTTP ${res.status}` });
        stopSession();
        return;
      }

      const data = await res.json();
      const sessionId = data.session_id;

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/voice/ws/${sessionId}?voice=${encodeURIComponent(voiceModel)}`;

      const token = authHeaders.Authorization?.replace(/^Bearer\s+/i, '');
      if (!token) {
        toast.error('Authentication Required', { description: 'Your Clerk session token is unavailable. Please sign in again.' });
        stopSession();
        return;
      }
      const ws = new WebSocket(wsUrl, ['shinra-auth', token]);
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      ws.onopen = async () => {
        updateState('CONNECTED');
        try {
          await startMicrophone();
          toast.success('Voice Session Active', { description: `Streaming with voice: ${voiceModel}` });
        } catch (micErr: any) {
          console.error('Microphone access failed:', micErr);
          toast.error('Microphone Access Denied', {
            description: 'Please enable microphone permissions in your browser to speak with Shinra.',
          });
          stopSession();
        }
      };

      // ── Stable message dispatch via wsHandlerRef ─────────────────────────
      // ws.onmessage never changes — it always calls wsHandlerRef.current which
      // is reassigned on every render to the latest handleControlMessage closure.
      // This eliminates the stale-closure chain without rebinding the socket.
      ws.onmessage = (e) => {
        if (e.data instanceof ArrayBuffer) {
          playSynthesizedAudio(e.data);
        } else {
          try {
            const msg = JSON.parse(e.data);
            wsHandlerRef.current?.(msg);
          } catch (err) {
            console.warn('[useVoiceAgent] Failed to parse WS message:', err);
          }
        }
      };

      ws.onclose = () => stopSession();
      ws.onerror = (err) => {
        console.error('WS Error:', err);
        toast.error('Voice Connection Lost', { description: 'Real-time WebSocket stream was closed unexpectedly.' });
        stopSession();
      };
    } catch (err: any) {
      toast.error('Voice Session Initialization Failed', { description: err?.message || String(err) });
      stopSession();
    }
  }, [closeAssistantTurn, getAuthHeaders, playSynthesizedAudio, startMicrophone, stopSession, updateState]);

  // ── Text injection ──────────────────────────────────────────────────────────

  const injectTextMessage = useCallback((text: string) => {
    if (text && wsRef.current?.readyState === WebSocket.OPEN) {
      stopAllAudioPlayback();
      playbackSuppressedRef.current = false;
      wsRef.current.send(JSON.stringify({ type: 'InjectUserMessage', content: text }));
      setCurrentSubtitle(`"${text}"`);
      appendUserMessage(text);
    }
  }, [appendUserMessage, stopAllAudioPlayback]);

  // ── Transcript clear ────────────────────────────────────────────────────────

  const clearTranscripts = useCallback(() => {
    setTranscripts([]);
    setTurnsCount(0);
    closeAssistantTurn();
  }, [closeAssistantTurn]);

  // ── Cleanup on unmount ──────────────────────────────────────────────────────

  useEffect(() => {
    return () => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, []);

  // ── Public API ──────────────────────────────────────────────────────────────

  return {
    state,
    transcripts,
    findings,
    recentTools,
    currentSubtitle,
    activeTool,
    latencyMs,
    turnsCount,
    audioRMS,
    noiseProfile,
    isMicMuted,
    setNoiseProfile,
    toggleMicMute,
    startSession,
    stopSession,
    injectTextMessage,
    clearTranscripts,
  };
}

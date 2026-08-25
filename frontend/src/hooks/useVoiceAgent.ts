import { useState, useRef, useCallback } from 'react';
import { SessionState, TranscriptEntry, ToolTrace, FindingItem } from '@/types';

export function useVoiceAgent() {
  const [state, setState] = useState<SessionState>('DISCONNECTED');
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [findings, setFindings] = useState<FindingItem[]>([]);
  const [recentTools, setRecentTools] = useState<ToolTrace[]>([]);
  const [currentSubtitle, setCurrentSubtitle] = useState<string>(
    'SHINRA Voice Intelligence standing by. Activate to initiate dialogue.'
  );
  const [activeTool, setActiveTool] = useState<ToolTrace | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [turnsCount, setTurnsCount] = useState<number>(0);
  const [audioRMS, setAudioRMS] = useState<number>(0);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const nextPlayTimeRef = useRef<number>(0);
  const activeSourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const playbackSuppressedRef = useRef<boolean>(false);
  const stateRef = useRef<SessionState>('DISCONNECTED');

  const updateState = useCallback((newState: SessionState) => {
    setState(newState);
    stateRef.current = newState;
  }, []);

  const stopAllAudioPlayback = useCallback(() => {
    activeSourcesRef.current.forEach((source) => {
      try {
        source.stop();
        source.disconnect();
      } catch {}
    });
    activeSourcesRef.current = [];
    if (playbackContextRef.current) {
      nextPlayTimeRef.current = playbackContextRef.current.currentTime;
    }
  }, []);

  const playSynthesizedAudio = useCallback((buffer: ArrayBuffer) => {
    if (playbackSuppressedRef.current || !playbackContextRef.current) return;

    const pcm16 = new Int16Array(buffer);
    const float32 = new Float32Array(pcm16.length);
    let sumSq = 0.0;

    for (let i = 0; i < pcm16.length; i++) {
      const val = pcm16[i] / 32768.0;
      float32[i] = val;
      sumSq += val * val;
    }

    if (stateRef.current === 'SPEAKING') {
      setAudioRMS(Math.min(1.0, Math.sqrt(sumSq / pcm16.length) * 7.0));
    }

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
      if (activeSourcesRef.current.length === 0) setAudioRMS(0);
    };
  }, []);

  const appendTranscript = useCallback((role: 'user' | 'assistant' | 'system', content: string) => {
    const newEntry: TranscriptEntry = {
      id: `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      role,
      content,
      timestamp: new Date().toLocaleTimeString(),
    };
    setTranscripts((prev) => [...prev, newEntry]);
  }, []);

  const appendFindingFromTool = useCallback((name: string, params: Record<string, any>) => {
    let type: FindingItem['type'] = 'workspace';
    let title = name.toUpperCase().replace(/_/g, ' ');

    if (name.includes('email') || name.includes('mail')) {
      type = 'email';
      title = 'Email Extraction & Dispatch';
    } else if (name.includes('calendar') || name.includes('event')) {
      type = 'calendar';
      title = 'Calendar Event & Scheduling';
    } else if (name.includes('search')) {
      type = 'search';
      title = 'Web Intelligence Synthesis';
    }

    const summary = params.query
      ? `Query: "${params.query}"`
      : params.title
      ? `Title: "${params.title}"`
      : params.recipient
      ? `Recipient: ${params.recipient}`
      : `Executed action ${name} with ${Object.keys(params).length} parameters.`;

    const newFinding: FindingItem = {
      id: `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      type,
      title,
      summary,
      details: params,
      timestamp: new Date().toLocaleTimeString(),
    };

    setFindings((prev) => [newFinding, ...prev]);
  }, []);

  const stopSession = useCallback(() => {
    updateState('DISCONNECTED');
    playbackSuppressedRef.current = false;
    setAudioRMS(0);
    setActiveTool(null);
    stopAllAudioPlayback();

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
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
  }, [stopAllAudioPlayback, updateState]);

  const handleControlMessage = useCallback(
    (msg: any) => {
      if (msg.type === 'SessionStateChange') {
        updateState(msg.state.toUpperCase());
        if (msg.state.toUpperCase() === 'DISCONNECTED') stopSession();
      } else if (msg.type === 'ConversationText') {
        setActiveTool(null);
        if (msg.content && !msg.content.startsWith('Hi, please greet me')) {
          setCurrentSubtitle(msg.content);
          appendTranscript(msg.role || 'assistant', msg.content);
        }
        if (msg.role === 'assistant') {
          playbackSuppressedRef.current = false;
          setTurnsCount((prev) => prev + 1);
        }
      } else if (msg.type === 'FunctionCallRequest') {
        const fns = msg.functions || [{ name: msg.function_name || msg.name, arguments: msg.input || msg.parameters }];
        if (fns.length > 0) {
          const trace: ToolTrace = {
            name: fns[0].name || 'Tool',
            params: fns[0].arguments || {},
            timestamp: Date.now(),
          };
          setActiveTool(trace);
          setRecentTools((prev) => [trace, ...prev.slice(0, 20)]);
          appendFindingFromTool(trace.name, trace.params);
        }
      } else if (msg.type === 'UserStartedSpeaking') {
        updateState('USER_SPEAKING');
        stopAllAudioPlayback();
        playbackSuppressedRef.current = true;
      } else if (msg.type === 'AgentThinking') {
        updateState('THINKING');
        playbackSuppressedRef.current = false;
      } else if (msg.type === 'AgentStartedSpeaking') {
        updateState('SPEAKING');
        playbackSuppressedRef.current = false;
      } else if (msg.type === 'AgentAudioDone') {
        updateState('LISTENING');
        playbackSuppressedRef.current = false;
        setActiveTool(null);
      } else if (msg.type === 'LatencyReport') {
        if (msg.latency_ms) setLatencyMs(Math.round(msg.latency_ms));
      }
    },
    [appendFindingFromTool, appendTranscript, stopAllAudioPlayback, stopSession, updateState]
  );

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
    processorRef.current = audioContextRef.current.createScriptProcessor(1024, 1, 1);
    src.connect(processorRef.current);
    processorRef.current.connect(audioContextRef.current.destination);

    processorRef.current.onaudioprocess = (e) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

      const input = e.inputBuffer.getChannelData(0);
      const pcm16 = new Int16Array(input.length);
      let sumSq = 0.0;

      for (let i = 0; i < input.length; i++) {
        const s = Math.max(-1, Math.min(1, input[i]));
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        sumSq += s * s;
      }

      if (stateRef.current === 'USER_SPEAKING') {
        setAudioRMS(Math.min(1.0, Math.sqrt(sumSq / input.length) * 8.0));
      }

      wsRef.current.send(pcm16.buffer);
    };
  }, []);

  const startSession = useCallback(
    async (voiceModel: string) => {
      try {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        if (!playbackContextRef.current) {
          playbackContextRef.current = new AudioCtx({ sampleRate: 24000 });
        }
        if (playbackContextRef.current.state === 'suspended') {
          await playbackContextRef.current.resume();
        }
        nextPlayTimeRef.current = playbackContextRef.current.currentTime;
        playbackSuppressedRef.current = false;

        const res = await fetch('/api/voice/sessions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: 'web_user', persona: 'companion', voice_model: voiceModel }),
        });
        const data = await res.json();
        const sessionId = data.session_id;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/voice/ws/${sessionId}?user_id=web_user&voice=${encodeURIComponent(
          voiceModel
        )}`;

        const ws = new WebSocket(wsUrl);
        ws.binaryType = 'arraybuffer';
        wsRef.current = ws;

        ws.onopen = async () => {
          updateState('CONNECTED');
          await startMicrophone();
        };

        ws.onmessage = (e) => {
          if (e.data instanceof ArrayBuffer) {
            playSynthesizedAudio(e.data);
          } else {
            const msg = JSON.parse(e.data);
            handleControlMessage(msg);
          }
        };

        ws.onclose = () => {
          stopSession();
        };
        ws.onerror = (err) => {
          console.error('WS Error:', err);
          stopSession();
        };
      } catch (err) {
        alert('Voice Session Initialization Failed: ' + err);
        stopSession();
      }
    },
    [handleControlMessage, playSynthesizedAudio, startMicrophone, stopSession, updateState]
  );

  const injectTextMessage = useCallback(
    (text: string) => {
      if (text && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        stopAllAudioPlayback();
        playbackSuppressedRef.current = false;
        wsRef.current.send(JSON.stringify({ type: 'InjectUserMessage', content: text }));
        setCurrentSubtitle(`"${text}"`);
        appendTranscript('user', text);
      }
    },
    [appendTranscript, stopAllAudioPlayback]
  );

  const clearTranscripts = useCallback(() => {
    setTranscripts([]);
    setTurnsCount(0);
  }, []);

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
    startSession,
    stopSession,
    injectTextMessage,
    clearTranscripts,
  };
}

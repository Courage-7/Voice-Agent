import React, { useState } from 'react';
import { NeuralCanvas3D } from '@/components/3d/NeuralCanvas3D';
import { CyberNav } from '@/components/hud/CyberNav';
import { DialoguePod } from '@/components/hud/DialoguePod';
import { ControllerDeck } from '@/components/hud/ControllerDeck';
import { FindingsCanvas } from '@/components/findings/FindingsCanvas';
import { TranscriptsDrawer } from '@/components/drawers/TranscriptsDrawer';
import { useVoiceAgent } from '@/hooks/useVoiceAgent';
import { useConnectors } from '@/hooks/useConnectors';

export const App: React.FC = () => {
  const [selectedVoice, setSelectedVoice] = useState('aura-2-thalia-en');
  const [isTranscriptsOpen, setIsTranscriptsOpen] = useState(false);

  const {
    state,
    transcripts,
    findings,
    recentTools,
    currentSubtitle,
    latencyMs,
    turnsCount,
    audioRMS,
    startSession,
    stopSession,
    injectTextMessage,
    clearTranscripts,
  } = useVoiceAgent();

  const {
    connectors,
    connectApp,
  } = useConnectors();

  const handleToggleSession = () => {
    if (state === 'DISCONNECTED') {
      startSession(selectedVoice);
    } else {
      stopSession();
    }
  };

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-[#09090b] flex flex-col p-5 gap-4">
      {/* 1. Top Cyber Nav Bar */}
      <CyberNav
        state={state}
        latencyMs={latencyMs}
        turnsCount={turnsCount}
        onToggleTranscripts={() => setIsTranscriptsOpen((prev) => !prev)}
      />

      {/* 2. Main Dual-Zone Workspace */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-0">
        {/* Zone A: 3D Organic Liquid Audio Core & Voice Controls (Left 6 Cols) */}
        <section className="lg:col-span-6 flex flex-col justify-between relative shinra-card rounded-2xl p-6 overflow-hidden">
          {/* Subtle Ambient Background */}
          <div className="absolute inset-0 bg-gradient-to-b from-[#10B981]/5 to-transparent pointer-events-none" />

          {/* 3D Liquid Organic Orb Canvas */}
          <div className="flex-1 w-full min-h-[300px] flex items-center justify-center relative z-[1]">
            <NeuralCanvas3D state={state} audioRMS={audioRMS} />
          </div>

          {/* Floating Minimalist Speech Ribbon & Controller Deck */}
          <div className="relative z-[2] flex flex-col gap-3.5 mt-2">
            <DialoguePod
              state={state}
              subtitle={currentSubtitle}
              audioRMS={audioRMS}
            />

            <ControllerDeck
              state={state}
              selectedVoice={selectedVoice}
              onVoiceChange={setSelectedVoice}
              onToggleSession={handleToggleSession}
              onInjectText={injectTextMessage}
            />
          </div>
        </section>

        {/* Zone B: Dedicated Agent Findings & Intelligence Workspace (Right 6 Cols) */}
        <section className="lg:col-span-6 h-full min-h-0">
          <FindingsCanvas
            findings={findings}
            recentTools={recentTools}
            connectors={connectors}
            onConnectApp={connectApp}
          />
        </section>
      </main>

      {/* 3. Session Transcripts Log Drawer */}
      <TranscriptsDrawer
        isOpen={isTranscriptsOpen}
        onClose={() => setIsTranscriptsOpen(false)}
        transcripts={transcripts}
        onClear={clearTranscripts}
      />
    </div>
  );
};

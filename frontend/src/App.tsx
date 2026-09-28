import React, { lazy, Suspense, useState } from 'react';
import { Toaster, toast } from 'sonner';
import { CenteredHeader, ActivePageView } from './components/layout/CenteredHeader';
import { AppSidebarDrawer } from './components/layout/AppSidebarDrawer';
import { GatewayHeroPage } from './components/pages/GatewayHeroPage';
import { VoiceStudioPage } from './components/pages/VoiceStudioPage';
import { ConnectorsPage } from './components/pages/ConnectorsPage';
import { HistoryPage } from './components/pages/HistoryPage';
import { SkillsRegistryPage } from './components/pages/SkillsRegistryPage';
import { useVoiceAgent } from './hooks/useVoiceAgent';
import { useConnectors } from './hooks/useConnectors';
import { useConversations } from './hooks/useConversations';
import { LoginModal } from './components/auth/LoginModal';
import { useAuth } from './context/AuthContext';
import { RuntimeNotice } from './components/layout/RuntimeNotice';

const TranscriptsDrawer = lazy(() =>
  import('./components/drawers/TranscriptsDrawer').then(({ TranscriptsDrawer }) => ({ default: TranscriptsDrawer }))
);
const IntelligenceDrawer = lazy(() =>
  import('./components/drawers/IntelligenceDrawer').then(({ IntelligenceDrawer }) => ({ default: IntelligenceDrawer }))
);

export const App: React.FC = () => {
  const [activeView, setActiveView] = useState<ActivePageView>('hero');
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isTranscriptDrawerOpen, setIsTranscriptDrawerOpen] = useState(false);
  const [isActivityDrawerOpen, setIsActivityDrawerOpen] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState<string>('aura-2-thalia-en');
  const { isAuthenticated, openLoginModal } = useAuth();

  const {
    state,
    transcripts,
    findings,
    recentTools,
    currentSubtitle,
    activeTool,
    latencyMs,
    audioRMS,
    noiseProfile,
    isMicMuted,
    setNoiseProfile,
    toggleMicMute,
    startSession,
    stopSession,
    injectTextMessage,
    clearTranscripts,
  } = useVoiceAgent();

  const {
    connectors,
    loading: connectorsLoading,
    connectApp,
    disconnectApp,
    refreshConnectors,
  } = useConnectors();

  const {
    conversations,
    loading: historyLoading,
    activeConversation,
    selectedSessionId,
    selectConversation,
    deleteConversation,
  } = useConversations();

  const handleToggleSession = () => {
    if (state === 'DISCONNECTED') {
      if (!isAuthenticated) {
        toast.error('Authentication Required', {
          description: 'Please sign in with your email to start a live voice session.',
          action: {
            label: 'Sign In',
            onClick: () => openLoginModal(),
          },
        });
        openLoginModal();
        return;
      }
      startSession(selectedVoice);
      setActiveView('matrix');
    } else {
      stopSession();
    }
  };

  const handleEnterVoiceStudio = () => {
    if (state === 'DISCONNECTED') {
      if (!isAuthenticated) {
        toast.error('Authentication Required', {
          description: 'Please sign in with your email to enter the voice studio.',
          action: {
            label: 'Sign In',
            onClick: () => openLoginModal(),
          },
        });
        openLoginModal();
        return;
      }
      startSession(selectedVoice);
    }
    setActiveView('matrix');
  };

  const handleResumeSession = (sessionId: string) => {
    selectConversation(sessionId);
    setActiveView('matrix');
  };

  return (
    <div className="relative w-screen h-screen max-h-screen overflow-hidden bg-[var(--color-canvas)] text-[var(--color-ink)] flex flex-col font-['Manrope',sans-serif]">
      <RuntimeNotice />
      {/* 1. App Header */}
      <CenteredHeader
        state={state}
        latencyMs={latencyMs}
        activeView={activeView}
        connectorsCount={connectors.filter((c) => c.connected).length}
        historyCount={conversations.length}
        skillsCount={17}
        onNavigate={(view) => setActiveView(view)}
        onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
      />

      {/* 2. Main Page Views Stage */}
      <main className={`flex-1 w-full min-h-0 relative flex flex-col ${activeView === 'matrix' ? 'overflow-hidden' : 'overflow-y-auto'}`}>
        {activeView === 'hero' && (
          <GatewayHeroPage
            onEnterStudio={handleEnterVoiceStudio}
            onOpenConnectors={() => setActiveView('connectors')}
            onOpenSkills={() => setActiveView('skills')}
          />
        )}

        {activeView === 'matrix' && (
          <VoiceStudioPage
            state={state}
            audioRMS={audioRMS}
            subtitle={currentSubtitle}
            selectedVoice={selectedVoice}
            activeTool={activeTool}
            transcriptCount={transcripts.length}
            activityCount={findings.length + recentTools.length}
            transcripts={transcripts}
            findings={findings}
            recentTools={recentTools}
            noiseProfile={noiseProfile}
            isMicMuted={isMicMuted}
            onNoiseProfileChange={setNoiseProfile}
            onToggleMicMute={toggleMicMute}
            onVoiceChange={setSelectedVoice}
            onToggleSession={handleToggleSession}
            onInjectText={injectTextMessage}
            onOpenTranscripts={() => setIsTranscriptDrawerOpen(true)}
            onOpenActivity={() => setIsActivityDrawerOpen(true)}
            onClearTranscripts={clearTranscripts}
          />
        )}

        {activeView === 'connectors' && (
          <ConnectorsPage
            connectors={connectors}
            loading={connectorsLoading}
            onConnectApp={connectApp}
            onDisconnectApp={disconnectApp}
            onRefresh={refreshConnectors}
          />
        )}

        {activeView === 'history' && (
          <HistoryPage
            conversations={conversations}
            activeConversation={activeConversation}
            selectedSessionId={selectedSessionId}
            loading={historyLoading}
            onSelectSession={selectConversation}
            onDeleteSession={deleteConversation}
            onResumeSession={handleResumeSession}
          />
        )}

        {activeView === 'skills' && (
          <SkillsRegistryPage />
        )}
      </main>

      {/* 3. Slide-out Workspace Drawer (Skills, Connectors, History) */}
      <AppSidebarDrawer
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        conversations={conversations}
        connectors={connectors}
        onConnectApp={connectApp}
        onDisconnectApp={disconnectApp}
        onSelectConversation={selectConversation}
        onDeleteConversation={deleteConversation}
        onNavigatePage={(page) => setActiveView(page)}
      />

      {/* 4. Clerk-hosted email-code sign-in modal */}
      <LoginModal />

      <Suspense fallback={null}>
        {isTranscriptDrawerOpen && (
          <TranscriptsDrawer
            isOpen
            transcripts={transcripts}
            onClear={clearTranscripts}
            onClose={() => setIsTranscriptDrawerOpen(false)}
          />
        )}
        {isActivityDrawerOpen && (
          <IntelligenceDrawer
            isOpen
            findings={findings}
            recentTools={recentTools}
            connectors={connectors}
            onConnectApp={connectApp}
            onClose={() => setIsActivityDrawerOpen(false)}
          />
        )}
      </Suspense>

      {/* 5. Sonner Toast Notification Center */}
      <Toaster
        position="top-right"
        theme="light"
        richColors
        closeButton
        toastOptions={{
          style: {
            background: 'var(--color-surface)',
            border: '1px solid var(--color-hairline)',
            color: 'var(--color-ink)',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)',
          },
        }}
      />
    </div>
  );
};
export default App;

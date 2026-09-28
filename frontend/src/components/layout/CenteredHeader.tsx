import React from 'react';
import { 
  Mic, 
  Blocks, 
  Clock, 
  Wrench,
  User,
  LogOut,
  Menu,
  SlidersHorizontal
} from 'lucide-react';
import { SessionState } from '@/types';
import { ShinraLogo } from './ShinraLogo';
import { useAuth } from '@/context/AuthContext';

export type ActivePageView = 'hero' | 'matrix' | 'connectors' | 'history' | 'skills';

export interface CenteredHeaderProps {
  state: SessionState;
  latencyMs: number | null;
  activeView: ActivePageView;
  connectorsCount: number;
  historyCount: number;
  skillsCount?: number;
  onNavigate: (view: ActivePageView) => void;
  onToggleSidebar: () => void;
}

const STATE_CONFIG: Record<SessionState, { text: string; dot: string; bg: string; textCol: string; border: string }> = {
  DISCONNECTED: { 
    text: 'Ready', 
    dot: 'bg-[#9b978e]', 
    bg: 'bg-[#eeece7]/80', 
    textCol: 'text-[#45443f]', 
    border: 'border-[#dedbd3]' 
  },
  CONNECTED: { 
    text: 'Ready', 
    dot: 'bg-[#28734d]', 
    bg: 'bg-[#eef6f0]', 
    textCol: 'text-[#28734d]', 
    border: 'border-[#c7e3d0]' 
  },
  LISTENING: { 
    text: 'Listening', 
    dot: 'bg-[#b95740] animate-pulse', 
    bg: 'bg-[#fcf1ee]', 
    textCol: 'text-[#b95740]', 
    border: 'border-[#f2d0c7]' 
  },
  USER_SPEAKING: { 
    text: 'You are speaking', 
    dot: 'bg-[#b95740] animate-pulse', 
    bg: 'bg-[#fcf1ee]', 
    textCol: 'text-[#b95740]', 
    border: 'border-[#f2d0c7]' 
  },
  THINKING: { 
    text: 'Thinking', 
    dot: 'bg-[#94651f] animate-pulse', 
    bg: 'bg-[#fdf6ea]', 
    textCol: 'text-[#94651f]', 
    border: 'border-[#f2debe]' 
  },
  SPEAKING: { 
    text: 'Assistant speaking', 
    dot: 'bg-[#245d83]', 
    bg: 'bg-[#eef4f8]', 
    textCol: 'text-[#245d83]', 
    border: 'border-[#cce0ed]' 
  },
  MUTED: { 
    text: 'Muted', 
    dot: 'bg-[#b45309]', 
    bg: 'bg-[#fffbeb]', 
    textCol: 'text-[#92400e]', 
    border: 'border-[#fde68a]' 
  },
  ERROR: { 
    text: 'Offline', 
    dot: 'bg-[#a33e3e]', 
    bg: 'bg-[#fcf0f0]', 
    textCol: 'text-[#a33e3e]', 
    border: 'border-[#f3cece]' 
  },
};

export const CenteredHeader: React.FC<CenteredHeaderProps> = ({
  state,
  latencyMs,
  activeView,
  connectorsCount,
  historyCount,
  skillsCount = 17,
  onNavigate,
  onToggleSidebar,
}) => {
  const { user, isAuthenticated, openLoginModal, logout } = useAuth();
  const currentBadge = STATE_CONFIG[state] || STATE_CONFIG.DISCONNECTED;

  return (
    <header className="w-full h-16 bg-[var(--color-surface)] border-b border-[var(--color-hairline)] z-40 shrink-0 select-none">
      <div className="max-w-[1200px] w-full mx-auto h-full px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-4">
        
        {/* 1. Left: Product Name & Identity */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => onNavigate('hero')}
            className="flex items-center gap-2.5 cursor-pointer bg-transparent border-0 p-0 text-left group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)] rounded-md"
            title="Shinra home"
            aria-label="Shinra home"
          >
            <ShinraLogo size={26} />
            <div className="flex items-baseline gap-2">
              <span className="font-['DM_Serif_Display'] text-[21px] font-normal tracking-tight text-[var(--color-ink)] leading-none">
                Shinra
              </span>
              <span className="hidden sm:inline-block text-[11px] font-medium text-[var(--color-muted)] pl-2 border-l border-[var(--color-hairline)] leading-none">
                Voice assistant
              </span>
            </div>
          </button>
        </div>

        {/* 2. Center: Primary Navigation (Desktop & Tablet) */}
        <nav 
          className="hidden md:flex items-center gap-1 h-full"
          aria-label="Primary navigation"
        >
          <button
            onClick={() => onNavigate('matrix')}
            className={`relative h-full px-3.5 flex items-center gap-2 text-[13px] font-medium transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)] ${
              activeView === 'matrix'
                ? 'text-[var(--color-ink)] font-semibold after:absolute after:bottom-0 after:left-2 after:right-2 after:h-[2px] after:bg-[var(--color-action)]'
                : 'text-[var(--color-body)] hover:text-[var(--color-ink)] hover:bg-[var(--color-surface-muted)]/50'
            }`}
          >
            <Mic className="w-4 h-4 text-[var(--color-muted)]" />
            <span>Voice</span>
          </button>

          <button
            onClick={() => onNavigate('history')}
            className={`relative h-full px-3.5 flex items-center gap-2 text-[13px] font-medium transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)] ${
              activeView === 'history'
                ? 'text-[var(--color-ink)] font-semibold after:absolute after:bottom-0 after:left-2 after:right-2 after:h-[2px] after:bg-[var(--color-action)]'
                : 'text-[var(--color-body)] hover:text-[var(--color-ink)] hover:bg-[var(--color-surface-muted)]/50'
            }`}
          >
            <Clock className="w-4 h-4 text-[var(--color-muted)]" />
            <span>History</span>
            {historyCount > 0 && (
              <span className="text-[11px] font-mono text-[var(--color-muted)] font-normal">
                ({historyCount})
              </span>
            )}
          </button>

          <button
            onClick={() => onNavigate('connectors')}
            className={`relative h-full px-3.5 flex items-center gap-2 text-[13px] font-medium transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)] ${
              activeView === 'connectors'
                ? 'text-[var(--color-ink)] font-semibold after:absolute after:bottom-0 after:left-2 after:right-2 after:h-[2px] after:bg-[var(--color-action)]'
                : 'text-[var(--color-body)] hover:text-[var(--color-ink)] hover:bg-[var(--color-surface-muted)]/50'
            }`}
          >
            <Blocks className="w-4 h-4 text-[var(--color-muted)]" />
            <span>Connections</span>
            {connectorsCount > 0 && (
              <span className="text-[11px] font-mono text-[var(--color-muted)] font-normal">
                ({connectorsCount})
              </span>
            )}
          </button>

          <button
            onClick={() => onNavigate('skills')}
            className={`relative h-full px-3.5 flex items-center gap-2 text-[13px] font-medium transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)] ${
              activeView === 'skills'
                ? 'text-[var(--color-ink)] font-semibold after:absolute after:bottom-0 after:left-2 after:right-2 after:h-[2px] after:bg-[var(--color-action)]'
                : 'text-[var(--color-body)] hover:text-[var(--color-ink)] hover:bg-[var(--color-surface-muted)]/50'
            }`}
          >
            <Wrench className="w-4 h-4 text-[var(--color-muted)]" />
            <span>Skills</span>
            <span className="text-[11px] font-mono text-[var(--color-muted)] font-normal">
              ({skillsCount})
            </span>
          </button>
        </nav>

        {/* 3. Right: Honest Status, Account & Mobile Menu */}
        <div className="flex items-center gap-3 shrink-0">
          
          {/* Measured Latency (Only shown when an actual numeric measurement is available) */}
          {latencyMs !== null && (
            <div 
              className="hidden xl:inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono text-[var(--color-muted)] bg-[var(--color-surface-muted)] border border-[var(--color-hairline)]"
              title={`Network latency: ${latencyMs}ms`}
            >
              <span>{latencyMs}ms</span>
            </div>
          )}

          {/* Session State Badge */}
          <div 
            role="status"
            aria-live="polite"
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[12px] font-medium border ${currentBadge.bg} ${currentBadge.border} ${currentBadge.textCol}`}
          >
            <span className={`w-2 h-2 rounded-full ${currentBadge.dot}`} aria-hidden="true" />
            <span>{currentBadge.text}</span>
          </div>

          {/* Account Authentication Actions */}
          {isAuthenticated && user ? (
            <div className="flex items-center gap-2 pl-2 border-l border-[var(--color-hairline)]">
              <div 
                className="hidden lg:flex items-center gap-1.5 text-[12px] text-[var(--color-body)] font-mono max-w-[130px] truncate"
                title={user.email}
              >
                <User className="w-3.5 h-3.5 text-[var(--color-muted)] shrink-0" />
                <span className="truncate">{user.email.split('@')[0]}</span>
              </div>
              <button
                onClick={logout}
                title="Sign out"
                aria-label="Sign out"
                className="min-h-[36px] min-w-[36px] px-2 rounded-md hover:bg-[var(--color-surface-muted)] text-[var(--color-muted)] hover:text-[var(--color-danger)] flex items-center justify-center transition-colors cursor-pointer text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)]"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline ml-1">Sign out</span>
              </button>
            </div>
          ) : (
            <button
              onClick={openLoginModal}
              title="Sign in or create an account with email"
              aria-label="Sign in or create an account"
              className="min-h-[36px] px-3 py-1.5 rounded-md bg-[var(--color-action)] hover:bg-[var(--color-action-active)] text-[var(--color-on-action)] text-[12px] font-medium flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)]"
            >
              <User className="w-3.5 h-3.5" />
              <span>Sign in / sign up</span>
            </button>
          )}

          {/* Workspace Drawer Toggle (Desktop) */}
          <button
            onClick={onToggleSidebar}
            title="Open workspace panel"
            aria-label="Open workspace panel"
            className="hidden md:flex min-h-[36px] min-w-[36px] rounded-md border border-[var(--color-hairline)] hover:bg-[var(--color-surface-muted)] text-[var(--color-body)] hover:text-[var(--color-ink)] items-center justify-center transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)]"
          >
            <SlidersHorizontal className="w-4 h-4" />
          </button>

          {/* Mobile Menu Toggle (< 768px) */}
          <button
            onClick={onToggleSidebar}
            title="Open navigation menu"
            aria-label="Open navigation menu"
            className="md:hidden min-h-[44px] min-w-[44px] rounded-md border border-[var(--color-hairline)] hover:bg-[var(--color-surface-muted)] text-[var(--color-body)] hover:text-[var(--color-ink)] flex items-center justify-center transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)]"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>

      </div>
    </header>
  );
};

export default CenteredHeader;

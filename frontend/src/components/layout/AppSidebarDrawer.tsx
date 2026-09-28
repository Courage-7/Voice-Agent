import React, { useState } from 'react';
import { 
  X, 
  Clock, 
  Blocks, 
  Wrench, 
  Power, 
  ArrowUpRight, 
  Search, 
  ShieldCheck, 
  Trash2,
  MessageSquare,
  RefreshCw,
  Mic,
  Plus
} from 'lucide-react';
import { ConnectorApp } from '@/types';
import { AppBrandIcon } from '../connectors/AppBrandIcon';
import { SavedConversation } from '@/hooks/useConversations';
import { ActivePageView } from './CenteredHeader';

interface AppSidebarDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  conversations: SavedConversation[];
  connectors: ConnectorApp[];
  onConnectApp: (name: string) => void;
  onDisconnectApp: (id: string) => void;
  onSelectConversation: (sessionId: string) => void;
  onDeleteConversation: (sessionId: string) => void;
  onNavigatePage: (page: ActivePageView) => void;
}

type DrawerTab = 'history' | 'connectors' | 'skills';

const SAMPLE_SKILLS = [
  { name: 'search_web', category: 'Research', safe: true, desc: 'Live web intelligence and research' },
  { name: 'read_emails', category: 'Communication', safe: true, desc: 'Extract recent inbox threads and summaries' },
  { name: 'send_email', category: 'Communication', safe: false, desc: 'Draft and dispatch email (verbal confirmation required)' },
  { name: 'list_calendar_events', category: 'Scheduling', safe: true, desc: 'Inspect schedule and agenda conflicts' },
  { name: 'create_calendar_event', category: 'Scheduling', safe: false, desc: 'Book meetings (verbal confirmation required)' },
  { name: 'query_postgresql', category: 'Data & Database', safe: true, desc: 'Execute read-only SQL queries' },
  { name: 'github_create_pr', category: 'Developer', safe: false, desc: 'Submit pull request to active repository' },
  { name: 'save_memory', category: 'Memory', safe: true, desc: 'Store facts and preferences in long-term memory' },
  { name: 'search_memory', category: 'Memory', safe: true, desc: 'Semantic recall across past sessions' },
  { name: 'end_session', category: 'System', safe: true, desc: 'Gracefully terminate active voice dialogue' },
];

export const AppSidebarDrawer: React.FC<AppSidebarDrawerProps> = ({
  isOpen,
  onClose,
  conversations,
  connectors,
  onConnectApp,
  onDisconnectApp,
  onSelectConversation,
  onDeleteConversation,
  onNavigatePage,
}) => {
  const [activeTab, setActiveTab] = useState<DrawerTab>('history');
  const [searchQuery, setSearchQuery] = useState('');

  if (!isOpen) return null;

  const filteredConversations = conversations.filter((c) =>
    (c.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (c.preview || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredConnectors = connectors.filter((app) =>
    (app.display_name || app.name || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Calm Backdrop */}
      <div 
        onClick={onClose} 
        className="fixed inset-0 bg-black/25 transition-opacity" 
        aria-hidden="true"
      />

      {/* Slide-out Drawer Container */}
      <aside 
        role="dialog"
        aria-label="Workspace panel"
        className="relative w-full max-w-md h-full bg-[var(--color-surface)] border-l border-[var(--color-hairline)] shadow-xl flex flex-col z-10 animate-in slide-in-from-right duration-200"
      >
        {/* Drawer Header */}
        <div className="p-4 border-b border-[var(--color-hairline)] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-['DM_Serif_Display'] text-[18px] text-[var(--color-ink)]">
              Workspace
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                onClose();
                onNavigatePage(activeTab === 'history' ? 'history' : activeTab === 'connectors' ? 'connectors' : 'skills');
              }}
              title="Open full page"
              className="px-2.5 py-1 rounded-md text-[12px] font-medium text-[var(--color-link)] hover:bg-[var(--color-surface-muted)] transition-colors flex items-center gap-1 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)]"
            >
              <span>View full page</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={onClose}
              title="Close panel"
              aria-label="Close panel"
              className="w-8 h-8 rounded-md hover:bg-[var(--color-surface-muted)] text-[var(--color-muted)] hover:text-[var(--color-ink)] flex items-center justify-center transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)]"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Mobile Quick Action to jump to Voice workspace */}
        <div className="md:hidden px-4 py-2 border-b border-[var(--color-hairline)] bg-[var(--color-surface-muted)]/50 flex items-center justify-between">
          <span className="text-xs text-[var(--color-muted)]">Primary view:</span>
          <button
            onClick={() => {
              onClose();
              onNavigatePage('matrix');
            }}
            className="px-3 py-1 rounded-md bg-[var(--color-action)] text-[var(--color-on-action)] text-xs font-medium flex items-center gap-1.5 cursor-pointer"
          >
            <Mic className="w-3.5 h-3.5" />
            <span>Open voice workspace</span>
          </button>
        </div>

        {/* Tab Selector */}
        <div className="px-4 pt-2.5 pb-2 border-b border-[var(--color-hairline)] flex items-center gap-1 bg-[var(--color-surface-muted)]/40">
          <button
            onClick={() => setActiveTab('history')}
            className={`flex-1 py-1.5 rounded-md text-[12px] font-medium flex items-center justify-center gap-1.5 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)] ${
              activeTab === 'history'
                ? 'bg-[var(--color-surface)] text-[var(--color-ink)] font-semibold shadow-xs border border-[var(--color-hairline)]'
                : 'text-[var(--color-body)] hover:text-[var(--color-ink)]'
            }`}
          >
            <Clock className="w-3.5 h-3.5 text-[var(--color-muted)]" />
            <span>History</span>
          </button>

          <button
            onClick={() => setActiveTab('connectors')}
            className={`flex-1 py-1.5 rounded-md text-[12px] font-medium flex items-center justify-center gap-1.5 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)] ${
              activeTab === 'connectors'
                ? 'bg-[var(--color-surface)] text-[var(--color-ink)] font-semibold shadow-xs border border-[var(--color-hairline)]'
                : 'text-[var(--color-body)] hover:text-[var(--color-ink)]'
            }`}
          >
            <Blocks className="w-3.5 h-3.5 text-[var(--color-muted)]" />
            <span>Connections</span>
          </button>

          <button
            onClick={() => setActiveTab('skills')}
            className={`flex-1 py-1.5 rounded-md text-[12px] font-medium flex items-center justify-center gap-1.5 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)] ${
              activeTab === 'skills'
                ? 'bg-[var(--color-surface)] text-[var(--color-ink)] font-semibold shadow-xs border border-[var(--color-hairline)]'
                : 'text-[var(--color-body)] hover:text-[var(--color-ink)]'
            }`}
          >
            <Wrench className="w-3.5 h-3.5 text-[var(--color-muted)]" />
            <span>Skills</span>
          </button>
        </div>

        {/* Search Bar */}
        <div className="p-3 border-b border-[var(--color-hairline)]">
          <div className="flex items-center bg-[var(--color-surface-muted)]/60 rounded-md px-3 h-9 border border-[var(--color-hairline)]">
            <Search className="w-3.5 h-3.5 text-[var(--color-muted)] mr-2 flex-shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={`Filter ${activeTab}...`}
              className="w-full bg-transparent text-[13px] outline-none placeholder:text-[var(--color-muted)] text-[var(--color-ink)]"
            />
          </div>
        </div>

        {/* Tab 1: Conversation History */}
        {activeTab === 'history' && (
          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
            {filteredConversations.length === 0 ? (
              <div className="p-8 text-center text-[var(--color-muted)] text-[13px]">
                <MessageSquare className="w-7 h-7 mx-auto mb-2 text-[var(--color-faint)]" />
                <p>No saved conversations found.</p>
                <p className="text-[12px] mt-1 text-[var(--color-muted)]">Voice session transcripts will appear here.</p>
              </div>
            ) : (
              filteredConversations.map((conv) => (
                <div
                  key={conv.session_id}
                  onClick={() => {
                    onSelectConversation(conv.session_id);
                    onClose();
                    onNavigatePage('history');
                  }}
                  className="p-3 rounded-md border border-[var(--color-hairline)] hover:border-[var(--color-muted)] hover:bg-[var(--color-surface-muted)]/40 transition-colors cursor-pointer group flex flex-col gap-1 relative bg-[var(--color-surface)]"
                >
                  <div className="flex items-center justify-between">
                    <h4 className="text-[13px] font-semibold text-[var(--color-ink)] truncate pr-6">
                      {conv.title}
                    </h4>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversation(conv.session_id);
                      }}
                      title="Delete conversation"
                      aria-label="Delete conversation"
                      className="opacity-0 group-hover:opacity-100 p-1 text-[var(--color-muted)] hover:text-[var(--color-danger)] transition-opacity rounded"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <p className="text-[12px] text-[var(--color-body)] line-clamp-1">
                    {conv.preview || 'Voice session transcript'}
                  </p>
                  <div className="flex items-center gap-2 mt-1 text-[11px] font-mono text-[var(--color-muted)]">
                    <span>{new Date(conv.created_at).toLocaleDateString()}</span>
                    <span>·</span>
                    <span>{conv.turns} turns</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab 2: Connectors */}
        {activeTab === 'connectors' && (
          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
            <div className="p-3 rounded-md bg-[var(--color-surface-muted)]/60 border border-[var(--color-hairline)] mb-1 text-[12px] text-[var(--color-body)] leading-relaxed">
              Connect external services to allow the assistant to read and write on your behalf with verbal confirmation.
            </div>

            {filteredConnectors.map((app) => {
              return (
                <div
                  key={app.name}
                  className="p-3 rounded-md border border-[var(--color-hairline)] hover:border-[var(--color-muted)] transition-colors flex items-center justify-between gap-3 bg-[var(--color-surface)]"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-md bg-[var(--color-surface-muted)] border border-[var(--color-hairline)] flex items-center justify-center flex-shrink-0 p-1">
                      <AppBrandIcon name={app.name} logoUrl={app.logo_url} size={20} />
                    </div>
                    <div>
                      <div className="text-[13px] font-semibold text-[var(--color-ink)]">
                        {app.display_name || app.name}
                      </div>
                      <div className="text-[11px] text-[var(--color-muted)] font-mono">
                        {app.connected ? 'Connected' : app.authorizing ? 'Connecting...' : 'Not connected'}
                      </div>
                    </div>
                  </div>

                  {app.connected ? (
                    <button
                      onClick={() => onDisconnectApp(app.connection_id || app.name)}
                      className="px-2.5 py-1 rounded-md text-[12px] font-medium text-[var(--color-danger)] hover:bg-[#fcf0f0] border border-[#f3cece] flex items-center gap-1 cursor-pointer transition-colors"
                    >
                      <Power className="w-3 h-3 text-[var(--color-danger)]" />
                      <span>Disconnect</span>
                    </button>
                  ) : app.authorizing ? (
                    <div className="px-2.5 py-1 rounded-md text-[12px] font-medium text-[var(--color-warning)] bg-[#fdf6ea] border border-[#f2debe] flex items-center gap-1.5 animate-pulse">
                      <RefreshCw className="w-3 h-3 animate-spin text-[var(--color-warning)]" />
                      <span>Authenticating...</span>
                    </div>
                  ) : (
                    <button
                      onClick={() => onConnectApp(app.name)}
                      className="px-3 py-1 rounded-md bg-[var(--color-action)] hover:bg-[var(--color-action-active)] text-[var(--color-on-action)] text-[12px] font-medium flex items-center gap-1 cursor-pointer transition-colors shadow-xs"
                    >
                      <Plus className="w-3 h-3" />
                      <span>Connect</span>
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Tab 3: Skills */}
        {activeTab === 'skills' && (
          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
            <div className="p-3 rounded-md bg-[var(--color-surface-muted)]/60 border border-[var(--color-hairline)] mb-1 flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 text-[var(--color-success)] flex-shrink-0 mt-0.5" />
              <p className="text-[12px] text-[var(--color-body)] leading-relaxed">
                <strong>Verbal confirmation policy:</strong> Actions that modify data or send messages will always request your verbal confirmation before running.
              </p>
            </div>

            {SAMPLE_SKILLS.map((skill) => (
              <div
                key={skill.name}
                className="p-3 rounded-md border border-[var(--color-hairline)] flex flex-col gap-1 bg-[var(--color-surface)]"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[12px] font-mono font-medium text-[var(--color-ink)]">
                    {skill.name}
                  </span>
                  {skill.safe ? (
                    <span className="px-1.5 py-0.5 rounded text-[11px] font-medium bg-[#eef6f0] text-[var(--color-success)] border border-[#c7e3d0]">
                      Read only
                    </span>
                  ) : (
                    <span className="px-1.5 py-0.5 rounded text-[11px] font-medium bg-[#fdf6ea] text-[var(--color-warning)] border border-[#f2debe] flex items-center gap-1">
                      <ShieldCheck className="w-3 h-3 text-[var(--color-warning)]" />
                      <span>Confirmation required</span>
                    </span>
                  )}
                </div>
                <p className="text-[12px] text-[var(--color-muted)] leading-normal">
                  {skill.desc}
                </p>
              </div>
            ))}
          </div>
        )}
      </aside>
    </div>
  );
};

export default AppSidebarDrawer;

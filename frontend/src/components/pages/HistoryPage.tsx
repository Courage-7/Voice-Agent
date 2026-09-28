import React, { useState } from 'react';
import { 
  MessageSquare, 
  Trash2, 
  Search, 
  Download, 
  Mic, 
  Wrench, 
  ChevronDown, 
  ChevronUp, 
  X 
} from 'lucide-react';
import { SavedConversation, ConversationDetail } from '@/hooks/useConversations';
import { MessageRenderer } from '../chat';

export interface HistoryPageProps {
  conversations: SavedConversation[];
  activeConversation: ConversationDetail | null;
  selectedSessionId: string | null;
  loading?: boolean;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onResumeSession: (sessionId: string) => void;
}

export const HistoryPage: React.FC<HistoryPageProps> = ({
  conversations,
  activeConversation,
  selectedSessionId,
  loading,
  onSelectSession,
  onDeleteSession,
  onResumeSession,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedPayloads, setExpandedPayloads] = useState<Record<string, boolean>>({});

  const togglePayload = (key: string) => {
    setExpandedPayloads((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const filtered = conversations.filter((c) =>
    (c.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (c.preview || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleExportJSON = () => {
    if (!activeConversation) return;
    const blob = new Blob([JSON.stringify(activeConversation, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `voice-session-${activeConversation.session_id.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full max-w-[1200px] mx-auto flex-1 min-h-0 flex flex-col px-4 sm:px-6 lg:px-8 py-6 pb-24">
      
      {/* 1. Page Header: Left-Aligned Editorial Style */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-[var(--color-hairline)] shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="font-['DM_Serif_Display'] text-2xl sm:text-3xl text-[var(--color-ink)] leading-none">
              Recent conversations
            </h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono text-[var(--color-muted)] bg-[var(--color-surface-muted)] border border-[var(--color-hairline)]">
              {conversations.length} {conversations.length === 1 ? 'session' : 'sessions'}
            </span>
          </div>
          <p className="text-[14px] text-[var(--color-body)] leading-relaxed font-sans">
            Review past voice transcripts, user instructions, and completed service actions.
          </p>
        </div>

        {/* Action Controls for Selected Session */}
        {activeConversation && (
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleExportJSON}
              title="Download transcript JSON"
              aria-label="Download transcript JSON"
              className="h-9 px-3 rounded-md border border-[var(--color-hairline)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-muted)] text-[12px] text-[var(--color-body)] hover:text-[var(--color-ink)] font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Download className="w-3.5 h-3.5 text-[var(--color-muted)]" />
              <span>Export transcript</span>
            </button>

            <button
              onClick={() => onResumeSession(activeConversation.session_id)}
              className="h-9 px-3.5 rounded-md bg-[var(--color-action)] hover:bg-[var(--color-action-active)] text-white text-[12px] font-medium flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Resume session</span>
            </button>
          </div>
        )}
      </div>

      {/* 2. Dual-Pane Content: Left = Conversation List, Right = Transcript Inspector */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-4 pt-4 min-h-0 overflow-hidden">
        
        {/* Left Pane (5 cols on md/lg): Conversation List */}
        <div className="md:col-span-5 rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] flex flex-col min-h-0 overflow-hidden shadow-xs">
          
          {/* Search Field */}
          <div className="p-3 border-b border-[var(--color-hairline)] bg-[var(--color-surface-muted)]/30 shrink-0">
            <div className="relative flex items-center bg-[var(--color-surface)] border border-[var(--color-hairline)] rounded-md px-3 h-9 focus-within:border-[var(--color-focus)] transition-colors">
              <Search className="w-3.5 h-3.5 text-[var(--color-muted)] mr-2 shrink-0" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter conversations..."
                className="w-full bg-transparent text-[12.5px] text-[var(--color-ink)] outline-none placeholder:text-[var(--color-muted)]"
              />
              {searchQuery && (
                <button 
                  onClick={() => setSearchQuery('')}
                  aria-label="Clear filter"
                  className="p-0.5 text-[var(--color-muted)] hover:text-[var(--color-ink)]"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* List of Conversations */}
          <div className="flex-1 overflow-y-auto divide-y divide-[var(--color-hairline)]">
            {loading && (
              <div className="p-6 text-center text-[12px] text-[var(--color-muted)]">
                Loading conversations...
              </div>
            )}
            {filtered.length === 0 && !loading ? (
              <div className="p-8 text-center text-[var(--color-muted)]">
                <MessageSquare className="w-8 h-8 mx-auto mb-2 text-[var(--color-faint)]" />
                <p className="text-[13px] font-medium text-[var(--color-ink)]">No conversations found</p>
                <p className="text-[12px] text-[var(--color-muted)] mt-0.5">Start a voice session to save dialogue records.</p>
              </div>
            ) : (
              filtered.map((conv) => {
                const isSelected = selectedSessionId === conv.session_id;

                return (
                  <div
                    key={conv.session_id}
                    onClick={() => onSelectSession(conv.session_id)}
                    className={`p-3.5 flex flex-col gap-1 transition-colors cursor-pointer group relative ${
                      isSelected
                        ? 'bg-[var(--color-surface-muted)]/70'
                        : 'hover:bg-[var(--color-surface-muted)]/30'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-[13px] font-semibold text-[var(--color-ink)] truncate">
                        {conv.title}
                      </h3>

                      <div className="flex items-center gap-2 shrink-0">
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-medium bg-[#eef6f0] text-[var(--color-success)] border border-[#c7e3d0]">
                          Completed
                        </span>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteSession(conv.session_id);
                          }}
                          title="Delete conversation"
                          aria-label="Delete conversation"
                          className="opacity-0 group-hover:opacity-100 p-1 text-[var(--color-muted)] hover:text-[var(--color-danger)] transition-opacity rounded"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <p className="text-[12px] text-[var(--color-body)] line-clamp-1">
                      {conv.preview || 'Spoken session transcript'}
                    </p>

                    <div className="flex items-center gap-2 mt-1 text-[11px] font-mono text-[var(--color-muted)]">
                      <span>{new Date(conv.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}</span>
                      <span>·</span>
                      <span>{new Date(conv.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      <span>·</span>
                      <span>{conv.turns} {conv.turns === 1 ? 'turn' : 'turns'}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

        </div>

        {/* Right Pane (7 cols on md/lg): Selected Transcript Inspector */}
        <div className="md:col-span-7 rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] flex flex-col min-h-0 overflow-hidden shadow-xs">
          {activeConversation ? (
            <div className="flex-1 flex flex-col min-h-0">
              
              {/* Transcript Metadata Banner */}
              <div className="p-4 border-b border-[var(--color-hairline)] bg-[var(--color-surface-muted)]/30 shrink-0">
                <h2 className="text-[15px] font-semibold text-[var(--color-ink)] leading-snug">
                  {activeConversation.title}
                </h2>
                <div className="text-[11.5px] font-mono text-[var(--color-muted)] flex items-center gap-2 mt-1">
                  <span>{new Date(activeConversation.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span>
                  <span>·</span>
                  <span>{activeConversation.turns} turns</span>
                  <span>·</span>
                  <span className="text-[var(--color-faint)]">ID: {activeConversation.session_id.slice(0, 8)}</span>
                </div>
              </div>

              {/* Message Stream */}
              <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3.5">
                {(!activeConversation.messages || activeConversation.messages.length === 0) ? (
                  <div className="p-8 text-center text-[var(--color-muted)] text-[13px]">
                    No messages recorded for this session.
                  </div>
                ) : (
                  activeConversation.messages.map((msg, idx) => {
                    const isUser = msg.role === 'user' || msg.role === 'operator';
                    const toolCall = msg.tool_calls && msg.tool_calls.length > 0 ? msg.tool_calls[0] : null;
                    const payloadKey = `tool-${idx}`;
                    const isPayloadExpanded = Boolean(expandedPayloads[payloadKey]);

                    return (
                      <div
                        key={idx}
                        className={`flex flex-col gap-1 max-w-[88%] ${
                          isUser ? 'self-end items-end' : 'self-start items-start'
                        }`}
                      >
                        <div className="text-[11px] font-mono text-[var(--color-muted)] px-1">
                          {isUser ? 'You' : 'Assistant'}
                        </div>

                        <div
                          className={`p-3 rounded-lg text-[13.5px] leading-relaxed border ${
                            isUser
                              ? 'bg-[var(--color-surface-muted)] text-[var(--color-ink)] border-[var(--color-hairline)]'
                              : 'bg-white text-[var(--color-ink)] border-[var(--color-hairline)]'
                          }`}
                        >
                          {isUser ? (
                            <div className="whitespace-pre-wrap">{msg.content}</div>
                          ) : (
                            <MessageRenderer content={msg.content} />
                          )}
                        </div>

                        {/* Executed Tool Trace Callout */}
                        {toolCall && (
                          <div className="mt-1 w-full rounded-md border border-[var(--color-hairline)] bg-[var(--color-surface-muted)]/40 p-2.5 text-[12px]">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-1.5 text-[var(--color-ink)] font-medium">
                                <Wrench className="w-3.5 h-3.5 text-[var(--color-muted)]" />
                                <span>Tool executed: {toolCall.name || 'Workspace tool'}</span>
                              </div>
                              <button
                                onClick={() => togglePayload(payloadKey)}
                                className="text-[11px] text-[var(--color-link)] hover:underline flex items-center gap-0.5 cursor-pointer"
                              >
                                <span>{isPayloadExpanded ? 'Hide details' : 'Details'}</span>
                                {isPayloadExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                              </button>
                            </div>

                            {/* Details behind disclosure as requested by DESIGN.md */}
                            {isPayloadExpanded && (
                              <pre className="mt-2 p-2 rounded bg-[var(--color-surface)] border border-[var(--color-hairline)] font-mono text-[11px] text-[var(--color-body)] overflow-x-auto whitespace-pre-wrap">
                                {JSON.stringify(toolCall.parameters || toolCall.args || toolCall.input || toolCall, null, 2)}
                              </pre>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>

            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-[var(--color-muted)]">
              <MessageSquare className="w-9 h-9 text-[var(--color-faint)] mb-2" />
              <h3 className="text-[14px] font-medium text-[var(--color-ink)]">
                Select a conversation
              </h3>
              <p className="text-[12px] text-[var(--color-muted)] max-w-xs mt-1">
                Choose a session from the list on the left to read its dialogue transcript and executed tools.
              </p>
            </div>
          )}
        </div>

      </div>

    </div>
  );
};

export default HistoryPage;

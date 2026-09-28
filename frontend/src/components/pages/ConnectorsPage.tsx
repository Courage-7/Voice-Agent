import React, { useState, useMemo } from 'react';
import { 
  Search, 
  X, 
  RefreshCw, 
  Power, 
  ChevronDown, 
  ChevronUp, 
  ToggleLeft, 
  ToggleRight,
  Plus
} from 'lucide-react';
import { ConnectorApp } from '@/types';
import { AppBrandIcon } from '../connectors/AppBrandIcon';

interface ConnectorsPageProps {
  connectors: ConnectorApp[];
  loading: boolean;
  onConnectApp: (name: string) => void;
  onDisconnectApp: (connectionId: string) => void;
  onRefresh: () => void;
}

const APP_METADATA: Record<string, {
  badge: string;
  availableTools: Array<{ id: string; name: string; desc: string; defaultEnabled: boolean; mutating?: boolean }>;
}> = {
  GITHUB: {
    badge: 'Developer',
    availableTools: [
      { id: 'github_create_pr', name: 'Create pull request', desc: 'Push branches and create review PRs', defaultEnabled: true, mutating: true },
      { id: 'github_search_issues', name: 'Search issues & PRs', desc: 'Query active issue backlog', defaultEnabled: true },
      { id: 'github_read_repo', name: 'Inspect codebase', desc: 'Read code files across repositories', defaultEnabled: true },
    ],
  },
  SLACK: {
    badge: 'Communication',
    availableTools: [
      { id: 'slack_send_message', name: 'Send channel message', desc: 'Post updates to authorized channels', defaultEnabled: true, mutating: true },
      { id: 'slack_search_threads', name: 'Search threads', desc: 'Locate conversations and discussions', defaultEnabled: true },
    ],
  },
  GMAIL: {
    badge: 'Communication',
    availableTools: [
      { id: 'gmail_search_emails', name: 'Search messages', desc: 'Filter emails by sender, subject, date', defaultEnabled: true },
      { id: 'gmail_send_draft', name: 'Send email / reply', desc: 'Dispatch verified email responses', defaultEnabled: false, mutating: true },
    ],
  },
  GOOGLECALENDAR: {
    badge: 'Productivity',
    availableTools: [
      { id: 'cal_list_events', name: 'Check schedule', desc: 'Retrieve upcoming agenda & meetings', defaultEnabled: true },
      { id: 'cal_create_event', name: 'Schedule meeting', desc: 'Book appointments with attendees', defaultEnabled: false, mutating: true },
    ],
  },
  NOTION: {
    badge: 'Productivity',
    availableTools: [
      { id: 'notion_query_database', name: 'Query database', desc: 'Filter tables and property rows', defaultEnabled: true },
      { id: 'notion_append_block', name: 'Append notes', desc: 'Add summary bullets to active pages', defaultEnabled: true, mutating: true },
    ],
  },
  LINEAR: {
    badge: 'Developer',
    availableTools: [
      { id: 'linear_create_issue', name: 'Create issue', desc: 'Log task in team backlog', defaultEnabled: true, mutating: true },
      { id: 'linear_search_backlog', name: 'Search backlog', desc: 'Check priority sprint items', defaultEnabled: true },
    ],
  },
  POSTGRESQL: {
    badge: 'Data & database',
    availableTools: [
      { id: 'pg_execute_query', name: 'Read-only SQL query', desc: 'Run SELECT queries against authorized schema', defaultEnabled: true },
      { id: 'pg_schema_inspect', name: 'Inspect table schemas', desc: 'List columns and datatypes', defaultEnabled: true },
    ],
  },
  STRIPE: {
    badge: 'Data & finance',
    availableTools: [
      { id: 'stripe_get_subscription', name: 'Query subscriptions', desc: 'Check customer billing status', defaultEnabled: true },
      { id: 'stripe_invoice_summary', name: 'Invoice summary', desc: 'Summarize monthly statements', defaultEnabled: true },
    ],
  },
  SERPAPI: {
    badge: 'Search API',
    availableTools: [
      { id: 'serp_google_search', name: 'Web search', desc: 'Extract factual web snippets and links', defaultEnabled: true },
    ],
  },
  PERPLEXITYAI: {
    badge: 'Search API',
    availableTools: [
      { id: 'perplexity_deep_search', name: 'Research synthesis', desc: 'Synthesize web queries with citations', defaultEnabled: true },
    ],
  },
  TAVILY: {
    badge: 'Search API',
    availableTools: [
      { id: 'tavily_web_search', name: 'Factual search', desc: 'Real-time factual web search', defaultEnabled: true },
      { id: 'tavily_extract_page', name: 'Extract web page', desc: 'Parse content from web URLs', defaultEnabled: true },
    ],
  },
  GOOGLESHEETS: {
    badge: 'Productivity',
    availableTools: [
      { id: 'sheets_read_rows', name: 'Read spreadsheet rows', desc: 'Parse worksheet tables', defaultEnabled: true },
      { id: 'sheets_append_row', name: 'Append row', desc: 'Add new entry to sheet', defaultEnabled: true, mutating: true },
    ],
  },
  GOOGLEDRIVE: {
    badge: 'Productivity',
    availableTools: [
      { id: 'drive_search_files', name: 'Search files', desc: 'Find documents by title and content', defaultEnabled: true },
    ],
  },
  TALLY: {
    badge: 'Productivity',
    availableTools: [
      { id: 'tally_get_form', name: 'Inspect forms', desc: 'Retrieve form schema and fields', defaultEnabled: true },
      { id: 'tally_list_submissions', name: 'List submissions', desc: 'Fetch lead responses & surveys', defaultEnabled: true },
    ],
  },
  WHATSAPP: {
    badge: 'Communication',
    availableTools: [
      { id: 'whatsapp_send_message', name: 'Send message', desc: 'Send chat update', defaultEnabled: true, mutating: true },
    ],
  },
  TELEGRAM: {
    badge: 'Communication',
    availableTools: [
      { id: 'telegram_send_message', name: 'Send message', desc: 'Broadcast update to channel', defaultEnabled: true, mutating: true },
    ],
  },
  MICROSOFT_TEAMS: {
    badge: 'Communication',
    availableTools: [
      { id: 'teams_send_chat', name: 'Send chat message', desc: 'Post message to channel', defaultEnabled: true, mutating: true },
    ],
  },
  LINKEDIN: {
    badge: 'Communication',
    availableTools: [
      { id: 'linkedin_post_update', name: 'Share update', desc: 'Publish professional post', defaultEnabled: false, mutating: true },
      { id: 'linkedin_get_profile', name: 'Inspect profile', desc: 'Fetch verified member profile', defaultEnabled: true },
    ],
  },
  NEON: {
    badge: 'Data & database',
    availableTools: [
      { id: 'neon_list_projects', name: 'List serverless projects', desc: 'Retrieve Postgres branches & endpoints', defaultEnabled: true },
    ],
  },
  I_LOVE_PDF: {
    badge: 'Productivity',
    availableTools: [
      { id: 'ilovepdf_process', name: 'Process PDF', desc: 'Compress, merge, and convert documents', defaultEnabled: true },
    ],
  },
  GOOGLEDOCS: {
    badge: 'Productivity',
    availableTools: [
      { id: 'docs_read_document', name: 'Read Google Doc', desc: 'Extract full text and document body', defaultEnabled: true },
      { id: 'docs_create_doc', name: 'Create document', desc: 'Generate new document in Drive', defaultEnabled: false, mutating: true },
    ],
  },
  OUTLOOK: {
    badge: 'Communication',
    availableTools: [
      { id: 'outlook_get_emails', name: 'Read inbox', desc: 'Search and read Microsoft emails', defaultEnabled: true },
      { id: 'outlook_send_mail', name: 'Send email', desc: 'Dispatch verified email from Outlook', defaultEnabled: false, mutating: true },
    ],
  },
};

export const ConnectorsPage: React.FC<ConnectorsPageProps> = ({
  connectors,
  loading,
  onConnectApp,
  onDisconnectApp,
  onRefresh,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});
  const [toolToggles, setToolToggles] = useState<Record<string, boolean>>({});

  const toggleRowExpanded = (appName: string) => {
    setExpandedRows((prev) => ({
      ...prev,
      [appName]: !prev[appName],
    }));
  };

  const toggleTool = (toolId: string) => {
    setToolToggles((prev) => ({
      ...prev,
      [toolId]: prev[toolId] !== undefined ? !prev[toolId] : false,
    }));
  };

  const filteredConnectors = useMemo(() => {
    return connectors.filter((app) => {
      const query = searchQuery.toLowerCase();
      const matchesSearch =
        (app.display_name || app.name || '').toLowerCase().includes(query) ||
        (app.description || '').toLowerCase().includes(query);

      if (!matchesSearch) return false;

      if (selectedCategory === 'ALL') return true;
      if (selectedCategory === 'CONNECTED') return app.connected;
      if (selectedCategory === 'DEVELOPER') return app.capability === 'developer';
      if (selectedCategory === 'COMMUNICATION') return app.capability === 'communication';
      if (selectedCategory === 'PRODUCTIVITY') return app.capability === 'productivity';
      if (selectedCategory === 'SEARCH') return app.capability === 'search';
      if (selectedCategory === 'DATA') return app.capability === 'database';
      return true;
    });
  }, [connectors, searchQuery, selectedCategory]);

  const connectedCount = useMemo(() => connectors.filter((c) => c.connected).length, [connectors]);

  return (
    <div className="w-full max-w-[1200px] mx-auto shrink-0 px-4 sm:px-6 lg:px-8 py-6 pb-12">
      
      {/* 1. Header: Left-Aligned Editorial Title & Honest Status */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-6 border-b border-[var(--color-hairline)]">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <h1 className="font-['DM_Serif_Display'] text-2xl sm:text-3xl text-[var(--color-ink)] leading-none">
              Connections
            </h1>
            <span className="px-2.5 py-0.5 rounded text-[12px] font-mono text-[var(--color-muted)] bg-[var(--color-surface-muted)] border border-[var(--color-hairline)]">
              {connectedCount} of {connectors.length} active
            </span>
          </div>
          <p className="text-[14px] text-[var(--color-body)] max-w-2xl leading-relaxed font-sans">
            Manage external service integrations used by the voice assistant. Mutating actions require explicit verbal confirmation before running.
          </p>
        </div>

        {/* Refresh Action */}
        <button
          onClick={onRefresh}
          title="Refresh connection states"
          aria-label="Refresh connection states"
          className="h-9 px-3.5 rounded-md border border-[var(--color-hairline)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-muted)] text-[12px] text-[var(--color-body)] hover:text-[var(--color-ink)] font-medium flex items-center gap-2 transition-colors cursor-pointer shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)]"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[var(--color-action)]' : 'text-[var(--color-muted)]'}`} />
          <span>Refresh status</span>
        </button>
      </div>

      {/* 2. Filter Tabs & Search Controls */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 py-4">
        
        {/* Category Filters in Sentence Case */}
        <div className="flex items-center flex-wrap gap-1.5">
          {[
            { id: 'ALL', label: `All (${connectors.length})` },
            { id: 'CONNECTED', label: `Connected (${connectedCount})` },
            { id: 'COMMUNICATION', label: 'Communication' },
            { id: 'PRODUCTIVITY', label: 'Productivity' },
            { id: 'DEVELOPER', label: 'Developer' },
            { id: 'SEARCH', label: 'Search & research' },
            { id: 'DATA', label: 'Database' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedCategory(tab.id)}
              className={`px-3 py-1.5 rounded-md text-[12px] font-medium transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)] ${
                selectedCategory === tab.id
                  ? 'bg-[var(--color-surface-dark)] text-white'
                  : 'bg-[var(--color-surface)] text-[var(--color-body)] hover:text-[var(--color-ink)] hover:bg-[var(--color-surface-muted)] border border-[var(--color-hairline)]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search Field */}
        <div className="relative flex items-center bg-[var(--color-surface)] border border-[var(--color-hairline)] rounded-md px-3 h-9 sm:w-64 focus-within:border-[var(--color-focus)] transition-colors">
          <Search className="w-3.5 h-3.5 text-[var(--color-muted)] mr-2 shrink-0" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter services..."
            className="w-full bg-transparent text-[13px] text-[var(--color-ink)] outline-none placeholder:text-[var(--color-muted)]"
          />
          {searchQuery && (
            <button 
              onClick={() => setSearchQuery('')}
              aria-label="Clear search"
              className="p-1 text-[var(--color-muted)] hover:text-[var(--color-ink)]"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* 3. Practical Account List Table */}
      <div className="rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] overflow-hidden shadow-xs mb-8">
        
        {/* Table Header Row */}
        <div className="hidden md:grid grid-cols-12 gap-4 px-4 py-2.5 bg-[var(--color-surface-muted)]/50 border-b border-[var(--color-hairline)] text-[11px] font-medium text-[var(--color-muted)] uppercase tracking-wider">
          <div className="col-span-4">Service</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-4">Scope & tools</div>
          <div className="col-span-2 text-right">Action</div>
        </div>

        {/* Account Rows */}
        <div className="divide-y divide-[var(--color-hairline)]">
          {filteredConnectors.length === 0 ? (
            <div className="p-8 text-center text-[var(--color-muted)] text-[13px]">
              No services match the current filter.
            </div>
          ) : (
            filteredConnectors.map((app) => {
              const appKey = (app.name || '').toUpperCase();
              const meta = APP_METADATA[appKey] || {
                badge: app.capability || 'Tool',
                availableTools: [
                  { id: `${app.name}_default_action`, name: 'Workspace action', desc: 'Autonomous execution hook', defaultEnabled: true },
                ],
              };

              const isConnected = Boolean(app.connected);
              const isAuthorizing = Boolean(app.authorizing);
              const isExpanded = Boolean(expandedRows[app.name]);

              // Plain-language connection status
              let statusLabel = 'Not connected';
              let statusClass = 'bg-[var(--color-surface-muted)] text-[var(--color-muted)] border-[var(--color-hairline)]';
              let dotClass = 'bg-[var(--color-faint)]';

              if (isAuthorizing) {
                statusLabel = 'Checking connection';
                statusClass = 'bg-[#fdf6ea] text-[var(--color-warning)] border-[#f2debe]';
                dotClass = 'bg-[var(--color-warning)] animate-spin';
              } else if (app.status === 'NEEDS_RECONNECT') {
                statusLabel = 'Needs reconnecting';
                statusClass = 'bg-[#fdf6ea] text-[var(--color-warning)] border-[#f2debe]';
                dotClass = 'bg-[var(--color-warning)]';
              } else if (app.status === 'ERROR') {
                statusLabel = 'Connection failed';
                statusClass = 'bg-[#fcf0f0] text-[var(--color-danger)] border-[#f3cece]';
                dotClass = 'bg-[var(--color-danger)]';
              } else if (isConnected) {
                statusLabel = 'Connected';
                statusClass = 'bg-[#eef6f0] text-[var(--color-success)] border-[#c7e3d0]';
                dotClass = 'bg-[var(--color-success)]';
              }

              return (
                <div key={app.name} className="flex flex-col">
                  
                  {/* Primary Row Content */}
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-3 md:gap-4 p-4 items-center hover:bg-[var(--color-surface-muted)]/20 transition-colors">
                    
                    {/* Col 1: Service Brand Icon & Name (4 cols) */}
                    <div className="md:col-span-4 flex items-center gap-3">
                      <div className="w-9 h-9 rounded-md bg-[var(--color-surface-muted)] border border-[var(--color-hairline)] flex items-center justify-center p-1.5 shrink-0">
                        <AppBrandIcon name={app.name} logoUrl={app.logo_url} size={20} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[14px] font-semibold text-[var(--color-ink)] leading-snug">
                            {app.display_name || app.name}
                          </span>
                          {(meta.badge === 'Search API' || app.capability === 'search') && (
                            <span className="px-1.5 py-0.2 rounded text-[10px] font-mono text-[var(--color-muted)] bg-[var(--color-surface-muted)] border border-[var(--color-hairline)]">
                              API Key
                            </span>
                          )}
                        </div>
                        <div className="text-[12px] text-[var(--color-muted)] font-sans line-clamp-1">
                          {app.description || `${meta.badge} service integration`}
                        </div>
                      </div>
                    </div>

                    {/* Col 2: Plain Language Status (2 cols) */}
                    <div className="md:col-span-2 flex items-center">
                      <span 
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11.5px] font-medium border ${statusClass}`}
                        title={app.status === 'ERROR' ? 'Check API key in backend environment (.env) or Composio configuration' : undefined}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${dotClass}`} aria-hidden="true" />
                        <span>{statusLabel}</span>
                      </span>
                    </div>

                    {/* Col 3: Scope & Tools Toggle Trigger (4 cols) */}
                    <div className="md:col-span-4 flex items-center gap-2">
                      <span className="text-[12px] font-mono text-[var(--color-muted)]">
                        {meta.availableTools.length} {meta.availableTools.length === 1 ? 'action' : 'actions'}
                      </span>
                      <button
                        onClick={() => toggleRowExpanded(app.name)}
                        className="text-[11.5px] text-[var(--color-link)] hover:underline flex items-center gap-0.5 cursor-pointer"
                        title="View enabled tool details"
                      >
                        <span>{isExpanded ? 'Hide tools' : 'View tools'}</span>
                        {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      </button>
                    </div>

                    {/* Col 4: Action Button (2 cols) */}
                    <div className="md:col-span-2 flex justify-start md:justify-end">
                      {isConnected ? (
                        <button
                          onClick={() => onDisconnectApp(app.connection_id || app.name)}
                          className="min-h-[36px] px-3 py-1 rounded-md text-[12px] font-medium text-[var(--color-danger)] hover:bg-[#fcf0f0] border border-[#f3cece] flex items-center gap-1.5 cursor-pointer transition-colors"
                        >
                          <Power className="w-3.5 h-3.5 text-[var(--color-danger)]" />
                          <span>Disconnect</span>
                        </button>
                      ) : isAuthorizing ? (
                        <span className="min-h-[36px] px-3 py-1 rounded-md bg-[#fdf6ea] text-[var(--color-warning)] border border-[#f2debe] text-[12px] font-medium flex items-center gap-1.5">
                          <RefreshCw className="w-3 h-3 animate-spin text-[var(--color-warning)]" />
                          <span>Authorizing...</span>
                        </span>
                      ) : (
                        <button
                          onClick={() => onConnectApp(app.name)}
                          className="min-h-[36px] px-3.5 py-1 rounded-md bg-[var(--color-action)] hover:bg-[var(--color-action-active)] text-white text-[12px] font-medium flex items-center gap-1.5 cursor-pointer transition-colors shadow-xs"
                        >
                          <Plus className="w-3.5 h-3.5" />
                          <span>Connect</span>
                        </button>
                      )}
                    </div>

                  </div>

                  {/* Expandable Tool Drawer for this connection */}
                  {isExpanded && (
                    <div className="px-4 py-3 bg-[var(--color-surface-muted)]/40 border-t border-[var(--color-hairline)] flex flex-col gap-2">
                      <div className="text-[11px] font-semibold text-[var(--color-ink)] uppercase tracking-wider mb-0.5">
                        Available actions for {app.display_name || app.name}
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {meta.availableTools.map((tool) => {
                          const isEnabled = toolToggles[tool.id] ?? tool.defaultEnabled;

                          return (
                            <div
                              key={tool.id}
                              className="p-2.5 rounded-md border border-[var(--color-hairline)] bg-[var(--color-surface)] flex items-center justify-between gap-2"
                            >
                              <div className="pr-2 min-w-0">
                                <div className="flex items-center gap-1.5">
                                  <span className="text-[12px] font-medium text-[var(--color-ink)] truncate">
                                    {tool.name}
                                  </span>
                                  {tool.mutating && (
                                    <span className="px-1.5 py-0.2 rounded text-[9.5px] font-medium bg-[#fdf6ea] text-[var(--color-warning)] border border-[#f2debe]">
                                      Approval required
                                    </span>
                                  )}
                                </div>
                                <p className="text-[11px] text-[var(--color-muted)] leading-tight line-clamp-1 mt-0.5">
                                  {tool.desc}
                                </p>
                              </div>

                              {isConnected ? (
                                <button
                                  onClick={() => toggleTool(tool.id)}
                                  className="cursor-pointer text-[var(--color-muted)] hover:text-[var(--color-ink)] shrink-0"
                                  title={isEnabled ? 'Disable action' : 'Enable action'}
                                  aria-label={isEnabled ? `Disable ${tool.name}` : `Enable ${tool.name}`}
                                >
                                  {isEnabled ? (
                                    <ToggleRight className="w-5 h-5 text-[var(--color-success)]" />
                                  ) : (
                                    <ToggleLeft className="w-5 h-5 text-[var(--color-faint)]" />
                                  )}
                                </button>
                              ) : (
                                <span className="text-[10px] font-mono text-[var(--color-muted)] shrink-0">
                                  Not connected
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                </div>
              );
            })
          )}
        </div>
      </div>

    </div>
  );
};

export default ConnectorsPage;

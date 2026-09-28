import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Search, 
  Lock, 
  Code,
  X
} from 'lucide-react';

interface ToolSchema {
  name: string;
  description: string;
  parameters?: Record<string, any>;
  category?: string;
  is_destructive?: boolean;
}

const REGISTERED_TOOLS_CATALOG: ToolSchema[] = [
  {
    name: 'search_web',
    description: 'Execute live real-time web intelligence queries via SerpApi and Perplexity AI.',
    category: 'Research',
    is_destructive: false,
    parameters: { query: 'string (required)', max_results: 'number' },
  },
  {
    name: 'read_emails',
    description: 'Search and inspect email threads from connected Gmail or Outlook inboxes.',
    category: 'Communication',
    is_destructive: false,
    parameters: { query: 'string', limit: 'number' },
  },
  {
    name: 'send_email',
    description: 'Dispatch an email to specified recipients. Requires verbal confirmation.',
    category: 'Communication',
    is_destructive: true,
    parameters: { recipient: 'string (required)', subject: 'string', body: 'string' },
  },
  {
    name: 'list_calendar_events',
    description: 'Query upcoming calendar meetings and scheduling conflicts across Google Calendar.',
    category: 'Scheduling',
    is_destructive: false,
    parameters: { time_min: 'ISO timestamp', time_max: 'ISO timestamp' },
  },
  {
    name: 'create_calendar_event',
    description: 'Schedule a new calendar appointment with title and attendees. Requires verbal confirmation.',
    category: 'Scheduling',
    is_destructive: true,
    parameters: { title: 'string (required)', start_time: 'ISO timestamp', attendees: 'array of emails' },
  },
  {
    name: 'query_postgresql',
    description: 'Execute read-only SQL queries against connected enterprise PostgreSQL database.',
    category: 'Developer',
    is_destructive: false,
    parameters: { query: 'SQL SELECT query string' },
  },
  {
    name: 'github_create_pr',
    description: 'Open a GitHub pull request with title and branch reference. Requires verbal confirmation.',
    category: 'Developer',
    is_destructive: true,
    parameters: { title: 'string', branch: 'string', body: 'string' },
  },
  {
    name: 'sheets_read_rows',
    description: 'Extract rows and columnar cells from authorized Google Sheets worksheets.',
    category: 'Workspace',
    is_destructive: false,
    parameters: { spreadsheet_id: 'string', range: 'string' },
  },
  {
    name: 'sheets_append_row',
    description: 'Append a new row of data to the active spreadsheet. Requires verbal confirmation.',
    category: 'Workspace',
    is_destructive: true,
    parameters: { spreadsheet_id: 'string', values: 'array of values' },
  },
  {
    name: 'save_memory',
    description: 'Store contextual facts, user preferences, and operator traits in long-term memory.',
    category: 'Memory',
    is_destructive: false,
    parameters: { key: 'string', value: 'any', category: 'string' },
  },
  {
    name: 'search_memory',
    description: 'Semantic vector similarity recall across past sessions and stored preferences.',
    category: 'Memory',
    is_destructive: false,
    parameters: { query: 'string (required)', top_k: 'number' },
  },
  {
    name: 'end_session',
    description: 'Gracefully disconnect the active full-duplex voice stream and finalize transcripts.',
    category: 'System',
    is_destructive: false,
    parameters: {},
  },
];

export const SkillsRegistryPage: React.FC = () => {
  const [tools, setTools] = useState<ToolSchema[]>(REGISTERED_TOOLS_CATALOG);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [selectedTool, setSelectedTool] = useState<ToolSchema | null>(REGISTERED_TOOLS_CATALOG[0]);

  useEffect(() => {
    fetch('/api/tools')
      .then((res) => res.json())
      .then((data) => {
        if (data.tools && data.tools.length > 0) {
          const apiTools: ToolSchema[] = data.tools.map((t: any) => ({
            name: t.name,
            description: t.description,
            parameters: t.parameters?.properties || {},
            category: t.name.includes('email') ? 'Communication' : t.name.includes('calendar') ? 'Scheduling' : t.name.includes('memory') ? 'Memory' : 'Workspace',
            is_destructive: t.name.includes('send') || t.name.includes('create') || t.name.includes('append'),
          }));
          setTools(apiTools);
        }
      })
      .catch(() => {});
  }, []);

  const filtered = tools.filter((tool) => {
    const q = searchQuery.toLowerCase();
    const match = tool.name.toLowerCase().includes(q) || tool.description.toLowerCase().includes(q);
    if (!match) return false;
    if (selectedCategory === 'ALL') return true;
    if (selectedCategory === 'SAFE') return !tool.is_destructive;
    if (selectedCategory === 'MUTABLE') return tool.is_destructive;
    return tool.category?.toUpperCase() === selectedCategory;
  });

  return (
    <div className="w-full max-w-[1200px] mx-auto flex-1 min-h-0 flex flex-col px-4 sm:px-6 lg:px-8 py-6 pb-24">
      
      {/* 1. Page Header: Left-Aligned Editorial Style */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-[var(--color-hairline)] shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="font-['DM_Serif_Display'] text-2xl sm:text-3xl text-[var(--color-ink)] leading-none">
              Skills & tool safety
            </h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono text-[var(--color-muted)] bg-[var(--color-surface-muted)] border border-[var(--color-hairline)]">
              {tools.length} actions registered
            </span>
          </div>
          <p className="text-[14px] text-[var(--color-body)] leading-relaxed font-sans">
            Autonomous tools accessible to the assistant during voice sessions. Mutating actions require verbal approval.
          </p>
        </div>

        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#eef6f0] border border-[#c7e3d0] text-[var(--color-success)] text-[12px] font-medium shrink-0">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Verbal confirmation policy active</span>
        </div>
      </div>

      {/* 2. Dual-Pane Architecture: Left = Tool List, Right = Schema & Policy */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-4 pt-4 min-h-0 overflow-hidden">
        
        {/* Left Pane (5 cols): Tools Directory */}
        <div className="md:col-span-5 rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] flex flex-col min-h-0 overflow-hidden shadow-xs">
          
          {/* Search & Category Filter */}
          <div className="p-3 border-b border-[var(--color-hairline)] bg-[var(--color-surface-muted)]/30 flex flex-col gap-2 shrink-0">
            <div className="relative flex items-center bg-[var(--color-surface)] border border-[var(--color-hairline)] rounded-md px-3 h-9 focus-within:border-[var(--color-focus)] transition-colors">
              <Search className="w-3.5 h-3.5 text-[var(--color-muted)] mr-2 shrink-0" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter tools..."
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

            <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
              {[
                { id: 'ALL', label: `All (${tools.length})` },
                { id: 'SAFE', label: 'Read-only' },
                { id: 'MUTABLE', label: 'Requires approval' }
              ].map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors cursor-pointer ${
                    selectedCategory === cat.id
                      ? 'bg-[var(--color-surface-dark)] text-white'
                      : 'bg-[var(--color-surface)] text-[var(--color-body)] hover:text-[var(--color-ink)] border border-[var(--color-hairline)]'
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {/* List of Registered Actions */}
          <div className="flex-1 overflow-y-auto divide-y divide-[var(--color-hairline)]">
            {filtered.map((tool) => {
              const isSelected = selectedTool?.name === tool.name;

              return (
                <div
                  key={tool.name}
                  onClick={() => setSelectedTool(tool)}
                  className={`p-3 flex items-center justify-between gap-2 transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-[var(--color-surface-muted)]/70'
                      : 'hover:bg-[var(--color-surface-muted)]/30'
                  }`}
                >
                  <div className="min-w-0 pr-1">
                    <div className="text-[12.5px] font-mono font-medium text-[var(--color-ink)] truncate">
                      {tool.name}
                    </div>
                    <div className="text-[11.5px] text-[var(--color-muted)] line-clamp-1 mt-0.5">
                      {tool.description}
                    </div>
                  </div>

                  {tool.is_destructive ? (
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-medium bg-[#fdf6ea] text-[var(--color-warning)] border border-[#f2debe] shrink-0">
                      Approval required
                    </span>
                  ) : (
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-medium bg-[#eef6f0] text-[var(--color-success)] border border-[#c7e3d0] shrink-0">
                      Read-only
                    </span>
                  )}
                </div>
              );
            })}
          </div>

        </div>

        {/* Right Pane (7 cols): Schema & Policy Inspector */}
        <div className="md:col-span-7 rounded-xl border border-[var(--color-hairline)] bg-[var(--color-surface)] flex flex-col min-h-0 overflow-hidden shadow-xs">
          {selectedTool ? (
            <div className="flex-1 flex flex-col min-h-0 overflow-y-auto p-5">
              
              {/* Tool Header & Status */}
              <div className="border-b border-[var(--color-hairline)] pb-4 mb-4">
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <h2 className="text-[17px] font-mono font-semibold text-[var(--color-ink)]">
                    {selectedTool.name}
                  </h2>

                  {selectedTool.is_destructive ? (
                    <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-[#fdf6ea] text-[var(--color-warning)] border border-[#f2debe] flex items-center gap-1.5">
                      <Lock className="w-3 h-3 text-[var(--color-warning)]" />
                      <span>Verbal confirmation required</span>
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-[#eef6f0] text-[var(--color-success)] border border-[#c7e3d0] flex items-center gap-1.5">
                      <ShieldCheck className="w-3 h-3 text-[var(--color-success)]" />
                      <span>Automatic read execution</span>
                    </span>
                  )}
                </div>

                <p className="text-[13.5px] text-[var(--color-body)] leading-relaxed">
                  {selectedTool.description}
                </p>
              </div>

              {/* Execution Policy Card */}
              <div className="p-3.5 rounded-lg bg-[var(--color-surface-muted)]/50 border border-[var(--color-hairline)] mb-4">
                <div className="text-[12px] font-semibold text-[var(--color-ink)] mb-1 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-[var(--color-link)]" />
                  <span>Execution guardrail</span>
                </div>
                <p className="text-[12.5px] text-[var(--color-body)] leading-relaxed">
                  {selectedTool.is_destructive
                    ? 'When this action is invoked, the voice assistant pauses and speaks an explicit confirmation prompt. The action only runs if you answer "yes", "confirm", or "proceed".'
                    : 'This tool is read-only. It executes in the background and feeds findings directly into the conversation context with zero friction.'}
                </p>
              </div>

              {/* Parameters Schema */}
              <div>
                <div className="text-[12px] font-semibold text-[var(--color-ink)] mb-2 flex items-center gap-1.5">
                  <Code className="w-4 h-4 text-[var(--color-muted)]" />
                  <span>Parameter schema</span>
                </div>
                <pre className="p-3 rounded-md bg-[var(--color-surface-muted)]/40 border border-[var(--color-hairline)] font-mono text-[11.5px] text-[var(--color-body)] overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(selectedTool.parameters || {}, null, 2)}
                </pre>
              </div>

            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-[var(--color-muted)] text-[13px] p-8">
              Select a tool to inspect its execution schema and safety policy.
            </div>
          )}
        </div>

      </div>

    </div>
  );
};

export default SkillsRegistryPage;

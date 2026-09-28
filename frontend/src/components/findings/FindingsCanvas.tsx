import React, { useState } from 'react';
import { Sparkles, Search, Mail, Calendar, FileText, Database, Copy, Check, Wrench, CheckCircle2 } from 'lucide-react';
import { FindingItem, ToolTrace, ConnectorApp } from '@/types';

interface FindingsCanvasProps {
  findings: FindingItem[];
  recentTools: ToolTrace[];
  connectors: ConnectorApp[];
  onConnectApp: (name: string) => void;
}

/** Format any timestamp (ISO string, unix ms, or garbage) into a short time or fallback. */
const safeFormatTime = (ts: string | number | undefined | null): string => {
  if (ts == null || ts === '') return '';
  const d = new Date(ts);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const normalizeDetails = (raw: unknown): Record<string, unknown> | null => {
  if (!raw) return null;
  if (typeof raw === 'object' && raw !== null) {
    return raw as Record<string, unknown>;
  }
  if (typeof raw === 'string') {
    const trimmed = raw.trim();
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      try {
        const parsed = JSON.parse(trimmed);
        if (typeof parsed === 'object' && parsed !== null) {
          return parsed as Record<string, unknown>;
        }
        return { value: parsed };
      } catch {
        return { info: trimmed };
      }
    }
    return { info: trimmed };
  }
  return { value: raw };
};

export const FindingsCanvas: React.FC<FindingsCanvasProps> = ({
  findings,
  recentTools,
  connectors,
  onConnectApp,
}) => {
  const [activeTab, setActiveTab] = useState<'findings' | 'tools' | 'connectors'>('findings');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="h-full flex flex-col bg-[var(--color-surface)] rounded-xl overflow-hidden">
      {/* Segmented Tab Navigation Header */}
      <div className="pb-3 shrink-0">
        <div className="flex items-center p-1 bg-[var(--color-surface-muted)] border border-[var(--color-hairline)] rounded-xl gap-1">
          <button
            type="button"
            onClick={() => setActiveTab('findings')}
            className={`flex-1 py-1.5 px-3 rounded-lg text-[12px] font-medium transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
              activeTab === 'findings'
                ? 'bg-[var(--color-surface)] text-[var(--color-ink)] shadow-xs font-semibold'
                : 'text-[var(--color-muted)] hover:text-[var(--color-ink)]'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-[var(--color-action)]" />
            <span>Requests</span>
            <span className="font-mono text-[11px] px-1.5 py-0.2 rounded-full bg-[var(--color-surface-muted)] text-[var(--color-muted)] font-medium">
              {findings.length}
            </span>
          </button>
          
          <button
            type="button"
            onClick={() => setActiveTab('tools')}
            className={`flex-1 py-1.5 px-3 rounded-lg text-[12px] font-medium transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
              activeTab === 'tools'
                ? 'bg-[var(--color-surface)] text-[var(--color-ink)] shadow-xs font-semibold'
                : 'text-[var(--color-muted)] hover:text-[var(--color-ink)]'
            }`}
          >
            <Database className="w-3.5 h-3.5 text-[var(--color-link)]" />
            <span>Tool Traces</span>
            <span className="font-mono text-[11px] px-1.5 py-0.2 rounded-full bg-[var(--color-surface-muted)] text-[var(--color-muted)] font-medium">
              {recentTools.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('connectors')}
            className={`flex-1 py-1.5 px-3 rounded-lg text-[12px] font-medium transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
              activeTab === 'connectors'
                ? 'bg-[var(--color-surface)] text-[var(--color-ink)] shadow-xs font-semibold'
                : 'text-[var(--color-muted)] hover:text-[var(--color-ink)]'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-[var(--color-success)]" />
            <span>Connectors</span>
            <span className="font-mono text-[11px] px-1.5 py-0.2 rounded-full bg-[var(--color-surface-muted)] text-[var(--color-muted)] font-medium">
              {connectors.length}
            </span>
          </button>
        </div>
      </div>

      {/* Tab Feed Content */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-3 pr-1">
        
        {/* Tab 1: Findings Feed */}
        {activeTab === 'findings' && (
          findings.length === 0 ? (
            <div className="h-full min-h-[220px] flex flex-col items-center justify-center text-center p-6 text-[var(--color-muted)] gap-2">
              <Sparkles className="w-8 h-8 text-[var(--color-faint)]" />
              <p className="text-[14px] font-medium text-[var(--color-ink)]">
                No tool activity recorded yet
              </p>
              <p className="text-[12px] text-[var(--color-muted)] max-w-[280px]">
                When the assistant performs research, checks calendar, or sends messages, execution summaries will appear here.
              </p>
            </div>
          ) : (
            findings.map((item) => {
              const detailsObj = normalizeDetails(item.details);
              return (
                <div
                  key={item.id}
                  className="bg-[var(--color-surface)] border border-[var(--color-hairline)] rounded-xl p-4 flex flex-col gap-3 shadow-xs hover:border-[var(--color-muted)]/60 transition-all"
                >
                  {/* Card Top Row: Type Badge, Title, Timestamp, Copy */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="w-7 h-7 rounded-lg shrink-0 flex items-center justify-center bg-[var(--color-surface-muted)] border border-[var(--color-hairline)]">
                        {item.type === 'email' && <Mail className="w-3.5 h-3.5 text-blue-600" />}
                        {item.type === 'calendar' && <Calendar className="w-3.5 h-3.5 text-amber-600" />}
                        {item.type === 'search' && <Search className="w-3.5 h-3.5 text-emerald-600" />}
                        {item.type === 'workspace' && <FileText className="w-3.5 h-3.5 text-purple-600" />}
                        {!['email', 'calendar', 'search', 'workspace'].includes(item.type) && (
                          <Wrench className="w-3.5 h-3.5 text-[var(--color-action)]" />
                        )}
                      </div>
                      <span className="font-semibold text-[13.5px] text-[var(--color-ink)] tracking-tight truncate">
                        {item.title}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span className="font-mono text-[11px] text-[var(--color-muted)]">
                        {item.timestamp}
                        {safeFormatTime(item.timestamp)}
                      </span>
                      <button
                        onClick={() => handleCopy(item.id, item.summary)}
                        className="p-1.5 rounded-md hover:bg-[var(--color-surface-muted)] text-[var(--color-muted)] hover:text-[var(--color-ink)] transition-colors cursor-pointer"
                        title="Copy summary"
                      >
                        {copiedId === item.id ? (
                          <Check className="w-3.5 h-3.5 text-[var(--color-success)]" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Summary Text */}
                  <p className="text-[13px] leading-relaxed text-[var(--color-body)]">
                    {item.summary}
                  </p>

                  {/* Structured Light-Mode Parameter Inspector */}
                  {detailsObj && Object.keys(detailsObj).length > 0 && (
                    <div className="bg-[var(--color-surface-muted)]/60 border border-[var(--color-hairline)] rounded-lg p-3 flex flex-col gap-2">
                      <div className="flex items-center justify-between text-[11px] font-mono font-semibold text-[var(--color-muted)] uppercase tracking-wider">
                        <span>Parameters & Details</span>
                        <button
                          onClick={() => handleCopy(
                            item.id + '-details',
                            typeof item.details === 'string' ? item.details : JSON.stringify(detailsObj, null, 2)
                          )}
                          className="hover:text-[var(--color-ink)] flex items-center gap-1 cursor-pointer normal-case text-[11px] font-sans"
                        >
                          {copiedId === item.id + '-details' ? (
                            <Check className="w-3 h-3 text-[var(--color-success)]" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                          <span>{copiedId === item.id + '-details' ? 'Copied' : 'Copy parameters'}</span>
                        </button>
                      </div>

                      <div className="flex flex-col gap-1.5">
                        {Object.entries(detailsObj).map(([key, value]) => {
                          const isComplex = typeof value === 'object' && value !== null;
                          return (
                            <div
                              key={key}
                              className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-2 text-[12px]"
                            >
                              <span className="font-mono font-semibold text-[var(--color-ink)] bg-[var(--color-surface)] px-1.5 py-0.5 rounded border border-[var(--color-hairline)] shrink-0 self-start text-[11.5px]">
                                {key}:
                              </span>
                              <span className="font-mono text-[var(--color-body)] break-all select-all font-medium leading-relaxed">
                                {isComplex ? JSON.stringify(value) : String(value)}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )
        )}

        {/* Tab 2: Tool Execution Traces */}
        {activeTab === 'tools' && (
          recentTools.length === 0 ? (
            <div className="h-full min-h-[220px] flex flex-col items-center justify-center text-center p-6 text-[var(--color-muted)] gap-2">
              <Database className="w-8 h-8 text-[var(--color-faint)]" />
              <p className="text-[14px] font-medium text-[var(--color-ink)]">
                No tool executions recorded
              </p>
              <p className="text-[12px] text-[var(--color-muted)] max-w-[280px]">
                Low-level tool call traces and RPC parameters will appear here during assistant execution.
              </p>
            </div>
          ) : (
            recentTools.map((tool, idx) => {
              const parsedParams = normalizeDetails(tool.params);
              return (
                <div
                  key={idx}
                  className="bg-[var(--color-surface)] border border-[var(--color-hairline)] rounded-xl p-3.5 flex flex-col gap-2.5 shadow-xs hover:border-[var(--color-muted)]/60 transition-all"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-md bg-[var(--color-surface-muted)] border border-[var(--color-hairline)] flex items-center justify-center text-[var(--color-action)]">
                        <Wrench className="w-3.5 h-3.5" />
                      </div>
                      <span className="font-mono font-bold text-[12.5px] text-[var(--color-ink)]">
                        {tool.name.toUpperCase()}
                      </span>
                    </div>
                    <span className="font-mono text-[11px] text-[var(--color-muted)]">
                      {new Date(tool.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      {safeFormatTime(tool.timestamp)}
                    </span>
                  </div>

                  {parsedParams && Object.keys(parsedParams).length > 0 ? (
                    <div className="bg-[var(--color-surface-muted)]/60 border border-[var(--color-hairline)] rounded-lg p-2.5 flex flex-col gap-1.5 text-[11.5px]">
                      {Object.entries(parsedParams).map(([k, v]) => (
                        <div key={k} className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-2">
                          <span className="font-mono font-semibold text-[var(--color-ink)] bg-[var(--color-surface)] px-1.5 py-0.5 rounded border border-[var(--color-hairline)] shrink-0 self-start">
                            {k}:
                          </span>
                          <span className="font-mono text-[var(--color-body)] break-all font-medium">
                            {typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="font-mono text-[11px] text-[var(--color-muted)] italic px-1">
                      No parameters passed
                    </div>
                  )}
                </div>
              );
            })
          )
        )}

        {/* Tab 3: Connectors Matrix */}
        {activeTab === 'connectors' && (
          <div className="flex flex-col gap-2.5">
            {connectors.length === 0 ? (
              <div className="h-full min-h-[200px] flex flex-col items-center justify-center text-center p-6 text-[var(--color-muted)]">
                <p className="text-[13px] font-medium text-[var(--color-ink)]">No connectors configured</p>
              </div>
            ) : (
              connectors.map((app) => (
                <div
                  key={app.name}
                  className={`bg-[var(--color-surface)] border rounded-xl p-3.5 flex items-center justify-between gap-3 shadow-xs transition-all ${
                    app.connected
                      ? 'border-[var(--color-success)]/40 hover:border-[var(--color-success)]'
                      : 'border-[var(--color-hairline)] hover:border-[var(--color-muted)]'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-[var(--color-surface-muted)] border border-[var(--color-hairline)] flex items-center justify-center text-[var(--color-muted)] shrink-0">
                      <Sparkles className={`w-4 h-4 ${app.connected ? 'text-[var(--color-success)]' : 'text-[var(--color-muted)]'}`} />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[13px] font-semibold text-[var(--color-ink)] truncate">
                        {app.display_name || app.name}
                      </div>
                      <div className="font-mono text-[11px] flex items-center gap-1.5 mt-0.5">
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            app.connected ? 'bg-[var(--color-success)]' : 'bg-[var(--color-muted)]'
                          }`}
                        />
                        <span className={app.connected ? 'text-[var(--color-success)] font-medium' : 'text-[var(--color-muted)]'}>
                          {app.connected ? 'Connected & Active' : 'Not Connected'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {!app.connected ? (
                    <button
                      type="button"
                      onClick={() => onConnectApp(app.name)}
                      className="px-3 py-1.5 rounded-lg bg-[var(--color-action)] hover:bg-[var(--color-action-active)] text-white font-mono text-[11px] font-semibold tracking-wider transition-colors cursor-pointer shrink-0 shadow-xs"
                    >
                      Connect
                    </button>
                  ) : (
                    <span className="px-2.5 py-1 rounded-md bg-[#f0fdf4] text-[var(--color-success)] border border-[#bbf7d0] font-mono text-[11px] font-medium shrink-0">
                      Active
                    </span>
                  )}
                </div>
              ))
            )}
          </div>
        )}

      </div>
    </div>
  );
};

export default FindingsCanvas;

import React, { useState } from 'react';
import { Sparkles, Search, Mail, Calendar, FileText, Database, Copy, Check } from 'lucide-react';
import { FindingItem, ToolTrace, ConnectorApp } from '@/types';

interface FindingsCanvasProps {
  findings: FindingItem[];
  recentTools: ToolTrace[];
  connectors: ConnectorApp[];
  onConnectApp: (name: string) => void;
}

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
    <div className="h-full flex flex-col shinra-card rounded-2xl overflow-hidden">
      {/* Workspace Header */}
      <div className="p-4 border-b border-white/8 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[#10B981]/15 border border-[#10B981]/30 flex items-center justify-center text-[#10B981]">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
          <div>
            <h2 className="font-['Space_Grotesk'] text-[14px] font-bold text-white tracking-tight">
              SHINRA Intelligence & Findings
            </h2>
            <p className="font-['JetBrains_Mono'] text-[10.5px] text-zinc-400">
              Structured agent extractions & workspace outputs
            </p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center bg-[#09090b] border border-white/10 rounded-lg p-1">
          <button
            onClick={() => setActiveTab('findings')}
            className={`px-3 py-1 rounded-md text-[11.5px] font-['Space_Grotesk'] font-semibold transition-all cursor-pointer ${
              activeTab === 'findings'
                ? 'bg-[#18181c] text-[#10B981] shadow-sm'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            Findings ({findings.length})
          </button>
          <button
            onClick={() => setActiveTab('tools')}
            className={`px-3 py-1 rounded-md text-[11.5px] font-['Space_Grotesk'] font-semibold transition-all cursor-pointer ${
              activeTab === 'tools'
                ? 'bg-[#18181c] text-[#10B981] shadow-sm'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            Tool Traces ({recentTools.length})
          </button>
          <button
            onClick={() => setActiveTab('connectors')}
            className={`px-3 py-1 rounded-md text-[11.5px] font-['Space_Grotesk'] font-semibold transition-all cursor-pointer ${
              activeTab === 'connectors'
                ? 'bg-[#18181c] text-[#10B981] shadow-sm'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            Connectors
          </button>
        </div>
      </div>

      {/* Workspace Content Feed */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {/* Tab 1: Findings Feed */}
        {activeTab === 'findings' && (
          findings.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-zinc-500">
              <Sparkles className="w-8 h-8 text-zinc-600 mb-2 opacity-50" />
              <p className="font-['Space_Grotesk'] text-[13px] font-medium text-zinc-400">
                No active agent findings yet
              </p>
              <p className="font-['JetBrains_Mono'] text-[11px] text-zinc-500 mt-1 max-w-[280px]">
                Speak or type requests like "Search my emails for flight tickets" or "Find recent AI news".
              </p>
            </div>
          ) : (
            findings.map((item) => (
              <div
                key={item.id}
                className="bg-[#121215]/90 border border-white/8 rounded-xl p-4 flex flex-col gap-2.5 transition-all hover:border-[#10B981]/30 hover:bg-[#18181c]"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {item.type === 'email' && <Mail className="w-3.5 h-3.5 text-blue-400" />}
                    {item.type === 'calendar' && <Calendar className="w-3.5 h-3.5 text-amber-400" />}
                    {item.type === 'search' && <Search className="w-3.5 h-3.5 text-[#10B981]" />}
                    {item.type === 'workspace' && <FileText className="w-3.5 h-3.5 text-purple-400" />}
                    <span className="font-['Space_Grotesk'] text-[13px] font-bold text-white">
                      {item.title}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-['JetBrains_Mono'] text-[10px] text-zinc-400">
                      {item.timestamp}
                    </span>
                    <button
                      onClick={() => handleCopy(item.id, item.summary)}
                      className="text-zinc-500 hover:text-white transition-colors cursor-pointer"
                      title="Copy finding"
                    >
                      {copiedId === item.id ? (
                        <Check className="w-3.5 h-3.5 text-[#10B981]" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                <p className="font-['Plus_Jakarta_Sans'] text-[13px] leading-relaxed text-zinc-300">
                  {item.summary}
                </p>

                {item.details && Object.keys(item.details).length > 0 && (
                  <div className="mt-1 bg-[#09090b] border border-white/6 rounded-lg p-2.5 font-['JetBrains_Mono'] text-[11px] text-zinc-400 overflow-x-auto">
                    <pre>{JSON.stringify(item.details, null, 2)}</pre>
                  </div>
                )}
              </div>
            ))
          )
        )}

        {/* Tab 2: Tool Execution Traces */}
        {activeTab === 'tools' && (
          recentTools.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-zinc-500">
              <Database className="w-8 h-8 text-zinc-600 mb-2 opacity-50" />
              <p className="font-['Space_Grotesk'] text-[13px] font-medium text-zinc-400">
                No tool executions recorded
              </p>
            </div>
          ) : (
            recentTools.map((tool, idx) => (
              <div
                key={idx}
                className="bg-[#121215]/90 border border-white/8 rounded-xl p-3.5 flex flex-col gap-2 font-['JetBrains_Mono']"
              >
                <div className="flex items-center justify-between text-[11.5px]">
                  <span className="font-bold text-[#10B981]">
                    {tool.name.toUpperCase()}
                  </span>
                  <span className="text-zinc-500 text-[10px]">
                    {new Date(tool.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="bg-[#09090b] border border-white/6 rounded-lg p-2 text-[11px] text-zinc-300 overflow-x-auto">
                  <pre>{JSON.stringify(tool.params, null, 2)}</pre>
                </div>
              </div>
            ))
          )
        )}

        {/* Tab 3: Connectors Matrix */}
        {activeTab === 'connectors' && (
          <div className="flex flex-col gap-2.5">
            {connectors.map((app) => (
              <div
                key={app.name}
                className={`bg-[#121215]/90 border border-white/8 rounded-xl p-3.5 flex items-center justify-between gap-3 ${
                  app.connected ? 'border-l-2 border-l-[#10B981]' : ''
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-zinc-200">
                    <Sparkles className="w-4 h-4 text-[#10B981]" />
                  </div>
                  <div>
                    <div className="font-['Space_Grotesk'] text-[13px] font-bold text-white">
                      {app.display_name || app.name}
                    </div>
                    <div className={`font-['JetBrains_Mono'] text-[10px] flex items-center gap-1.5 ${
                      app.connected ? 'text-[#10B981]' : 'text-zinc-500'
                    }`}>
                      <span className="w-1.5 h-1.5 rounded-full bg-current" />
                      <span>{app.connected ? 'ACTIVE & CONNECTED' : 'NOT CONNECTED'}</span>
                    </div>
                  </div>
                </div>

                {!app.connected && (
                  <button
                    onClick={() => onConnectApp(app.name)}
                    className="px-3 py-1.5 rounded-lg bg-[#10B981]/15 border border-[#10B981]/30 text-[#10B981] font-['JetBrains_Mono'] text-[11px] font-semibold hover:bg-[#10B981] hover:text-black transition-all cursor-pointer"
                  >
                    CONNECT
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

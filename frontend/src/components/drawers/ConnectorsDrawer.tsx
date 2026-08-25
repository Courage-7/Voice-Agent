import React from 'react';
import { X, Network, Mail, Calendar, Table, FileText, HardDrive, Search, Sparkles } from 'lucide-react';
import { ConnectorApp } from '@/types';

interface ConnectorsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  connectors: ConnectorApp[];
  loading: boolean;
  onConnect: (appName: string) => void;
  onDisconnect: (connectionId: string) => void;
}

const APP_ICONS: Record<string, React.ReactNode> = {
  GMAIL: <Mail className="w-4 h-4 text-[#EA4335]" />,
  OUTLOOK: <Mail className="w-4 h-4 text-[#0078D4]" />,
  GOOGLECALENDAR: <Calendar className="w-4 h-4 text-[#4285F4]" />,
  GOOGLESHEETS: <Table className="w-4 h-4 text-[#0F9D58]" />,
  GOOGLEDOCS: <FileText className="w-4 h-4 text-[#4285F4]" />,
  GOOGLEDRIVE: <HardDrive className="w-4 h-4 text-[#FFC107]" />,
  SERPAPI: <Search className="w-4 h-4 text-[#4285F4]" />,
  PERPLEXITYAI: <Sparkles className="w-4 h-4 text-[#22D3EE]" />,
};

export const ConnectorsDrawer: React.FC<ConnectorsDrawerProps> = ({
  isOpen,
  onClose,
  connectors,
  loading,
  onConnect,
  onDisconnect,
}) => {
  return (
    <aside
      className={`fixed top-5 bottom-6 left-7 w-[380px] glass-drawer rounded-3xl p-5 flex flex-col gap-4 z-20 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] ${
        isOpen ? 'translate-x-0 opacity-100 pointer-events-auto' : '-translate-x-[calc(100%+40px)] opacity-0 pointer-events-none'
      }`}
    >
      {/* Drawer Header */}
      <div className="flex justify-between items-center pb-3 border-b border-white/10">
        <div className="font-['Syne'] text-[14px] font-extrabold tracking-wider uppercase text-white flex items-center gap-2">
          <Network className="w-4 h-4 text-[#00F0FF]" />
          <span>Connector Nodes</span>
        </div>
        <button
          onClick={onClose}
          className="w-7 h-7 rounded-full bg-white/5 border border-white/10 text-slate-300 flex items-center justify-center hover:bg-white/15 transition-all cursor-pointer"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Drawer Content Feed */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-2.5 pr-1">
        {loading ? (
          <div className="text-center py-8 text-slate-400 font-['JetBrains_Mono'] text-[11px] animate-pulse">
            DISCOVERING COMPOSIO NODES...
          </div>
        ) : connectors.length === 0 ? (
          <div className="text-center py-8 text-slate-500 font-['JetBrains_Mono'] text-[11px]">
            NO CONNECTORS CONFIGURED
          </div>
        ) : (
          connectors.map((app) => {
            const key = (app.name || '').toUpperCase();
            const icon = APP_ICONS[key] || <Network className="w-4 h-4 text-[#00F0FF]" />;

            return (
              <div
                key={key}
                className={`bg-[#040914]/65 border border-white/7 rounded-xl p-3 flex items-center justify-between gap-3 transition-all duration-200 hover:border-[#00F0FF]/30 hover:bg-[#081024]/85 hover:-translate-y-0.5 ${
                  app.connected ? 'border-l-[3px] border-l-[#00FF9D]' : ''
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0">
                    {icon}
                  </div>
                  <div className="min-w-0">
                    <div className="font-['Space_Grotesk'] text-[13px] font-bold text-white truncate">
                      {app.display_name || app.name}
                    </div>
                    <div
                      className={`font-['JetBrains_Mono'] text-[10px] flex items-center gap-1.5 ${
                        app.connected ? 'text-[#00FF9D]' : 'text-slate-400'
                      }`}
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-current" />
                      <span>{app.connected ? 'ONLINE / CONNECTED' : 'STANDBY'}</span>
                    </div>
                  </div>
                </div>

                {app.connected ? (
                  <button
                    onClick={() => onDisconnect(app.connection_id || key)}
                    className="px-2.5 py-1.5 rounded-lg bg-[#FF3366]/15 border border-[#FF3366]/30 text-[#FFA4B8] font-['JetBrains_Mono'] text-[10.5px] font-bold tracking-wider hover:bg-[#FF3366] hover:text-white transition-all cursor-pointer flex-shrink-0"
                  >
                    DISCONNECT
                  </button>
                ) : (
                  <button
                    onClick={() => onConnect(app.name)}
                    className="px-2.5 py-1.5 rounded-lg bg-[#00F0FF]/15 border border-[#00F0FF]/35 text-[#00F0FF] font-['JetBrains_Mono'] text-[10.5px] font-bold tracking-wider hover:bg-[#00F0FF] hover:text-[#020408] transition-all cursor-pointer flex-shrink-0"
                  >
                    CONNECT
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};

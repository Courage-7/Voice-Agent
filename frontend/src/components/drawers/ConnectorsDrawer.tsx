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
  GMAIL: <Mail className="w-4 h-4 text-red-600" />,
  OUTLOOK: <Mail className="w-4 h-4 text-blue-600" />,
  GOOGLECALENDAR: <Calendar className="w-4 h-4 text-amber-600" />,
  GOOGLESHEETS: <Table className="w-4 h-4 text-emerald-600" />,
  GOOGLEDOCS: <FileText className="w-4 h-4 text-blue-600" />,
  GOOGLEDRIVE: <HardDrive className="w-4 h-4 text-amber-600" />,
  SERPAPI: <Search className="w-4 h-4 text-blue-600" />,
  PERPLEXITYAI: <Sparkles className="w-4 h-4 text-purple-600" />,
  TAVILY: <Search className="w-4 h-4 text-sky-600" />,
};

export const ConnectorsDrawer: React.FC<ConnectorsDrawerProps> = ({
  isOpen,
  onClose,
  connectors,
  loading,
  onConnect,
  onDisconnect,
}) => {
  if (!isOpen) return null;

  let content: React.ReactNode;
  if (loading) {
    content = (
      <div className="text-center py-8 text-[var(--color-muted)] font-mono text-[11px] animate-pulse">
        Discovering connector nodes...
      </div>
    );
  } else if (connectors.length === 0) {
    content = (
      <div className="text-center py-8 text-[var(--color-muted)] text-[12px]">
        No connectors configured
      </div>
    );
  } else {
    content = connectors.map((app) => {
      const key = (app.name || '').toUpperCase();
      const icon = APP_ICONS[key] || <Network className="w-4 h-4 text-[var(--color-action)]" />;

      return (
        <div
          key={key}
          className={`bg-[var(--color-surface)] border rounded-xl p-3.5 flex items-center justify-between gap-3 transition-all shadow-xs ${
            app.connected
              ? 'border-[var(--color-success)]/40 hover:border-[var(--color-success)]'
              : 'border-[var(--color-hairline)] hover:border-[var(--color-muted)]'
          }`}
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-[var(--color-surface-muted)] border border-[var(--color-hairline)] flex items-center justify-center shrink-0">
              {icon}
            </div>
            <div className="min-w-0">
              <div className="text-[13px] font-semibold text-[var(--color-ink)] truncate">
                {app.display_name || app.name}
              </div>
              <div
                className={`font-mono text-[10.5px] flex items-center gap-1.5 mt-0.5 ${
                  app.connected ? 'text-[var(--color-success)] font-medium' : 'text-[var(--color-muted)]'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${app.connected ? 'bg-[var(--color-success)]' : 'bg-[var(--color-muted)]'}`} />
                <span>{app.connected ? 'ONLINE / CONNECTED' : 'STANDBY'}</span>
              </div>
            </div>
          </div>

          {app.connected ? (
            <button
              onClick={() => onDisconnect(app.connection_id || key)}
              className="px-2.5 py-1 rounded-md border border-[var(--color-hairline)] text-[var(--color-muted)] hover:text-[var(--color-danger)] hover:bg-[#fcf0f0] text-[11px] font-medium transition-colors cursor-pointer shrink-0"
            >
              Disconnect
            </button>
          ) : (
            <button
              onClick={() => onConnect(app.name)}
              className="px-3 py-1 rounded-md bg-[var(--color-action)] hover:bg-[var(--color-action-active)] text-white text-[11px] font-medium transition-colors cursor-pointer shrink-0 shadow-xs"
            >
              Connect
            </button>
          )}
        </div>
      );
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/25 transition-opacity duration-200"
        aria-hidden="true"
      />

      {/* Slide-Over Panel */}
      <aside
        role="dialog"
        aria-label="Connector nodes"
        className="relative w-full sm:w-[460px] h-full bg-[var(--color-surface)] border-l border-[var(--color-hairline)] shadow-xl z-10 flex flex-col p-5 gap-4 animate-in slide-in-from-right duration-200"
      >
        {/* Drawer Header */}
        <div className="flex justify-between items-center pb-3 border-b border-[var(--color-hairline)] shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-md bg-[var(--color-surface-muted)] border border-[var(--color-hairline)] flex items-center justify-center text-[var(--color-muted)]">
              <Network className="w-4 h-4" />
            </div>
            <div>
              <div className="font-['DM_Serif_Display'] text-[17px] text-[var(--color-ink)] leading-none">
                Workspace Connectors
              </div>
              <div className="font-mono text-[11px] text-[var(--color-muted)] mt-0.5">
                Manage integrated data sources and applications
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            title="Close panel"
            aria-label="Close panel"
            className="w-8 h-8 rounded-md hover:bg-[var(--color-surface-muted)] text-[var(--color-muted)] hover:text-[var(--color-ink)] flex items-center justify-center transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Drawer Content Feed */}
        <div className="flex-1 overflow-y-auto flex flex-col gap-2.5 pr-1">
          {content}
        </div>
      </aside>
    </div>
  );
};

export default ConnectorsDrawer;

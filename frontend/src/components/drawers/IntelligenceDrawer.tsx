import React from 'react';
import { X, Activity } from 'lucide-react';
import { FindingsCanvas } from '@/components/findings/FindingsCanvas';
import { FindingItem, ToolTrace, ConnectorApp } from '@/types';

interface IntelligenceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  findings: FindingItem[];
  recentTools: ToolTrace[];
  connectors: ConnectorApp[];
  onConnectApp: (name: string) => void;
}

export const IntelligenceDrawer: React.FC<IntelligenceDrawerProps> = ({
  isOpen,
  onClose,
  findings,
  recentTools,
  connectors,
  onConnectApp,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* 1. Backdrop Scrim */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/25 transition-opacity duration-200"
        aria-hidden="true"
      />

      {/* 2. Slide-Over Panel */}
      <aside
        role="dialog"
        aria-label="Tool activity panel"
        className="relative w-full sm:w-[540px] h-full bg-[var(--color-surface)] border-l border-[var(--color-hairline)] shadow-xl z-10 flex flex-col animate-in slide-in-from-right duration-200"
      >
        {/* Drawer Header */}
        <div className="flex justify-between items-center p-4 border-b border-[var(--color-hairline)] bg-[var(--color-surface)] shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-md bg-[var(--color-surface-muted)] border border-[var(--color-hairline)] flex items-center justify-center text-[var(--color-muted)]">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <div className="font-['DM_Serif_Display'] text-[17px] text-[var(--color-ink)] leading-none">
                Tool activity
              </div>
              <div className="font-mono text-[11px] text-[var(--color-muted)] mt-0.5">
                {findings.length} findings · {recentTools.length} traces · {connectors.length} apps
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

        {/* Content Body */}
        <div className="flex-1 overflow-hidden p-4">
          <FindingsCanvas
            findings={findings}
            recentTools={recentTools}
            connectors={connectors}
            onConnectApp={onConnectApp}
          />
        </div>
      </aside>
    </div>
  );
};

export default IntelligenceDrawer;

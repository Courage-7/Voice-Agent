export type SessionState =
  | 'DISCONNECTED'
  | 'CONNECTED'
  | 'LISTENING'
  | 'USER_SPEAKING'
  | 'THINKING'
  | 'SPEAKING'
  | 'ERROR';

export interface ConnectorApp {
  name: string;
  display_name?: string;
  capability?: string;
  description?: string;
  connected?: boolean;
  connection_id?: string;
  app_key?: string;
}

export interface TranscriptEntry {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface FindingItem {
  id: string;
  type: 'search' | 'email' | 'calendar' | 'workspace' | 'memory' | 'insight';
  title: string;
  summary: string;
  details?: Record<string, any>;
  timestamp: string;
}

export interface VoiceModelOption {
  id: string;
  name: string;
  accent?: string;
  gender?: string;
}

export interface ToolTrace {
  name: string;
  params: Record<string, any>;
  timestamp: number;
}

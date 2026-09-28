export type SessionState =
  | 'DISCONNECTED'
  | 'CONNECTED'
  | 'LISTENING'
  | 'USER_SPEAKING'
  | 'THINKING'
  | 'SPEAKING'
  | 'MUTED'
  | 'ERROR';

export interface ConnectorApp {
  name: string;
  display_name?: string;
  capability?: string;
  description?: string;
  connected?: boolean;
  authorizing?: boolean;
  status?: string;
  connection_id?: string;
  app_key?: string;
  logo_url?: string;
  categories?: string[];
  auth_url?: string;
}

export type TextBlock = {
  type: 'text';
  content: string;
};

export type CodeBlockData = {
  type: 'code';
  language?: string;
  code: string;
  title?: string;
};

export type ImageBlockData = {
  type: 'image';
  url: string;
  alt?: string;
  caption?: string;
};

export type FileBlockData = {
  type: 'file';
  name: string;
  url: string;
  mimeType?: string;
  size?: number;
};

export type ToolBlockData = {
  type: 'tool';
  tool: string;
  status: 'running' | 'success' | 'error';
  durationMs?: number;
  input?: Record<string, any>;
  output?: any;
};

export type CitationBlockData = {
  type: 'citation';
  url: string;
  title: string;
  snippet?: string;
};

export type LinkPreviewBlockData = {
  type: 'link_preview';
  url: string;
  title: string;
  description?: string;
  image?: string;
};

export type MessageBlock =
  | TextBlock
  | CodeBlockData
  | ImageBlockData
  | FileBlockData
  | ToolBlockData
  | CitationBlockData
  | LinkPreviewBlockData;

export interface AssistantMessage {
  id: string;
  role: 'assistant';
  display: {
    format: 'markdown';
    content: string;
  };
  speech?: {
    text: string;
  };
  blocks?: MessageBlock[];
  createdAt: string;
}

export interface TranscriptEntry {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  display?: {
    format: 'markdown' | 'text';
    content: string;
  };
  speech?: {
    text: string;
  };
  blocks?: MessageBlock[];
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

import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';

export interface SavedConversation {
  session_id: string;
  user_id: string;
  title: string;
  turns: number;
  created_at: string;
  updated_at?: string;
  status?: string;
  preview?: string;
}

export interface ConversationDetail extends SavedConversation {
  messages: Array<{
    role: string;
    content: string;
    timestamp?: string;
    tool_calls?: any[];
  }>;
}

export function useConversations() {
  const [conversations, setConversations] = useState<SavedConversation[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [activeConversation, setActiveConversation] = useState<ConversationDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);

  const { getAuthHeaders } = useAuth();

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    try {
      const headers = await getAuthHeaders();
      const res = await fetch('/api/conversations?limit=50', {
        headers,
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        const convs = data.conversations || [];
        const formatted: SavedConversation[] = convs.map((c: any) => ({
          session_id: c.session_id || c.id,
          user_id: c.user_id || '',
          title: c.title || c.summary || `Session ${c.session_id ? c.session_id.slice(0, 8) : 'Dialogue'}`,
          turns: c.turns_count || c.turns || (c.messages ? c.messages.length : 0),
          created_at: c.created_at || new Date().toISOString(),
          status: c.status || 'completed',
          preview: c.messages && c.messages.length > 0 ? c.messages[c.messages.length - 1].content : 'Voice interaction transcript',
        }));
        setConversations(formatted);
      }
    } catch (err) {
      console.warn('Could not fetch conversations from API, using cached state:', err);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeaders]);

  const loadConversationDetail = useCallback(async (sessionId: string) => {
    setSelectedSessionId(sessionId);
    setDetailLoading(true);
    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`/api/conversations/${sessionId}`, {
        headers,
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setActiveConversation({
          session_id: data.session_id || sessionId,
          user_id: data.user_id || '',
          title: data.title || `Session ${sessionId.slice(0, 8)}`,
          turns: data.turns_count || (data.messages ? data.messages.length : 0),
          created_at: data.created_at || new Date().toISOString(),
          messages: data.messages || [],
        });
      }
    } catch (err) {
      console.error('Error fetching conversation transcript:', err);
    } finally {
      setDetailLoading(false);
    }
  }, [getAuthHeaders]);

  const deleteConversation = useCallback(async (sessionId: string) => {
    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`/api/conversations/${sessionId}`, {
        method: 'DELETE',
        headers,
        credentials: 'include',
      });
      if (res.ok) {
        setConversations((prev) => prev.filter((c) => c.session_id !== sessionId));
        if (selectedSessionId === sessionId) {
          setSelectedSessionId(null);
          setActiveConversation(null);
        }
        toast.success('Conversation Deleted', {
          description: 'Session transcript removed from server.',
        });
      } else {
        toast.error('Deletion Failed', {
          description: `Server returned HTTP ${res.status}`,
        });
      }
    } catch (err: any) {
      console.error('Error deleting conversation:', err);
      toast.error('Failed to Delete Conversation', {
        description: err?.message || String(err),
      });
    }
  }, [getAuthHeaders, selectedSessionId]);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  return {
    conversations,
    loading,
    selectedSessionId,
    activeConversation,
    detailLoading,
    refreshConversations: fetchConversations,
    selectConversation: loadConversationDetail,
    deleteConversation,
  };
}

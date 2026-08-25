import { useState, useEffect, useCallback } from 'react';
import { ConnectorApp } from '@/types';

export function useConnectors() {
  const [connectors, setConnectors] = useState<ConnectorApp[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchConnectors = useCallback(async () => {
    try {
      const [appsRes, statusRes] = await Promise.all([
        fetch('/api/integrations/apps'),
        fetch('/api/integrations/status?user_id=web_user'),
      ]);

      const appsData = await appsRes.json();
      const statusData = await statusRes.json();

      const supported: ConnectorApp[] = appsData.apps || [];
      const connectedList: any[] = statusData.connected_accounts || [];

      const merged = supported.map((app) => {
        const appKey = (app.name || '').toUpperCase();
        const connectedMatch = connectedList.find(
          (c) => (c.app || '').toUpperCase() === appKey || (c.app_key || '').toUpperCase() === appKey
        );
        return {
          ...app,
          app_key: appKey,
          connected: Boolean(connectedMatch),
          connection_id: connectedMatch ? connectedMatch.id || connectedMatch.connection_id || appKey : appKey,
        };
      });

      setConnectors(merged);
    } catch (err) {
      console.error('Failed to fetch connectors:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConnectors();
  }, [fetchConnectors]);

  const connectApp = useCallback(
    async (appName: string) => {
      try {
        const res = await fetch(`/api/integrations/connect/${appName}?user_id=web_user`);
        const data = await res.json();
        if (data.auth_url) {
          window.open(data.auth_url, '_blank');
          const interval = setInterval(async () => {
            const check = await fetch('/api/integrations/status?user_id=web_user');
            const cData = await check.json();
            const target = (cData.connected_accounts || []).find(
              (a: any) => (a.app || a.app_key || '').toUpperCase() === appName.toUpperCase()
            );
            if (target) {
              clearInterval(interval);
              void fetchConnectors();
            }
          }, 2500);
        } else {
          void fetchConnectors();
        }
      } catch (e) {
        alert('OAuth initiation failed: ' + e);
      }
    },
    [fetchConnectors]
  );

  const disconnectApp = useCallback(
    async (connectionId: string) => {
      if (!confirm('Disconnect this workspace integration node?')) return;
      try {
        const res = await fetch(`/api/integrations/${connectionId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
          void fetchConnectors();
        } else {
          alert('Disconnect failed: ' + (data.detail || data.error));
        }
      } catch (e) {
        alert('Failed to disconnect: ' + e);
      }
    },
    [fetchConnectors]
  );

  return {
    connectors,
    loading,
    refreshConnectors: fetchConnectors,
    connectApp,
    disconnectApp,
  };
}

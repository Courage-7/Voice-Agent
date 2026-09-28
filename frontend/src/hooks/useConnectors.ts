import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';
import { ConnectorApp } from '@/types';
import { useAuth } from '@/context/AuthContext';

export function useConnectors() {
  const [connectors, setConnectors] = useState<ConnectorApp[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [authorizingApps, setAuthorizingApps] = useState<Record<string, boolean>>({});
  const activeIntervalsRef = useRef<Set<ReturnType<typeof setInterval>>>(new Set());
  const authorizingAppsRef = useRef(authorizingApps);
  const { getAuthHeaders, isAuthenticated } = useAuth();

  // Polling state must not recreate the fetch callback: doing so made the
  // effect below refetch and reset its cleanup every authorization update.
  useEffect(() => {
    authorizingAppsRef.current = authorizingApps;
  }, [authorizingApps]);

  const fetchConnectors = useCallback(async () => {
    try {
      // The app catalog is public metadata. Always load it even when the
      // per-user connection-status request is unavailable or unauthenticated.
      const appsRequest = fetch('/api/integrations/apps');
      const headers = await getAuthHeaders();
      const [appsResult, statusResult] = await Promise.allSettled([
        appsRequest,
        fetch('/api/integrations/status', { headers, credentials: 'include' }),
      ]);

      if (appsResult.status === 'rejected' || !appsResult.value.ok) {
        throw new Error('Unable to load the integration catalog.');
      }

      const appsData = await appsResult.value.json();
      const statusData = appsResult.status === 'fulfilled' && statusResult.status === 'fulfilled' && statusResult.value.ok
        ? await statusResult.value.json().catch(() => ({}))
        : {};


      const supported: ConnectorApp[] = appsData.apps || [];
      const connectedList: any[] = statusData.connected_accounts || [];

      const merged = supported.map((app) => {
        const appKey = (app.name || '').toUpperCase();
        const cleanTarget = appKey.replace(/[^A-Z0-9]/g, '');
        const connectedMatch = connectedList.find((c) => {
          const cApp = (c.app || c.app_key || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
          const status = (c.status || '').toUpperCase();
          const isActive = status === 'ACTIVE' || c.is_active === true;
          return isActive && (cApp === cleanTarget || (cApp.length > 3 && cleanTarget.length > 3 && (cApp.includes(cleanTarget) || cleanTarget.includes(cApp))));
        });
        return {
          ...app,
          app_key: appKey,
          connected: Boolean(connectedMatch),
          authorizing: Boolean(authorizingAppsRef.current[app.name] || authorizingAppsRef.current[appKey]),
          status: connectedMatch?.status || (Boolean(connectedMatch) ? 'ACTIVE' : 'DISCONNECTED'),
          connection_id: connectedMatch ? connectedMatch.id || connectedMatch.connection_id || appKey : appKey,
        };
      });

      setConnectors(merged);
    } catch (err) {
      console.error('Failed to fetch connectors:', err);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeaders]);

  useEffect(() => {
    fetchConnectors();
    const intervals = activeIntervalsRef.current;
    return () => {
      intervals.forEach((id) => clearInterval(id));
      intervals.clear();
    };
  }, [fetchConnectors, isAuthenticated]);

  const connectApp = useCallback(
    async (appName: string) => {
      const appKey = appName.toUpperCase();
      setAuthorizingApps((prev) => ({ ...prev, [appName]: true, [appKey]: true }));

      try {
        const headers = await getAuthHeaders();
        const res = await fetch(`/api/integrations/connect/${appName}`, {
          headers,
          credentials: 'include',
        });

        if (res.status === 401) {
          setAuthorizingApps((prev) => {
            const next = { ...prev };
            delete next[appName];
            delete next[appKey];
            return next;
          });
          toast.error('Authentication Required', {
            description: `Please sign in with your email to connect ${appName}.`,
          });
          return;
        }

        const data = await res.json();
        if (!res.ok) {
          setAuthorizingApps((prev) => {
            const next = { ...prev };
            delete next[appName];
            delete next[appKey];
            return next;
          });
          toast.error(`Connection Failed: ${appName}`, {
            description: data.detail || `Server returned HTTP ${res.status}`,
          });
          const detailStr = String(data?.detail || '');
          const isMissingAuthConfig =
            detailStr.includes('No active auth config') ||
            detailStr.includes('auth_configs');

          if (isMissingAuthConfig) {
            toast.info(`${appName} Integration`, {
              description: `${appName} is an API-based service. Ensure ${appKey}_API_KEY is configured in your server environment or enable it in Composio.`,
            });
          } else {
            toast.error(`Connection Failed: ${appName}`, {
              description: detailStr || `Server returned HTTP ${res.status}`,
            });
          }
          return;
        }

        const authUrl = data.auth_url || data.redirect_url || data.url;
        if (authUrl) {
          toast.info(`Authorizing ${appName}`, {
            description: 'Opening provider authorization window in a new tab...',
          });
          window.open(authUrl, '_blank');
          let attempts = 0;
          const maxAttempts = 30; // 75s timeout (30 * 2.5s)
          const intervalId = setInterval(async () => {
            attempts++;
            if (attempts >= maxAttempts) {
              clearInterval(intervalId);
              activeIntervalsRef.current.delete(intervalId);
              setAuthorizingApps((prev) => {
                const next = { ...prev };
                delete next[appName];
                delete next[appKey];
                return next;
              });
              toast.warning(`Authentication Timeout: ${appName}`, {
                description: 'Authorization was not completed in time. Click Connect to retry.',
              });
              void fetchConnectors();
              return;
            }
            try {
              const headers = await getAuthHeaders();
              const check = await fetch('/api/integrations/status', {
                headers,
                credentials: 'include',
              });
              const cData = await check.json();
              const cleanTarget = appName.toUpperCase().replace(/[^A-Z0-9]/g, '');
              const isConnected = (cData.connected_accounts || []).some(
                (a: any) => {
                  const aKey = (a.app || a.app_key || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
                  const isActive = (a.status || '').toUpperCase() === 'ACTIVE' || a.is_active === true;
                  return isActive && (aKey === cleanTarget || (aKey.length > 3 && cleanTarget.length > 3 && (aKey.includes(cleanTarget) || cleanTarget.includes(aKey))));
                }
              );
              if (isConnected) {
                clearInterval(intervalId);
                activeIntervalsRef.current.delete(intervalId);
                setAuthorizingApps((prev) => {
                  const next = { ...prev };
                  delete next[appName];
                  delete next[appKey];
                  return next;
                });
                toast.success(`${appName} Connected`, {
                  description: 'Workspace credentials verified and active.',
                });
                void fetchConnectors();
              }
            } catch {
              // Ignore transient fetch errors during polling
            }
          }, 2500);
          activeIntervalsRef.current.add(intervalId);
        } else {
          setAuthorizingApps((prev) => {
            const next = { ...prev };
            delete next[appName];
            delete next[appKey];
            return next;
          });
          void fetchConnectors();
        }
      } catch (e: any) {
        setAuthorizingApps((prev) => {
          const next = { ...prev };
          delete next[appName];
          delete next[appKey];
          return next;
        });
        toast.error('OAuth Initiation Failed', {
          description: e?.message || String(e),
        });
      }
    },
    [fetchConnectors, getAuthHeaders]
  );

  const disconnectApp = useCallback(
    async (connectionId: string) => {
      try {
        const headers = await getAuthHeaders();
        const res = await fetch(`/api/integrations/${connectionId}`, {
          method: 'DELETE',
          headers,
          credentials: 'include',
        });
        const data = await res.json();
        if (data.success) {
          toast.success('Integration Disconnected', {
            description: 'The connection credentials have been removed.',
          });
          void fetchConnectors();
        } else {
          toast.error('Disconnect Failed', {
            description: data.detail || data.error || 'Could not disconnect integration.',
          });
        }
      } catch (e: any) {
        toast.error('Failed to Disconnect', {
          description: e?.message || String(e),
        });
      }
    },
    [fetchConnectors, getAuthHeaders]
  );

  return {
    connectors,
    loading,
    refreshConnectors: fetchConnectors,
    connectApp,
    disconnectApp,
  };
}

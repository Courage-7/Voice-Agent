import { useEffect, useState } from 'react';

export function RuntimeNotice() {
  const [demoMode, setDemoMode] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    async function readRuntimeMode() {
      try {
        const response = await fetch('/api/health', { signal: controller.signal });
        if (!response.ok) return;
        const data = await response.json();
        if (!controller.signal.aborted) setDemoMode(data.demo_mode === true);
      } catch {
        // Normal connection controls report backend availability.
      }
    }
    void readRuntimeMode();
    return () => controller.abort();
  }, []);

  return demoMode ? (
    <div role="status" className="shrink-0 border-b border-amber-300/20 bg-amber-950/90 px-4 py-2 text-center text-xs text-amber-100">
      Demo mode. Live voice and connected apps are disabled. Saved data is temporary.
    </div>
  ) : null;
}

import { useState, useEffect, useRef, useCallback } from 'react';

type TerminalLine = {
  id: string;
  type: 'system' | 'output' | 'error';
  text: string;
};

export function useCodeLab(userId: string) {
  const [enginePhase, setEnginePhase] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [remainingTime, setRemainingTime] = useState<number | null>(null);
  const [terminalOutput, setTerminalOutput] = useState<TerminalLine[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const isEngineAwake = enginePhase === 'Running';

  const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
  const WS_URL = API_URL.replace(/^http/, 'ws');

  const addTermLine = useCallback((type: 'system' | 'output' | 'error', text: string) => {
    setTerminalOutput(prev => [...prev, { id: Math.random().toString(36).substring(7), type, text }]);
  }, []);

  // 2. The "Heartbeat" Mechanism
  useEffect(() => {
    const checkHealth = async () => {
      if (!userId) return;
      try {
        const res = await fetch(`${API_URL}/status/${userId}`, {
          signal: AbortSignal.timeout(5000)
        });
        if (res.ok) {
          const data = await res.json();
          setEnginePhase(data.phase);
          if (data.remaining_seconds !== undefined) {
            setRemainingTime(data.remaining_seconds);
          }
        } else {
          setEnginePhase('Offline');
          setRemainingTime(null);
        }
      } catch (err) {
        setEnginePhase('Offline');
      }
    };
    
    checkHealth();
    const interval = setInterval(checkHealth, 5000); // Poll every 5s
    
    return () => clearInterval(interval);
  }, [API_URL, userId]);

  const runCode = useCallback((code: string) => {
    if (!isEngineAwake || !userId) return;

    setIsRunning(true);
    setTerminalOutput([]);
    addTermLine('system', 'Initializing execution sandbox...');

    // 3. The WebSocket Lifecycle Manager
    const ws = new WebSocket(`${WS_URL}/execute/${userId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      addTermLine('system', 'Connected to Python execution engine. Running code...');
      ws.send(JSON.stringify({ code }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'output') {
          addTermLine('output', data.data);
        } else if (data.type === 'error') {
          addTermLine('error', data.data);
        } else if (data.type === 'system') {
          addTermLine('system', data.data);
        }
      } catch (e) {
        // Fallback for raw string
        addTermLine('output', event.data);
      }
    };

    ws.onclose = () => {
      setIsRunning(false);
      wsRef.current = null;
    };

    ws.onerror = () => {
      addTermLine('error', 'WebSocket Connection Error.');
    };
  }, [WS_URL, isEngineAwake, addTermLine, userId]);

  const exitLab = useCallback(async () => {
    if (!userId) return;
    try {
      await fetch(`${API_URL}/pod/${userId}`, { method: 'DELETE' });
    } catch (e) {
      console.error("Failed to cleanly exit lab", e);
    }
  }, [API_URL, userId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    isEngineAwake,
    enginePhase,
    isRunning,
    remainingTime,
    terminalOutput,
    runCode,
    exitLab
  };
}

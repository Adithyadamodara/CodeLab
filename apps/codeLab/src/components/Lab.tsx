import { Play, LogOut, Clock } from 'lucide-react';
import { useCodeLab } from '../hooks/useCodeLab';
import { EditorWidget } from './EditorWidget';
import { TerminalStreamer } from './TerminalStreamer';
import { useState } from 'react';

const DEFAULT_CODE = `def greet(name):
    print(f"Hello, {name}! Welcome to CodeLab.")

if __name__ == "__main__":
    greet("Explorer")
`;

export function Lab({ userId, onExit }: { userId: string, onExit: () => void }) {
  const { isEngineAwake, enginePhase, isRunning, remainingTime, terminalOutput, runCode, exitLab } = useCodeLab(userId);
  const [code, setCode] = useState(DEFAULT_CODE);

  const isOffline = isEngineAwake === false && enginePhase !== 'Expired';
  const isConnecting = isEngineAwake === null && enginePhase !== 'Expired';
  const isExpired = enginePhase === 'Expired';

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const handleExit = () => {
    exitLab();
    onExit();
  };

  return (
    <div className="lab-layout">
      <header className="lab-header glass-panel">
        <div className="brand">
          <span style={{ color: 'var(--color-forest-green)' }}>Code</span>
          <span style={{ color: 'var(--color-lake-blue)' }}>Lab</span>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          {remainingTime !== null && remainingTime > 0 && (
            <div className="timer-badge" style={{ display: 'flex', alignItems: 'center', gap: '6px', color: remainingTime < 60 ? 'red' : 'inherit' }}>
              <Clock size={16} />
              <span>{formatTime(remainingTime)} remaining</span>
            </div>
          )}
          <div className="status-badge">
            <div 
              className={`status-dot ${isOffline ? 'offline' : (isConnecting ? 'connecting' : 'online')}`} 
            />
            {isOffline ? 'Engine Offline' : (isConnecting ? 'Checking Engine...' : 'Engine Online')}
          </div>
          <button 
            onClick={handleExit}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', borderRadius: '6px', border: '1px solid #e2e8f0', background: 'white', cursor: 'pointer', color: '#64748b', fontSize: '0.9rem' }}
          >
            <LogOut size={16} />
            Exit Lab
          </button>
        </div>
      </header>

      <main className="lab-content">
        <section className="editor-section glass-panel">
          <div className="editor-toolbar">
            <span style={{ fontWeight: 600, color: 'var(--color-pine-dark)' }}>main.py</span>
            <button 
              className="run-btn"
              onClick={() => runCode(code)}
              disabled={isOffline || isRunning || isConnecting}
            >
              <Play size={16} />
              {isRunning ? 'Running...' : 'Run Code'}
            </button>
          </div>
          
          <EditorWidget 
            code={code}
            onChange={(val) => setCode(val || '')}
            readOnly={isOffline || isConnecting}
          />
        </section>

        <TerminalStreamer output={terminalOutput} />
      </main>

      {isExpired && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <div style={{
            background: 'white', padding: '30px', borderRadius: '12px',
            textAlign: 'center', maxWidth: '400px', boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
          }}>
            <h2 style={{ color: 'var(--color-pine-dark)', marginTop: 0 }}>Session Expired</h2>
            <p style={{ color: '#64748b', marginBottom: '24px' }}>
              Your 10-minute lab session has reached its time limit. 
              Please exit and launch a new session to continue.
            </p>
            <button 
              onClick={handleExit}
              className="run-btn"
              style={{ width: '100%', justifyContent: 'center' }}
            >
              Start New Session
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

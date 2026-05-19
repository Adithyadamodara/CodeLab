import React, { useEffect, useRef } from 'react';

type TerminalLine = {
  id: string;
  type: 'system' | 'output' | 'error';
  text: string;
};

interface TerminalStreamerProps {
  output: TerminalLine[];
}

export const TerminalStreamer: React.FC<TerminalStreamerProps> = ({ output }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [output]);

  return (
    <div className="terminal-section">
      <div className="terminal-header">
        Terminal
      </div>
      <div className="terminal-output" ref={containerRef}>
        {output.map((line) => (
          <div key={line.id} className={`term-line ${line.type}`}>
            {line.text}
          </div>
        ))}
      </div>
    </div>
  );
};

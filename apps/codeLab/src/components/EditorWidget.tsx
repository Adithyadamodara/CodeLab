import React from 'react';
import Editor from '@monaco-editor/react';

interface EditorWidgetProps {
  code: string;
  onChange: (value: string | undefined) => void;
  readOnly: boolean;
}

export const EditorWidget: React.FC<EditorWidgetProps> = ({ code, onChange, readOnly }) => {
  return (
    <div className="editor-wrapper">
      <Editor
        height="100%"
        defaultLanguage="python"
        theme="vs-light" // We can also define a custom nature theme here later
        value={code}
        onChange={onChange}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          fontFamily: "'Fira Code', monospace",
          readOnly: readOnly,
          wordWrap: 'on',
          scrollBeyondLastLine: false,
          padding: { top: 16 }
        }}
      />
      {readOnly && (
        <div className="offline-banner">
          <div className="offline-banner-content">
            <h3>Execution Engine Offline</h3>
            <p>The sandbox is currently asleep. The editor is in Read-Only mode.</p>
          </div>
        </div>
      )}
    </div>
  );
};

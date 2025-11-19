'use client';

import { useEffect, useRef } from 'react';
import Editor from '@monaco-editor/react';

interface CodeEditorProps {
  code: string;
  language: string;
  onChange?: (value: string) => void;
  readOnly?: boolean;
}

export default function CodeEditor({ code, language, onChange, readOnly = false }: CodeEditorProps) {
  const editorRef = useRef<any>(null);

  // Map our language names to Monaco language IDs
  const getMonacoLanguage = (lang: string): string => {
    const languageMap: Record<string, string> = {
      'html': 'html',
      'gradio': 'python',
      'streamlit': 'python',
      'transformers.js': 'html', // Contains HTML, CSS, and JavaScript - HTML is primary
      'react': 'javascriptreact', // JSX syntax highlighting
      'comfyui': 'json',
    };
    return languageMap[lang] || 'plaintext';
  };

  const handleEditorDidMount = (editor: any) => {
    editorRef.current = editor;
  };

  return (
    <div className="h-full overflow-hidden">
      <Editor
        height="100%"
        language={getMonacoLanguage(language)}
        value={code}
        onChange={(value) => onChange && onChange(value || '')}
        theme="vs-dark"
        options={{
          readOnly,
          minimap: { enabled: true },
          fontSize: 14,
          fontFamily: "'SF Mono', 'JetBrains Mono', 'Menlo', 'Monaco', 'Courier New', monospace",
          wordWrap: 'on',
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          padding: { top: 16, bottom: 16 },
          lineHeight: 22,
          letterSpacing: 0.5,
        }}
        onMount={handleEditorDidMount}
      />
    </div>
  );
}


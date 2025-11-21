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
  const lastFormattedCodeRef = useRef<string>('');
  const formatTimeoutRef = useRef<NodeJS.Timeout | null>(null);

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

  // Format code intelligently - only when generation appears complete
  useEffect(() => {
    if (editorRef.current && code && code.length > 100) {
      // Clear existing timeout
      if (formatTimeoutRef.current) {
        clearTimeout(formatTimeoutRef.current);
      }
      
      // Only format if code hasn't been formatted yet or if it's different
      if (code !== lastFormattedCodeRef.current) {
        // Wait 1 second after code stops changing before formatting
        formatTimeoutRef.current = setTimeout(() => {
          if (editorRef.current) {
            editorRef.current.getAction('editor.action.formatDocument')?.run();
            lastFormattedCodeRef.current = code;
          }
        }, 1000);
      }
    }
    
    return () => {
      if (formatTimeoutRef.current) {
        clearTimeout(formatTimeoutRef.current);
      }
    };
  }, [code]);

  return (
    <div className="h-full overflow-hidden bg-[#1e1e1e]">
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
          wordWrap: 'off',
          lineNumbers: 'on',
          lineNumbersMinChars: 3,
          glyphMargin: false,
          folding: true,
          lineDecorationsWidth: 10,
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          insertSpaces: true,
          padding: { top: 16, bottom: 16 },
          lineHeight: 22,
          letterSpacing: 0.5,
          renderLineHighlight: 'line',
          formatOnPaste: true,
          formatOnType: false,
          scrollbar: {
            verticalScrollbarSize: 10,
            horizontalScrollbarSize: 10,
          },
        }}
        onMount={handleEditorDidMount}
      />
    </div>
  );
}


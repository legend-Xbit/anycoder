'use client';

import { useState, useEffect } from 'react';
import Header from '@/components/Header';
import ChatInterface from '@/components/ChatInterface';
import CodeEditor from '@/components/CodeEditor';
import ControlPanel from '@/components/ControlPanel';
import { apiClient } from '@/lib/api';
import { isAuthenticated as checkIsAuthenticated, getStoredToken } from '@/lib/auth';
import type { Message, Language, CodeGenerationRequest } from '@/types';

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [generatedCode, setGeneratedCode] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState<Language>('html');
  const [selectedModel, setSelectedModel] = useState('openrouter/sherlock-dash-alpha');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    checkAuth();
    // Check auth status every second to catch OAuth redirects
    const interval = setInterval(checkAuth, 1000);
    return () => clearInterval(interval);
  }, []);

  const checkAuth = () => {
    const authenticated = checkIsAuthenticated();
    setIsAuthenticated(authenticated);
    
    // Make sure API client has the token
    if (authenticated) {
      const token = getStoredToken();
      if (token) {
        apiClient.setToken(token);
      }
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!isAuthenticated) {
      alert('Please sign in with HuggingFace first! Click the "Sign in with Hugging Face" button in the header.');
      return;
    }

    // Add user message
    const userMessage: Message = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsGenerating(true);

    // Prepare request
    const request: CodeGenerationRequest = {
      query: message,
      language: selectedLanguage,
      model_id: selectedModel,
      provider: 'auto',
      history: messages.map((m) => [m.role, m.content]),
      agent_mode: false,
    };

    let generatedCodeBuffer = '';
    const assistantMessage: Message = {
      role: 'assistant',
      content: '⏳ Generating code...',
      timestamp: new Date().toISOString(),
    };

    // Add placeholder for assistant message
    setMessages((prev) => [...prev, assistantMessage]);

    // Stream the response
    try {
      apiClient.generateCodeStream(
        request,
        // onChunk - Update code editor in real-time, NOT the chat
        (chunk: string) => {
          generatedCodeBuffer += chunk;
          setGeneratedCode(generatedCodeBuffer);
        },
        // onComplete
        (code: string) => {
          setGeneratedCode(code);
          setIsGenerating(false);
          
          // Update final message - just show success, not the code
          setMessages((prev) => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1] = {
              ...assistantMessage,
              content: '✅ Code generated successfully! Check the editor →',
            };
            return newMessages;
          });
        },
        // onError
        (error: string) => {
          setIsGenerating(false);
          setMessages((prev) => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1] = {
              ...assistantMessage,
              content: `❌ Error: ${error}`,
            };
            return newMessages;
          });
        }
      );
    } catch (error) {
      setIsGenerating(false);
      setMessages((prev) => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1] = {
          ...assistantMessage,
          content: `❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        };
        return newMessages;
      });
    }
  };

  const handleDeploy = async () => {
    if (!generatedCode) {
      alert('No code to deploy! Generate some code first.');
      return;
    }

    const spaceName = prompt('Enter HuggingFace Space name (or leave empty for auto-generated):');
    if (spaceName === null) return; // User cancelled

    try {
      const response = await apiClient.deploy({
        code: generatedCode,
        space_name: spaceName || undefined,
        language: selectedLanguage,
      });

      if (response.success) {
        // Open the space URL in a new tab
        window.open(response.space_url, '_blank');
        
        // Show success message
        const isDev = response.dev_mode;
        const message = isDev 
          ? '🚀 Opening HuggingFace Spaces creation page...\nPlease complete the space setup in the new tab.'
          : `✅ Deployed successfully!\n\nOpening: ${response.space_url}`;
        alert(message);
      } else {
        alert(`Deployment failed: ${response.message}`);
      }
    } catch (error) {
      alert(`Deployment error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleClear = () => {
    if (confirm('Clear all messages and code?')) {
      setMessages([]);
      setGeneratedCode('');
    }
  };

  return (
    <div className="h-screen flex flex-col bg-[#1d1d1f]">
      <Header />
      
      {/* VS Code layout with Apple styling */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Chat Panel */}
        <div className="w-80 bg-[#28282a] border-r border-[#48484a] flex flex-col shadow-xl">
          {/* Panel Header */}
          <div className="flex items-center px-5 py-4 bg-[#28282a] border-b border-[#48484a]">
            <div className="flex space-x-2">
              <div className="w-3 h-3 rounded-full bg-[#ff5f57] shadow-sm"></div>
              <div className="w-3 h-3 rounded-full bg-[#ffbd2e] shadow-sm"></div>
              <div className="w-3 h-3 rounded-full bg-[#28ca41] shadow-sm"></div>
            </div>
            <span className="ml-4 text-sm font-semibold text-[#e5e5e7] tracking-tight">Chat</span>
          </div>
          
          {/* Chat Panel */}
          <div className="flex-1 overflow-hidden">
            <ChatInterface
              messages={messages}
              onSendMessage={handleSendMessage}
              isGenerating={isGenerating}
              isAuthenticated={isAuthenticated}
            />
          </div>
        </div>

        {/* Center - Editor Group */}
        <div className="flex-1 flex flex-col bg-[#1d1d1f]">
          {/* Tab Bar */}
          <div className="flex items-center px-5 h-11 bg-[#28282a] border-b border-[#48484a]">
            <div className="flex items-center space-x-2">
              <div className="px-4 py-1.5 bg-[#1d1d1f] border-t-2 border-[#007aff] text-sm text-[#e5e5e7] rounded-t-lg shadow-sm font-medium">
                {selectedLanguage}.{selectedLanguage === 'html' ? 'html' : selectedLanguage === 'python' ? 'py' : 'js'}
              </div>
            </div>
            <div className="ml-auto flex items-center space-x-3 text-xs text-[#a1a1a6]">
              {isGenerating && (
                <span className="flex items-center space-x-1.5 animate-pulse">
                  <div className="w-2 h-2 bg-[#007aff] rounded-full shadow-lg"></div>
                  <span className="font-medium">Generating...</span>
                </span>
              )}
              <span className="font-semibold tracking-wide">{selectedLanguage.toUpperCase()}</span>
            </div>
          </div>
          
          {/* Editor */}
          <div className="flex-1">
            <CodeEditor
              code={generatedCode || '// Your generated code will appear here...\n// Select a model and start chatting to generate code'}
              language={selectedLanguage}
              onChange={setGeneratedCode}
              readOnly={isGenerating}
            />
          </div>
        </div>

        {/* Right Sidebar - Configuration Panel */}
        <div className="w-72 bg-[#28282a] border-l border-[#48484a] overflow-y-auto shadow-xl">
          <ControlPanel
            selectedLanguage={selectedLanguage}
            selectedModel={selectedModel}
            onLanguageChange={setSelectedLanguage}
            onModelChange={setSelectedModel}
            onDeploy={handleDeploy}
            onClear={handleClear}
            isGenerating={isGenerating}
          />
        </div>
      </main>

      {/* Status Bar - Apple style */}
      <footer className="h-7 bg-[#28282a] border-t border-[#48484a] text-[#a1a1a6] text-xs flex items-center px-5 justify-between font-medium">
        <div className="flex items-center space-x-5">
          <span className="flex items-center space-x-1.5">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 16 16">
              <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0zM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0z"/>
            </svg>
            <span>AnyCoder</span>
          </span>
          <span className="flex items-center space-x-1.5">
            {isAuthenticated ? (
              <>
                <span className="w-1.5 h-1.5 bg-[#30d158] rounded-full"></span>
                <span>Connected</span>
              </>
            ) : (
              <>
                <span className="w-1.5 h-1.5 bg-[#ff9f0a] rounded-full"></span>
                <span>Not authenticated</span>
              </>
            )}
          </span>
        </div>
        <div className="flex items-center space-x-5">
          <span>{messages.length} messages</span>
          <a
            href="https://huggingface.co/spaces/akhaliq/anycoder"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-[#e5e5e7] transition-colors"
          >
            Built with anycoder
          </a>
        </div>
      </footer>
    </div>
  );
}


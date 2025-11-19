'use client';

import { useState, useEffect } from 'react';
import { flushSync } from 'react-dom';
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
  const [selectedModel, setSelectedModel] = useState('gemini-3.0-pro');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentRepoId, setCurrentRepoId] = useState<string | null>(null);  // Track imported/deployed space
  const [username, setUsername] = useState<string | null>(null);  // Track current user
  
  // Mobile view state: 'chat', 'editor', or 'settings'
  const [mobileView, setMobileView] = useState<'chat' | 'editor' | 'settings'>('editor');

  useEffect(() => {
    checkAuth();
    // Check auth status every second to catch OAuth redirects
    const interval = setInterval(checkAuth, 1000);
    return () => clearInterval(interval);
  }, []);

  const checkAuth = async () => {
    const authenticated = checkIsAuthenticated();
    setIsAuthenticated(authenticated);
    
    // Make sure API client has the token
    if (authenticated) {
      const token = getStoredToken();
      if (token) {
        apiClient.setToken(token);
        
        // Get username from auth status
        try {
          const authStatus = await apiClient.getAuthStatus();
          if (authStatus.username) {
            setUsername(authStatus.username);
          }
        } catch (error) {
          console.error('Failed to get username:', error);
        }
      }
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!isAuthenticated) {
      alert('Please sign in with HuggingFace first! Click the "Sign in with Hugging Face" button in the header.');
      return;
    }

    // If there's existing code, include it in the message context for modifications
    let enhancedMessage = message;
    const hasRealCode = generatedCode && 
                        generatedCode.length > 50 && 
                        !generatedCode.includes('Your generated code will appear here');
    
    if (hasRealCode) {
      enhancedMessage = `I have existing code in the editor. Please modify it based on my request.\n\nCurrent code:\n\`\`\`${selectedLanguage}\n${generatedCode}\n\`\`\`\n\nMy request: ${message}`;
    }

    // Add user message (show original message to user, but send enhanced to API)
    const userMessage: Message = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsGenerating(true);
    
    // Clear previous code to show streaming from start
    setGeneratedCode('');

    // Prepare request with enhanced query that includes current code
    const request: CodeGenerationRequest = {
      query: enhancedMessage,
      language: selectedLanguage,
      model_id: selectedModel,
      provider: 'auto',
      history: messages.map((m) => [m.role, m.content]),
      agent_mode: false,
    };

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
        // onChunk - Update code editor in real-time with immediate flush
        (chunk: string) => {
          console.log('[Stream] Received chunk:', chunk.substring(0, 50), '... (length:', chunk.length, ')');
          // Use flushSync to force immediate DOM update without React batching
          flushSync(() => {
            setGeneratedCode((prevCode) => {
              const newCode = prevCode + chunk;
              console.log('[Stream] Total code length:', newCode.length);
              return newCode;
            });
          });
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
      alert('No code to publish! Generate some code first.');
      return;
    }

    // Determine if we're updating an existing space or creating a new one
    let existingRepoId = currentRepoId;
    
    // If we have a current repo, check if user owns it
    if (currentRepoId && username) {
      const ownsSpace = currentRepoId.startsWith(`${username}/`);
      if (ownsSpace) {
        // Update existing space without asking
        console.log('[Deploy] Updating existing space:', currentRepoId);
      } else {
        // User doesn't own the imported space, create a new one
        existingRepoId = null;
        console.log('[Deploy] Creating new space (user does not own imported space)');
      }
    } else {
      console.log('[Deploy] Creating new space (no current repo)');
    }

    // Auto-generate space name (never prompt user)
    let spaceName = undefined;  // undefined = backend will auto-generate

    try {
      console.log('[Deploy] ========== DEPLOY START ==========');
      console.log('[Deploy] Current username:', username);
      console.log('[Deploy] Current repo ID (state):', currentRepoId);
      console.log('[Deploy] Existing repo ID (var):', existingRepoId);
      console.log('[Deploy] Space name:', spaceName);
      console.log('[Deploy] Language:', selectedLanguage);
      console.log('[Deploy] Code length:', generatedCode.length);
      console.log('[Deploy] ========================================');
      
      const deployRequest = {
        code: generatedCode,
        space_name: spaceName,
        language: selectedLanguage,
        existing_repo_id: existingRepoId || undefined,
        commit_message: existingRepoId ? 'Update via AnyCoder' : undefined,
      };
      
      console.log('[Deploy] 🚀 Sending request to backend:', JSON.stringify({
        ...deployRequest,
        code: `${deployRequest.code.substring(0, 100)}... (${deployRequest.code.length} chars)`
      }, null, 2));
      
      const response = await apiClient.deploy(deployRequest);

      if (response.success) {
        // Update current repo ID if we got one back
        if (response.repo_id) {
          console.log('[Deploy] Setting currentRepoId to:', response.repo_id);
          setCurrentRepoId(response.repo_id);
        } else if (response.space_url) {
          // Extract repo_id from space_url as fallback
          const match = response.space_url.match(/huggingface\.co\/spaces\/([^\/\s\)]+\/[^\/\s\)]+)/);
          if (match) {
            console.log('[Deploy] Extracted repo_id from URL:', match[1]);
            setCurrentRepoId(match[1]);
          }
        }
        
        // Add deployment message to chat
        const deployMessage: Message = {
          role: 'assistant',
          content: existingRepoId 
            ? `✅ Updated space: ${response.space_url}` 
            : `✅ Published to: ${response.space_url}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, deployMessage]);
        
        // Open the space URL in a new tab
        window.open(response.space_url, '_blank');
        
        // Show success message
        const isDev = response.dev_mode;
        const message = isDev 
          ? '🚀 Opening HuggingFace Spaces creation page...\nPlease complete the space setup in the new tab.'
          : existingRepoId
            ? `✅ Updated successfully!\n\nOpening: ${response.space_url}`
            : `✅ Published successfully!\n\nOpening: ${response.space_url}`;
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

  const handleImport = (code: string, language: Language, importUrl?: string) => {
    console.log('[Import] ========== IMPORT START ==========');
    console.log('[Import] Language:', language);
    console.log('[Import] Import URL:', importUrl);
    console.log('[Import] Current username:', username);
    console.log('[Import] Current repo before import:', currentRepoId);
    
    setGeneratedCode(code);
    setSelectedLanguage(language);
    
    // Extract repo_id from import URL if provided
    if (importUrl) {
      const spaceMatch = importUrl.match(/huggingface\.co\/spaces\/([^\/\s\)]+\/[^\/\s\)]+)/);
      console.log('[Import] Regex match result:', spaceMatch);
      
      if (spaceMatch) {
        const importedRepoId = spaceMatch[1];
        const importedUsername = importedRepoId.split('/')[0];
        
        console.log('[Import] ========================================');
        console.log('[Import] Extracted repo_id:', importedRepoId);
        console.log('[Import] Imported username:', importedUsername);
        console.log('[Import] Logged-in username:', username);
        console.log('[Import] Ownership check:', importedUsername === username);
        console.log('[Import] ========================================');
        
        // Only set as current repo if user owns it
        if (username && importedRepoId.startsWith(`${username}/`)) {
          setCurrentRepoId(importedRepoId);
          console.log('[Import] ✅✅✅ SETTING currentRepoId to:', importedRepoId);
        } else {
          // User doesn't own the imported space, clear current repo
          setCurrentRepoId(null);
          if (!username) {
            console.log('[Import] ⚠️⚠️⚠️ USERNAME IS NULL - Cannot set repo ownership!');
          } else {
            console.log('[Import] ⚠️ User does not own imported space:', importedRepoId, '(username:', username, ')');
          }
        }
      } else {
        console.log('[Import] ⚠️ Could not extract repo_id from URL:', importUrl);
      }
    } else {
      console.log('[Import] No import URL provided');
    }
    
    console.log('[Import] ========== IMPORT END ==========');
    
    // Add messages that include the imported code so LLM can see it
    const userMessage: Message = {
      role: 'user',
      content: importUrl 
        ? `Imported Space from ${importUrl}`
        : `I imported a ${language} project. Here's the code that was imported.`,
      timestamp: new Date().toISOString(),
    };
    
    const assistantMessage: Message = {
      role: 'assistant',
      content: `✅ I've loaded your ${language} project. The code is now in the editor. You can ask me to:\n\n• Modify existing features\n• Add new functionality\n• Fix bugs or improve code\n• Explain how it works\n• Publish it to HuggingFace Spaces\n\nWhat would you like me to help you with?`,
      timestamp: new Date().toISOString(),
    };
    
    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    
    // Switch to editor view on mobile
    setMobileView('editor');
  };

  return (
    <div className="h-screen flex flex-col bg-[#1d1d1f]">
      <Header />
      
      {/* VS Code layout with Apple styling - Responsive */}
      <main className="flex-1 flex overflow-hidden relative">
        {/* Left Sidebar - Chat Panel (Hidden on mobile, shown when mobileView='chat') */}
        <div className={`
          ${mobileView === 'chat' ? 'flex' : 'hidden'} md:flex
          w-full md:w-80 
          bg-[#28282a] border-r border-[#48484a] 
          flex-col shadow-xl
          absolute md:relative inset-0 md:inset-auto z-10 md:z-auto
        `}>
          {/* Panel Header */}
          <div className="flex items-center px-5 py-4 bg-[#28282a] border-b border-[#48484a]">
            <span className="text-sm font-semibold text-[#e5e5e7] tracking-tight">Chat</span>
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

        {/* Center - Editor Group (Always visible on mobile when mobileView='editor', always visible on desktop) */}
        <div className={`
          ${mobileView === 'editor' ? 'flex' : 'hidden'} md:flex
          flex-1 flex-col bg-[#1d1d1f]
          absolute md:relative inset-0 md:inset-auto z-10 md:z-auto
        `}>
          {/* Tab Bar */}
          <div className="flex items-center px-5 h-11 bg-[#28282a] border-b border-[#48484a]">
            <div className="flex items-center space-x-2">
              <div className="px-4 py-1.5 bg-[#1d1d1f] border-t-2 border-[#007aff] text-sm text-[#e5e5e7] rounded-t-lg shadow-sm font-medium">
                {selectedLanguage}.{
                  selectedLanguage === 'html' ? 'html' : 
                  selectedLanguage === 'gradio' || selectedLanguage === 'streamlit' ? 'py' : 
                  selectedLanguage === 'transformers.js' ? 'js' :
                  selectedLanguage === 'comfyui' ? 'json' :
                  'jsx'
                }
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

        {/* Right Sidebar - Configuration Panel (Hidden on mobile, shown when mobileView='settings') */}
        <div className={`
          ${mobileView === 'settings' ? 'flex' : 'hidden'} md:flex
          w-full md:w-72
          bg-[#28282a] border-l border-[#48484a] 
          overflow-y-auto shadow-xl
          absolute md:relative inset-0 md:inset-auto z-10 md:z-auto
          flex-col
        `}>
          <ControlPanel
            selectedLanguage={selectedLanguage}
            selectedModel={selectedModel}
            onLanguageChange={setSelectedLanguage}
            onModelChange={setSelectedModel}
            onDeploy={handleDeploy}
            onClear={handleClear}
            onImport={handleImport}
            isGenerating={isGenerating}
          />
        </div>
      </main>

      {/* Mobile Bottom Navigation (visible only on mobile) */}
      <nav className="md:hidden bg-[#28282a] border-t border-[#48484a] flex items-center justify-around h-16 px-2 safe-area-bottom">
        <button
          onClick={() => setMobileView('chat')}
          className={`flex flex-col items-center justify-center flex-1 py-2 rounded-lg transition-all ${
            mobileView === 'chat' 
              ? 'text-[#007aff] bg-[#1d1d1f]' 
              : 'text-[#a1a1a6] hover:text-[#e5e5e7]'
          }`}
        >
          <svg className="w-6 h-6 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <span className="text-xs font-medium">Chat</span>
        </button>
        
        <button
          onClick={() => setMobileView('editor')}
          className={`flex flex-col items-center justify-center flex-1 py-2 rounded-lg transition-all ${
            mobileView === 'editor' 
              ? 'text-[#007aff] bg-[#1d1d1f]' 
              : 'text-[#a1a1a6] hover:text-[#e5e5e7]'
          }`}
        >
          <svg className="w-6 h-6 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
          </svg>
          <span className="text-xs font-medium">Code</span>
        </button>
        
        <button
          onClick={() => setMobileView('settings')}
          className={`flex flex-col items-center justify-center flex-1 py-2 rounded-lg transition-all ${
            mobileView === 'settings' 
              ? 'text-[#007aff] bg-[#1d1d1f]' 
              : 'text-[#a1a1a6] hover:text-[#e5e5e7]'
          }`}
        >
          <svg className="w-6 h-6 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="text-xs font-medium">Settings</span>
        </button>
      </nav>

      {/* Status Bar - Apple style (hidden on mobile) */}
      <footer className="hidden md:flex h-7 bg-[#28282a] border-t border-[#48484a] text-[#a1a1a6] text-xs items-center px-5 justify-between font-medium">
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


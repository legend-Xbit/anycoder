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
  // Initialize messages as empty array (will load from localStorage in useEffect)
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

  // Load messages from localStorage on mount (client-side only to avoid hydration issues)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('anycoder_messages');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          console.log('[localStorage] Loaded messages from localStorage:', parsed.length, 'messages');
          setMessages(parsed);
        } catch (e) {
          console.error('[localStorage] Failed to parse saved messages:', e);
        }
      }
    }
  }, []); // Empty deps = run once on mount

  // Save messages to localStorage whenever they change (CRITICAL FOR PERSISTENCE!)
  useEffect(() => {
    if (typeof window !== 'undefined' && messages.length > 0) {
      localStorage.setItem('anycoder_messages', JSON.stringify(messages));
      console.log('[localStorage] Saved', messages.length, 'messages to localStorage');
    }
  }, [messages]);

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
    console.log('[Deploy] 🎬 handleDeploy called');
    console.log('[Deploy] generatedCode exists?', !!generatedCode);
    console.log('[Deploy] generatedCode length:', generatedCode?.length);
    console.log('[Deploy] generatedCode preview:', generatedCode?.substring(0, 200));
    
    if (!generatedCode) {
      alert('No code to publish! Generate some code first.');
      return;
    }

    // Get current username (fetch if not loaded)
    let currentUsername = username;
    if (!currentUsername) {
      console.log('[Deploy] Username not in state, fetching from auth...');
      try {
        const authStatus = await apiClient.getAuthStatus();
        if (authStatus.username) {
          currentUsername = authStatus.username;
          setUsername(authStatus.username);
          console.log('[Deploy] Fetched username:', currentUsername);
        }
      } catch (e) {
        console.error('[Deploy] Could not get username:', e);
        // Don't fail - let backend handle auth
      }
    }

    // SAME LOGIC AS GRADIO VERSION: Parse message history to find existing space
    let existingSpace: string | null = null;
    
    // Look for previous deployment or imported space in history
    console.log('[Deploy] ========== DEBUG START ==========');
    console.log('[Deploy] Total messages in history:', messages.length);
    console.log('[Deploy] Current username:', currentUsername);
    console.log('[Deploy] Auth status:', isAuthenticated ? 'authenticated' : 'not authenticated');
    console.log('[Deploy] Messages:', JSON.stringify(messages, null, 2));
    
    if (messages.length > 0 && currentUsername) {
      console.log('[Deploy] Scanning message history FORWARD (oldest first) - MATCHING GRADIO LOGIC...');
      console.log('[Deploy] Total messages to scan:', messages.length);
      
      // EXACT GRADIO LOGIC: Scan forward (oldest first) and stop at first match
      // Gradio: for user_msg, assistant_msg in history:
      for (let i = 0; i < messages.length; i++) {
        const msg = messages[i];
        console.log(`[Deploy] Checking message ${i}:`, {
          role: msg.role,
          contentPreview: msg.content.substring(0, 100)
        });
        
        // Check assistant messages for deployment confirmations
        if (msg.role === 'assistant') {
          // Check for "✅ Deployed!" message
          if (msg.content.includes('✅ Deployed!')) {
            const match = msg.content.match(/huggingface\.co\/spaces\/([^\/\s\)]+\/[^\/\s\)]+)/);
            if (match) {
              existingSpace = match[1];
              console.log('[Deploy] ✅ Found "✅ Deployed!" - existing_space:', existingSpace);
              break;
            }
          }
          // Check for "✅ Updated!" message
          else if (msg.content.includes('✅ Updated!')) {
            const match = msg.content.match(/huggingface\.co\/spaces\/([^\/\s\)]+\/[^\/\s\)]+)/);
            if (match) {
              existingSpace = match[1];
              console.log('[Deploy] ✅ Found "✅ Updated!" - existing_space:', existingSpace);
              break;
            }
          }
        }
        // Check user messages for imports
        else if (msg.role === 'user' && msg.content.startsWith('Imported Space from')) {
          console.log('[Deploy] 🎯 Found "Imported Space from" message');
          const match = msg.content.match(/huggingface\.co\/spaces\/([^\/\s\)]+\/[^\/\s\)]+)/);
          if (match) {
            const importedSpace = match[1];
            console.log('[Deploy] Extracted imported space:', importedSpace);
            console.log('[Deploy] Checking ownership - user:', currentUsername, 'space:', importedSpace);
            
            // Only use if user owns it (EXACT GRADIO LOGIC)
            if (importedSpace.startsWith(`${currentUsername}/`)) {
              existingSpace = importedSpace;
              console.log('[Deploy] ✅✅✅ USER OWNS - Will update:', existingSpace);
              break;
            } else {
              console.log('[Deploy] ⚠️ User does NOT own - will create new space');
              // existing_space remains None (create new deployment)
            }
          }
        }
      }
      
      console.log('[Deploy] Final existingSpace value:', existingSpace);
    } else {
      console.log('[Deploy] Skipping scan - no messages or no username');
      console.log('[Deploy] Messages length:', messages.length);
      console.log('[Deploy] Username:', currentUsername);
    }
    console.log('[Deploy] ========== DEBUG END ==========');

    // TEMPORARY DEBUG: Show what will be sent
    console.log('[Deploy] 🚀 ABOUT TO DEPLOY:');
    console.log('[Deploy] - Language:', selectedLanguage);
    console.log('[Deploy] - existing_repo_id:', existingSpace || 'None (new deployment)');
    console.log('[Deploy] - Username:', currentUsername);

    // Auto-generate space name (never prompt user)
    let spaceName = undefined;  // undefined = backend will auto-generate

    try {
      console.log('[Deploy] ========== DEPLOY START (Gradio-style history parsing) ==========');
      console.log('[Deploy] Username:', currentUsername);
      console.log('[Deploy] Existing space from history:', existingSpace);
      console.log('[Deploy] Will create new space?', !existingSpace);
      console.log('[Deploy] =================================================================');
      
      // Build deploy request, omitting undefined fields
      const deployRequest: any = {
        code: generatedCode,
        language: selectedLanguage,
      };
      
      // Only include optional fields if they have values
      if (spaceName) {
        deployRequest.space_name = spaceName;
      }
      if (existingSpace) {
        deployRequest.existing_repo_id = existingSpace;
        deployRequest.commit_message = 'Update via AnyCoder';
      }
      
      console.log('[Deploy] 🚀 Sending to backend:', {
        existing_repo_id: deployRequest.existing_repo_id,
        space_name: deployRequest.space_name,
        language: deployRequest.language,
        has_code: !!deployRequest.code,
        code_length: deployRequest.code?.length
      });
      console.log('[Deploy] Full request object:', JSON.stringify(deployRequest, null, 2).substring(0, 500));
      
      const response = await apiClient.deploy(deployRequest);
      console.log('[Deploy] ✅ Response received:', response);

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
        
        // Add deployment message to chat (EXACT Gradio format with markdown link)
        const deployMessage: Message = {
          role: 'assistant',
          content: existingSpace 
            ? `✅ Updated! [Open your Space here](${response.space_url})` 
            : `✅ Deployed! [Open your Space here](${response.space_url})`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, deployMessage]);
        
        // Open the space URL in a new tab
        window.open(response.space_url, '_blank');
        
        // Show success message
        const isDev = response.dev_mode;
        const message = isDev 
          ? '🚀 Opening HuggingFace Spaces creation page...\nPlease complete the space setup in the new tab.'
          : existingSpace
            ? `✅ Updated successfully!\n\nOpening: ${response.space_url}`
            : `✅ Published successfully!\n\nOpening: ${response.space_url}`;
        alert(message);
      } else {
        alert(`Deployment failed: ${response.message}`);
      }
    } catch (error: any) {
      console.error('[Deploy] Full error object:', error);
      console.error('[Deploy] Error response:', error.response);
      console.error('[Deploy] Error data:', error.response?.data);
      
      const errorMessage = error.response?.data?.detail 
        || error.response?.data?.message 
        || error.message 
        || 'Unknown error';
      
      alert(`Deployment error: ${errorMessage}\n\nCheck console for details.`);
    }
  };

  const handleClear = () => {
    if (confirm('Clear all messages and code?')) {
      setMessages([]);
      setGeneratedCode('');
      // Clear localStorage to remove import history
      if (typeof window !== 'undefined') {
        localStorage.removeItem('anycoder_messages');
        console.log('[localStorage] Cleared messages from localStorage');
      }
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
                {selectedLanguage === 'html' ? 'app.html' :
                 selectedLanguage === 'gradio' || selectedLanguage === 'streamlit' ? 'app.py' : 
                 selectedLanguage === 'transformers.js' ? 'app.js' :
                 selectedLanguage === 'comfyui' ? 'app.json' :
                 selectedLanguage === 'react' ? 'app.jsx' :
                 `${selectedLanguage}.txt`}
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


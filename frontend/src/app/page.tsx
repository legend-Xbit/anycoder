'use client';

import { useState, useEffect, useRef } from 'react';
import { flushSync } from 'react-dom';
import Header from '@/components/Header';
import LandingPage from '@/components/LandingPage';
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
  const [selectedModel, setSelectedModel] = useState('zai-org/GLM-4.6');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentRepoId, setCurrentRepoId] = useState<string | null>(null);  // Track imported/deployed space
  const [username, setUsername] = useState<string | null>(null);  // Track current user
  
  // Landing page state - show landing page if no messages exist
  const [showLandingPage, setShowLandingPage] = useState(true);
  
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
          // If there are existing messages, show the full UI
          if (parsed.length > 0) {
            setShowLandingPage(false);
          }
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

  // Track if we've attempted to fetch username to avoid repeated failures
  const usernameFetchAttemptedRef = useRef(false);
  // Track if backend appears to be unavailable (to avoid repeated failed requests)
  const backendUnavailableRef = useRef(false);

  // Check auth on mount and handle OAuth callback
  useEffect(() => {
    checkAuth();
    
    // Check for OAuth callback in URL (handles ?session=token)
    // initializeOAuth already handles this, but we call checkAuth to sync state
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('session')) {
      // OAuth callback - reset both flags and check auth after a brief delay
      usernameFetchAttemptedRef.current = false;
      backendUnavailableRef.current = false; // Reset backend status on OAuth callback
      setTimeout(() => checkAuth(), 200);
    }
  }, []); // Only run once on mount

  // Listen for storage changes (e.g., logout from another tab)
  // Note: storage events only fire in OTHER tabs, not the current one
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'hf_oauth_token' || e.key === 'hf_user_info') {
        // Only reset username fetch if we have a token (might be logging in)
        if (e.newValue) {
          usernameFetchAttemptedRef.current = false;
          backendUnavailableRef.current = false; // Reset backend status on login
        }
        checkAuth();
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  // Listen for authentication expiration events
  useEffect(() => {
    const handleAuthExpired = (e: CustomEvent) => {
      console.log('[Auth] Session expired:', e.detail?.message);
      // Clear authentication state
      setIsAuthenticated(false);
      setUsername(null);
      apiClient.setToken(null);
      
      // Show alert to user
      if (typeof window !== 'undefined') {
        alert(e.detail?.message || 'Your session has expired. Please sign in again.');
      }
    };

    window.addEventListener('auth-expired', handleAuthExpired as EventListener);
    return () => window.removeEventListener('auth-expired', handleAuthExpired as EventListener);
  }, []);

  // Listen for window focus (user returns to tab after OAuth redirect)
  // Only check if backend was available before or if we're authenticated with token
  useEffect(() => {
    const handleFocus = () => {
      // Only reset and check if we're authenticated (might have logged in elsewhere)
      // Don't reset if backend is known to be unavailable and we're not authenticated
      const authenticated = checkIsAuthenticated();
      if (authenticated) {
        usernameFetchAttemptedRef.current = false;
        backendUnavailableRef.current = false; // Reset backend status - might be back up
      }
      checkAuth();
    };

    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, []);

  const checkAuth = async () => {
    const authenticated = checkIsAuthenticated();
    setIsAuthenticated(authenticated);
    
    // Make sure API client has the token or clears it
    if (authenticated) {
      const token = getStoredToken();
      if (token) {
        apiClient.setToken(token);
        
        // Get username from auth status (only if we don't have it yet and backend is available)
        // Skip if backend is known to be unavailable to avoid repeated failed requests
        if (!username && !usernameFetchAttemptedRef.current && !backendUnavailableRef.current) {
          usernameFetchAttemptedRef.current = true;
          try {
            const authStatus = await apiClient.getAuthStatus();
            if (authStatus.username) {
              setUsername(authStatus.username);
              backendUnavailableRef.current = false; // Backend is working
            }
          } catch (error: any) {
            // Check if this is a connection error
            const isConnectionError = 
              error.code === 'ECONNABORTED' || 
              error.code === 'ECONNRESET' || 
              error.code === 'ECONNREFUSED' ||
              error.message?.includes('socket hang up') ||
              error.message?.includes('timeout') ||
              error.message?.includes('Network Error') ||
              error.response?.status === 503 ||
              error.response?.status === 502;
            
            if (isConnectionError) {
              // Mark backend as unavailable to avoid repeated requests
              backendUnavailableRef.current = true;
              // Don't reset attempt flag - keep it true so we don't retry until explicitly reset
              // This prevents repeated failed requests when backend is down
            } else {
              // Non-connection error - log it and reset attempt flag
              console.error('Failed to get username:', error);
              usernameFetchAttemptedRef.current = false;
            }
          }
        }
      } else {
        // Token missing but authenticated flag is true - clear state
        setIsAuthenticated(false);
        if (username) {
          setUsername(null);
        }
        usernameFetchAttemptedRef.current = false;
        backendUnavailableRef.current = false;
      }
    } else {
      // Not authenticated - clear username and reset flags
      apiClient.setToken(null);
      if (username) {
        setUsername(null);
      }
      usernameFetchAttemptedRef.current = false;
      // Keep backendUnavailableRef as is - it's useful information even when not authenticated
    }
  };

  const handleSendMessage = async (message: string, overrideLanguage?: Language, overrideModel?: string) => {
    if (!isAuthenticated) {
      alert('Please sign in with HuggingFace first! Click the "Sign in with Hugging Face" button in the header.');
      return;
    }

    // Hide landing page and show full UI when first message is sent
    if (showLandingPage) {
      setShowLandingPage(false);
    }

    // Use override values if provided, otherwise use state
    const language = overrideLanguage || selectedLanguage;
    const model = overrideModel || selectedModel;

    // Update state if override values provided
    if (overrideLanguage) {
      setSelectedLanguage(overrideLanguage);
    }
    if (overrideModel) {
      setSelectedModel(overrideModel);
    }

    // If there's existing code, include it in the message context for modifications
    let enhancedMessage = message;
    const hasRealCode = generatedCode && 
                        generatedCode.length > 50 && 
                        !generatedCode.includes('Your generated code will appear here');
    
    if (hasRealCode) {
      enhancedMessage = `I have existing code in the editor. Please modify it based on my request.\n\nCurrent code:\n\`\`\`${language}\n${generatedCode}\n\`\`\`\n\nMy request: ${message}`;
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
      language: language,
      model_id: model,
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
      setShowLandingPage(true);
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

  // Handle landing page prompt submission
  const handleLandingPageStart = async (prompt: string, language: Language, modelId: string) => {
    // Hide landing page immediately for smooth transition
    setShowLandingPage(false);
    // Send the message with the selected language and model
    await handleSendMessage(prompt, language, modelId);
  };

  // Show landing page if no messages and showLandingPage is true
  if (showLandingPage && messages.length === 0) {
    return (
      <div className="min-h-screen animate-in fade-in duration-300">
        <LandingPage 
          onStart={handleLandingPageStart}
          isAuthenticated={isAuthenticated}
          initialLanguage={selectedLanguage}
          initialModel={selectedModel}
          onAuthChange={checkAuth}
        />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-[#000000] animate-in fade-in duration-300">
      <Header />
      
      {/* Apple-style layout - Responsive */}
      <main className="flex-1 flex overflow-hidden relative">
        {/* Left Sidebar - Chat Panel (Hidden on mobile, shown when mobileView='chat') */}
        <div className={`
          ${mobileView === 'chat' ? 'flex' : 'hidden'} md:flex
          w-full md:w-80 
          bg-[#000000] border-r border-[#424245]/30 
          flex-col
          absolute md:relative inset-0 md:inset-auto z-10 md:z-auto
        `}>
          {/* Panel Header */}
          <div className="flex items-center px-4 py-3 bg-[#000000] border-b border-[#424245]/30">
            <span className="text-sm font-medium text-[#f5f5f7]">Chat</span>
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
          flex-1 flex-col bg-[#000000]
          absolute md:relative inset-0 md:inset-auto z-10 md:z-auto
        `}>
          {/* Tab Bar */}
          <div className="flex items-center px-4 h-10 bg-[#1d1d1f] border-b border-[#424245]/30">
            <div className="flex items-center space-x-2">
              <div className="px-3 py-1 bg-[#2d2d2f] text-sm text-[#f5f5f7] rounded-t-lg font-normal border-t border-x border-[#424245]/50">
                {selectedLanguage === 'html' ? 'app.html' :
                 selectedLanguage === 'gradio' || selectedLanguage === 'streamlit' ? 'app.py' : 
                 selectedLanguage === 'transformers.js' ? 'app.js' :
                 selectedLanguage === 'comfyui' ? 'app.json' :
                 selectedLanguage === 'react' ? 'app.jsx' :
                 `${selectedLanguage}.txt`}
              </div>
            </div>
            <div className="ml-auto flex items-center space-x-3 text-xs text-[#86868b]">
              {isGenerating && (
                <span className="flex items-center space-x-1.5">
                  <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></div>
                  <span>Generating...</span>
                </span>
              )}
              <span className="font-medium">{selectedLanguage.toUpperCase()}</span>
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
          bg-[#000000] border-l border-[#424245]/30 
          overflow-y-auto
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
      <nav className="md:hidden bg-[#000000]/95 backdrop-blur-xl border-t border-[#424245]/20 flex items-center justify-around h-14 px-2 safe-area-bottom">
        <button
          onClick={() => setMobileView('chat')}
          className={`flex flex-col items-center justify-center flex-1 py-1.5 transition-all ${
            mobileView === 'chat' 
              ? 'text-white' 
              : 'text-[#86868b]'
          }`}
        >
          <svg className="w-5 h-5 mb-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <span className="text-[10px]">Chat</span>
        </button>
        
        <button
          onClick={() => setMobileView('editor')}
          className={`flex flex-col items-center justify-center flex-1 py-1.5 transition-all ${
            mobileView === 'editor' 
              ? 'text-white' 
              : 'text-[#86868b]'
          }`}
        >
          <svg className="w-5 h-5 mb-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
          </svg>
          <span className="text-[10px]">Code</span>
        </button>
        
        <button
          onClick={() => setMobileView('settings')}
          className={`flex flex-col items-center justify-center flex-1 py-1.5 transition-all ${
            mobileView === 'settings' 
              ? 'text-white' 
              : 'text-[#86868b]'
          }`}
        >
          <svg className="w-5 h-5 mb-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="text-[10px]">Settings</span>
        </button>
      </nav>

      {/* Status Bar - Apple style (hidden on mobile) */}
      <footer className="hidden md:flex h-6 bg-[#000000] border-t border-[#424245]/20 text-[#86868b] text-[11px] items-center px-4 justify-between">
        <div className="flex items-center space-x-4">
          <span>AnyCoder</span>
          <span className="flex items-center gap-1.5">
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
        <div className="flex items-center space-x-4">
          <span>{messages.length} messages</span>
        </div>
      </footer>
    </div>
  );
}



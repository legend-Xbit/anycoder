'use client';

import { useState, useEffect, useRef } from 'react';
import { apiClient } from '@/lib/api';
import { 
  initializeOAuth, 
  loginWithHuggingFace, 
  loginDevMode,
  logout, 
  getStoredUserInfo, 
  isAuthenticated as checkIsAuthenticated,
  isDevelopmentMode 
} from '@/lib/auth';
import type { Model, Language } from '@/types';
import type { OAuthUserInfo } from '@/lib/auth';

interface LandingPageProps {
  onStart: (prompt: string, language: Language, modelId: string, repoId?: string, shouldCreatePR?: boolean) => void;
  onImport?: (code: string, language: Language, importUrl?: string) => void;
  isAuthenticated: boolean;
  initialLanguage?: Language;
  initialModel?: string;
  onAuthChange?: () => void;
}

export default function LandingPage({ 
  onStart, 
  onImport,
  isAuthenticated,
  initialLanguage = 'html',
  initialModel = 'deepseek-ai/DeepSeek-V3.2-Exp',
  onAuthChange
}: LandingPageProps) {
  const [prompt, setPrompt] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState<Language>(initialLanguage);
  const [selectedModel, setSelectedModel] = useState<string>(initialModel);
  const [models, setModels] = useState<Model[]>([]);
  const [languages, setLanguages] = useState<Language[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Auth states
  const [userInfo, setUserInfo] = useState<OAuthUserInfo | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [showDevLogin, setShowDevLogin] = useState(false);
  const [devUsername, setDevUsername] = useState('');
  const isDevMode = isDevelopmentMode();
  
  // Dropdown states
  const [showLanguageDropdown, setShowLanguageDropdown] = useState(false);
  const [showModelDropdown, setShowModelDropdown] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [showRedesignDialog, setShowRedesignDialog] = useState(false);
  const languageDropdownRef = useRef<HTMLDivElement>(null);
  const modelDropdownRef = useRef<HTMLDivElement>(null);
  const importDialogRef = useRef<HTMLDivElement>(null);
  const redesignDialogRef = useRef<HTMLDivElement>(null);
  
  // Trending apps state
  const [trendingApps, setTrendingApps] = useState<any[]>([]);
  
  // Import project state
  const [importUrl, setImportUrl] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState('');
  
  // Redesign project state
  const [redesignUrl, setRedesignUrl] = useState('');
  const [isRedesigning, setIsRedesigning] = useState(false);
  const [redesignError, setRedesignError] = useState('');
  const [createPR, setCreatePR] = useState(false); // Default to normal redesign (not PR)

  // Debug effect for dropdown state
  useEffect(() => {
    console.log('showModelDropdown state changed to:', showModelDropdown);
  }, [showModelDropdown]);

  // Debug effect for models state
  useEffect(() => {
    console.log('models state changed, length:', models.length, 'models:', models);
  }, [models]);

  useEffect(() => {
    console.log('Component mounted, initial load starting...');
    loadData();
    handleOAuthInit();
    loadTrendingApps();
    // Check auth status periodically to catch OAuth redirects
    const interval = setInterval(() => {
      const authenticated = checkIsAuthenticated();
      if (authenticated && !userInfo) {
        handleOAuthInit();
      }
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleOAuthInit = async () => {
    setIsAuthLoading(true);
    try {
      const oauthResult = await initializeOAuth();
      
      if (oauthResult) {
        setUserInfo(oauthResult.userInfo);
        apiClient.setToken(oauthResult.accessToken);
        if (onAuthChange) onAuthChange();
      } else {
        const storedUserInfo = getStoredUserInfo();
        if (storedUserInfo) {
          setUserInfo(storedUserInfo);
        }
      }
    } catch (error) {
      console.error('OAuth initialization error:', error);
    } finally {
      setIsAuthLoading(false);
    }
  };

  const handleLogin = async () => {
    try {
      await loginWithHuggingFace();
    } catch (error) {
      console.error('Login failed:', error);
      alert('Failed to start login process. Please try again.');
    }
  };

  const handleLogout = () => {
    logout();
    apiClient.logout();
    setUserInfo(null);
    if (onAuthChange) onAuthChange();
    window.location.reload();
  };

  const handleDevLogin = () => {
    if (!devUsername.trim()) {
      alert('Please enter a username');
      return;
    }
    
    try {
      const result = loginDevMode(devUsername);
      setUserInfo(result.userInfo);
      apiClient.setToken(result.accessToken);
      setShowDevLogin(false);
      setDevUsername('');
      if (onAuthChange) onAuthChange();
    } catch (error) {
      console.error('Dev login failed:', error);
      alert('Failed to login in dev mode');
    }
  };

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (languageDropdownRef.current && !languageDropdownRef.current.contains(event.target as Node)) {
        setShowLanguageDropdown(false);
      }
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(event.target as Node)) {
        setShowModelDropdown(false);
      }
      if (importDialogRef.current && !importDialogRef.current.contains(event.target as Node)) {
        setShowImportDialog(false);
      }
      if (redesignDialogRef.current && !redesignDialogRef.current.contains(event.target as Node)) {
        setShowRedesignDialog(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const loadData = async () => {
    console.log('loadData called');
    setIsLoading(true);
    await Promise.all([loadModels(), loadLanguages()]);
    setIsLoading(false);
    console.log('loadData completed');
  };

  const loadModels = async () => {
    try {
      console.log('Loading models...');
      const modelsList = await apiClient.getModels();
      console.log('Models loaded successfully:', modelsList);
      console.log('Number of models:', modelsList.length);
      setModels(modelsList);
      console.log('Models state updated');
    } catch (error) {
      console.error('Failed to load models:', error);
      setModels([]); // Set empty array on error
    }
  };

  const loadLanguages = async () => {
    try {
      const { languages: languagesList } = await apiClient.getLanguages();
      setLanguages(languagesList);
    } catch (error) {
      console.error('Failed to load languages:', error);
    }
  };

  const loadTrendingApps = async () => {
    try {
      const apps = await apiClient.getTrendingAnycoderApps();
      setTrendingApps(apps);
    } catch (error) {
      console.error('Failed to load trending apps:', error);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim() && isAuthenticated) {
      onStart(prompt.trim(), selectedLanguage, selectedModel);
    } else if (!isAuthenticated) {
      alert('Please sign in with HuggingFace first!');
    }
  };

  const formatLanguageName = (lang: Language) => {
    if (lang === 'html') return 'HTML';
    if (lang === 'transformers.js') return 'Transformers.js';
    if (lang === 'comfyui') return 'ComfyUI';
    return lang.charAt(0).toUpperCase() + lang.slice(1);
  };

  const handleImportProject = async () => {
    if (!importUrl.trim()) {
      setImportError('Please enter a valid URL');
      return;
    }

    if (!isAuthenticated) {
      alert('Please sign in with HuggingFace first!');
      return;
    }

    setIsImporting(true);
    setImportError('');

    try {
      console.log('[Import] ========== STARTING IMPORT ==========');
      console.log('[Import] Import URL:', importUrl);
      
      // Extract space ID from URL for duplication
      const spaceMatch = importUrl.match(/huggingface\.co\/spaces\/([^\/\s\)]+\/[^\/\s\)]+)/);
      console.log('[Import] Space regex match result:', spaceMatch);
      
      if (spaceMatch) {
        // This is a HuggingFace Space - duplicate it
        const fromSpaceId = spaceMatch[1];
        console.log('[Import] ✅ Detected HF Space - will duplicate:', fromSpaceId);
        console.log('[Import] Calling apiClient.duplicateSpace...');
        
        const duplicateResult = await apiClient.duplicateSpace(fromSpaceId);
        console.log('[Import] Duplicate API response:', duplicateResult);
        
        if (duplicateResult.success) {
          console.log('[Import] ========== DUPLICATE SUCCESS ==========');
          console.log('[Import] Duplicated space URL:', duplicateResult.space_url);
          console.log('[Import] Duplicated space ID:', duplicateResult.space_id);
          console.log('[Import] ==========================================');
          
          // Also load the code in the editor
          const importResult = await apiClient.importProject(importUrl);
          if (importResult.status === 'success' && onImport && importResult.code) {
            console.log('[Import] Calling onImport with duplicated space URL:', duplicateResult.space_url);
            // Pass the duplicated space URL so it's tracked for future deployments
            onImport(importResult.code, importResult.language || 'html', duplicateResult.space_url);
            
            // Show success message with link to duplicated space
            alert(`✅ Space duplicated successfully!\n\nYour space: ${duplicateResult.space_url}\n\nThe code has been loaded in the editor. Any changes you deploy will update this duplicated space.`);
          }
          
          setShowImportDialog(false);
          setImportUrl('');
        } else {
          setImportError(duplicateResult.message || 'Failed to duplicate space');
        }
      } else {
        // Not a Space URL - fall back to regular import
        console.log('[Import] ❌ Not a HF Space URL - using regular import');
        const result = await apiClient.importProject(importUrl);
        
        if (result.status === 'success') {
          if (onImport && result.code) {
            onImport(result.code, result.language || 'html', importUrl);
          } else {
            const importMessage = `Imported from ${importUrl}`;
            onStart(importMessage, result.language || 'html', selectedModel);
          }
          
          setShowImportDialog(false);
          setImportUrl('');
        } else {
          setImportError(result.message || 'Failed to import project');
        }
      }
    } catch (error: any) {
      console.error('Import error:', error);
      setImportError(error.response?.data?.message || error.message || 'Failed to import project');
    } finally {
      setIsImporting(false);
    }
  };

  const handleRedesignProject = async () => {
    if (!redesignUrl.trim()) {
      setRedesignError('Please enter a valid URL');
      return;
    }

    if (!isAuthenticated) {
      alert('Please sign in with HuggingFace first!');
      return;
    }

    setIsRedesigning(true);
    setRedesignError('');

    try {
      // Extract space ID from URL
      const spaceMatch = redesignUrl.match(/huggingface\.co\/spaces\/([^\/\s\)]+\/[^\/\s\)]+)/);
      const repoId = spaceMatch ? spaceMatch[1] : null;
      
      if (!repoId) {
        setRedesignError('Please enter a valid HuggingFace Space URL');
        setIsRedesigning(false);
        return;
      }
      
      // Import the code first
      const result = await apiClient.importProject(redesignUrl);
      
      if (result.status !== 'success') {
        setRedesignError(result.message || 'Failed to import project for redesign');
        setIsRedesigning(false);
        return;
      }
      
      if (!createPR) {
        // Option 1: Redesign WITHOUT PR - Duplicate space first, then generate redesign
        console.log('[Redesign] Duplicating space first:', repoId);
        
        try {
          const duplicateResult = await apiClient.duplicateSpace(repoId);
          console.log('[Redesign] Duplicate result:', duplicateResult);
          
          if (!duplicateResult.success) {
            setRedesignError(duplicateResult.message || 'Failed to duplicate space');
            setIsRedesigning(false);
            return;
          }
          
          // Load code and trigger redesign
          if (onImport && onStart) {
            // Pass duplicated space URL
            onImport(result.code, result.language || 'html', duplicateResult.space_url);
            
            // Extract duplicated space ID to pass to generation
            const dupSpaceMatch = duplicateResult.space_url?.match(/huggingface\.co\/spaces\/([^\/\s\)]+\/[^\/\s\)]+)/);
            const duplicatedRepoId = dupSpaceMatch ? dupSpaceMatch[1] : undefined;
            
            console.log('[Redesign] Duplicated space ID:', duplicatedRepoId);
            
            setTimeout(() => {
              const isGradio = (result.language || 'html') === 'gradio';
              const redesignPrompt = `I have existing code in the editor from a duplicated space. Please redesign it to make it look better with minimal components needed, mobile friendly, and modern design.

Current code:
\`\`\`${result.language || 'html'}
${result.code}
\`\`\`

Please redesign this with:
- Minimal, clean components
- Mobile-first responsive design
- Modern UI/UX best practices
- Better visual hierarchy and spacing

${isGradio ? '\n\nIMPORTANT: Only output Python (.py) files. Do NOT include requirements.txt or any other non-Python files. The existing dependencies and configuration files will be preserved.' : ''}`;
              
              if (onStart) {
                // Pass duplicated space ID so auto-deploy updates it
                console.log('[Redesign] Calling onStart with duplicated repo ID:', duplicatedRepoId);
                console.log('[Redesign] Using Claude-Sonnet-4.5 for redesign');
                onStart(redesignPrompt, result.language || 'html', 'claude-sonnet-4.5', duplicatedRepoId);
              }
            }, 100);
            
            // Show success message
            alert(`✅ Space duplicated!\n\nYour space: ${duplicateResult.space_url}\n\nGenerating redesign now...`);
          }
          
          setShowRedesignDialog(false);
          setRedesignUrl('');
          
        } catch (dupError: any) {
          console.error('[Redesign] Duplication error:', dupError);
          setRedesignError(dupError.response?.data?.message || dupError.message || 'Failed to duplicate space');
          setIsRedesigning(false);
          return;
        }
        
      } else {
        // Option 2: Redesign WITH PR - Import code and generate, then create PR
        if (onImport && onStart) {
          onImport(result.code, result.language || 'html', redesignUrl);
          
          setTimeout(() => {
            const isGradio = (result.language || 'html') === 'gradio';
            const redesignPrompt = `I have existing code in the editor that I imported from ${redesignUrl}. Please redesign it to make it look better with minimal components needed, mobile friendly, and modern design.

Current code:
\`\`\`${result.language || 'html'}
${result.code}
\`\`\`

Please redesign this with:
- Minimal, clean components
- Mobile-first responsive design
- Modern UI/UX best practices
- Better visual hierarchy and spacing

${isGradio ? '\n\nIMPORTANT: Only output Python (.py) files. Do NOT include requirements.txt or any other non-Python files. The existing dependencies and configuration files will be preserved.' : ''}

Note: After generating the redesign, I will create a Pull Request on the original space.`;
            
            if (onStart) {
              console.log('[Redesign] Will create PR - not passing repo ID');
              console.log('[Redesign] Using Claude-Sonnet-4.5 for redesign');
              onStart(redesignPrompt, result.language || 'html', 'claude-sonnet-4.5', repoId, true); // Pass true for shouldCreatePR
            }
            
            console.log('[Redesign] Will create PR after code generation completes');
          }, 100);
          
          setShowRedesignDialog(false);
          setRedesignUrl('');
        } else {
          setRedesignError('Missing required callbacks. Please try again.');
        }
      }
    } catch (error: any) {
      console.error('Redesign error:', error);
      setRedesignError(error.response?.data?.message || error.message || 'Failed to process redesign request');
    } finally {
      setIsRedesigning(false);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-[#000000] overflow-hidden">
      {/* Header - Apple style */}
      <header className="flex items-center justify-between px-6 py-3 backdrop-blur-xl bg-[#000000]/80 border-b border-[#424245]/30 flex-shrink-0">
        <a 
          href="https://huggingface.co/spaces/akhaliq/anycoder" 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-sm font-medium text-[#f5f5f7] hover:text-white transition-colors"
        >
          AnyCoder
        </a>
        
        {/* Auth Section */}
        <div className="flex items-center space-x-3">
          {isAuthLoading ? (
            <span className="text-xs text-[#86868b]">Loading...</span>
          ) : userInfo ? (
            <div className="flex items-center space-x-3">
              {userInfo.avatarUrl && (
                <img 
                  src={userInfo.avatarUrl} 
                  alt={userInfo.name}
                  className="w-7 h-7 rounded-full"
                />
              )}
              <span className="hidden sm:inline text-sm text-[#f5f5f7] truncate max-w-[120px] font-medium">
                {userInfo.preferredUsername || userInfo.name}
              </span>
              <button
                onClick={handleLogout}
                className="px-3 py-1.5 text-sm text-[#f5f5f7] hover:text-white transition-colors"
              >
                Logout
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-3">
              {/* Dev Mode Login (only on localhost) */}
              {isDevMode && (
                <>
                  {showDevLogin ? (
                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        value={devUsername}
                        onChange={(e) => setDevUsername(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleDevLogin()}
                        placeholder="username"
                        className="px-3 py-1.5 rounded-lg text-sm bg-[#1d1d1f] text-[#f5f5f7] border border-[#424245] focus:outline-none focus:border-white/50 w-32 font-medium"
                        autoFocus
                      />
                      <button
                        onClick={handleDevLogin}
                        className="px-3 py-1.5 bg-white text-black rounded-lg text-sm hover:bg-[#f5f5f7] font-medium"
                      >
                        OK
                      </button>
                      <button
                        onClick={() => {
                          setShowDevLogin(false);
                          setDevUsername('');
                        }}
                        className="text-[#86868b] hover:text-[#f5f5f7] text-sm"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setShowDevLogin(true)}
                      className="px-3 py-1.5 text-sm text-[#f5f5f7] hover:text-white transition-colors"
                      title="Dev Mode"
                    >
                      Dev
                    </button>
                  )}
                  <span className="text-[#86868b] text-sm">or</span>
                </>
              )}
              
              {/* OAuth Login */}
              <button
                onClick={handleLogin}
                className="px-4 py-2 bg-white text-black rounded-full text-sm hover:bg-[#f5f5f7] transition-all font-medium"
              >
                Sign in
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Content - Apple-style centered layout */}
      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="w-full max-w-3xl mx-auto flex flex-col items-center justify-center min-h-full">
          {/* Apple-style Headline */}
          <div className="text-center mb-8">
            <h2 className="text-4xl md:text-5xl font-semibold text-white mb-2 tracking-tight leading-tight">
              Build with AnyCoder
            </h2>
            <p className="text-base md:text-lg text-[#86868b] font-normal">
              Create apps with AI
            </p>
          </div>

          {/* Simple prompt form */}
          <form onSubmit={handleSubmit} className="relative w-full mb-8">
            <div className="relative bg-[#2d2d30] rounded-2xl border border-[#424245] shadow-2xl">
              {/* Textarea */}
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Message AnyCoder"
                className="w-full px-4 py-3 text-sm text-[#f5f5f7] bg-transparent placeholder:text-[#86868b] resize-none focus:outline-none min-h-[48px] font-normal"
                rows={1}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
              />
              
              {/* Bottom controls - Apple style */}
              <div className="flex items-center justify-between px-3 pb-3 gap-2">
                {/* Compact dropdowns on the left */}
                <div className="flex items-center gap-2">
                  {/* Language Dropdown */}
                  <div className="relative" ref={languageDropdownRef}>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        console.log('Language button clicked, toggling dropdown');
                        setShowLanguageDropdown(!showLanguageDropdown);
                        setShowModelDropdown(false);
                      }}
                      disabled={isLoading}
                      className="px-3 py-1.5 bg-[#1d1d1f] text-[#f5f5f7] text-xs border border-[#424245] rounded-full hover:bg-[#2d2d2f] transition-all disabled:opacity-50 flex items-center gap-1.5 font-medium"
                    >
                      <span>{isLoading ? '...' : formatLanguageName(selectedLanguage)}</span>
                      <svg 
                        className={`w-3 h-3 text-[#86868b] transition-transform ${showLanguageDropdown ? 'rotate-180' : ''}`}
                        fill="none" 
                        stroke="currentColor" 
                        viewBox="0 0 24 24"
                        strokeWidth={2.5}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    
                    {/* Language Dropdown Menu */}
                    {showLanguageDropdown && !isLoading && languages.length > 0 && (
                      <div 
                        className="absolute bottom-full left-0 mb-2 w-48 bg-[#1d1d1f] border border-[#424245] rounded-xl shadow-2xl overflow-hidden backdrop-blur-xl"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="max-h-64 overflow-y-auto py-1">
                          {languages.map((lang) => (
                            <button
                              key={lang}
                              type="button"
                              onClick={() => {
                                setSelectedLanguage(lang);
                                setShowLanguageDropdown(false);
                              }}
                              className={`w-full px-4 py-2.5 text-left text-xs text-[#f5f5f7] hover:bg-[#2d2d2f] transition-colors font-medium ${
                                selectedLanguage === lang ? 'bg-[#2d2d2f]' : ''
                              }`}
                            >
                              {formatLanguageName(lang)}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Model Dropdown */}
                  <div className="relative" ref={modelDropdownRef}>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        console.log('Model button clicked! Models length:', models.length, 'Show:', showModelDropdown);
                        setShowModelDropdown(!showModelDropdown);
                        setShowLanguageDropdown(false);
                        setShowImportDialog(false);
                      }}
                      className="px-3 py-1.5 bg-[#1d1d1f] text-[#f5f5f7] text-xs border border-[#424245] rounded-full hover:bg-[#2d2d2f] transition-all flex items-center gap-1.5 max-w-[200px] font-medium"
                    >
                      <span className="truncate">
                        {isLoading 
                          ? '...' 
                          : models.find(m => m.id === selectedModel)?.name || selectedModel || 'Model'
                        }
                      </span>
                      <svg 
                        className={`w-3 h-3 text-[#86868b] flex-shrink-0 transition-transform ${showModelDropdown ? 'rotate-180' : ''}`}
                        fill="none" 
                        stroke="currentColor" 
                        viewBox="0 0 24 24"
                        strokeWidth={2.5}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    
                    {/* Model Dropdown Menu */}
                    {showModelDropdown && models.length > 0 && (
                      <div 
                        className="absolute top-full left-0 mt-2 w-56 bg-[#1d1d1f] border border-[#424245] rounded-xl shadow-2xl overflow-hidden backdrop-blur-xl z-50"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="max-h-96 overflow-y-auto py-1">
                          {models.map((model) => (
                            <button
                              key={model.id}
                              type="button"
                              onClick={() => {
                                setSelectedModel(model.id);
                                setShowModelDropdown(false);
                              }}
                              className={`w-full px-4 py-2 text-left transition-colors ${
                                selectedModel === model.id 
                                  ? 'bg-[#2d2d2f]' 
                                  : 'hover:bg-[#2d2d2f]'
                              }`}
                            >
                              <div className="text-xs font-medium text-[#f5f5f7]">{model.name}</div>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Import Project Button */}
                  <div className="relative" ref={importDialogRef}>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowImportDialog(!showImportDialog);
                        setShowLanguageDropdown(false);
                        setShowModelDropdown(false);
                        setShowRedesignDialog(false);
                        setImportError('');
                      }}
                      className="px-3 py-1.5 bg-[#1d1d1f] text-[#f5f5f7] text-xs border border-[#424245] rounded-full hover:bg-[#2d2d2f] transition-all flex items-center gap-1.5 font-medium"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      <span>Import</span>
                    </button>
                    
                    {/* Import Dialog */}
                    {showImportDialog && (
                      <div 
                        className="absolute top-full left-0 mt-2 w-80 bg-[#1d1d1f] border border-[#424245] rounded-xl shadow-2xl overflow-hidden backdrop-blur-xl z-50"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="p-4">
                          <h3 className="text-sm font-medium text-[#f5f5f7] mb-3">Import Project</h3>
                          <input
                            type="text"
                            value={importUrl}
                            onChange={(e) => setImportUrl(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleImportProject()}
                            placeholder="https://huggingface.co/spaces/..."
                            className="w-full px-3 py-2 rounded-lg text-xs bg-[#2d2d30] text-[#f5f5f7] border border-[#424245] focus:outline-none focus:border-white/50 font-normal mb-2"
                            disabled={isImporting}
                          />
                          {importError && (
                            <p className="text-xs text-red-400 mb-2">{importError}</p>
                          )}
                          <div className="flex gap-2">
                            <button
                              onClick={handleImportProject}
                              disabled={isImporting || !importUrl.trim()}
                              className="flex-1 px-3 py-2 bg-white text-black rounded-lg text-xs hover:bg-[#f5f5f7] disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                            >
                              {isImporting ? 'Importing...' : 'Import'}
                            </button>
                            <button
                              onClick={() => {
                                setShowImportDialog(false);
                                setImportUrl('');
                                setImportError('');
                              }}
                              className="px-3 py-2 bg-[#2d2d30] text-[#f5f5f7] rounded-lg text-xs hover:bg-[#3d3d3f] font-medium"
                            >
                              Cancel
                            </button>
                          </div>
                          <p className="text-[10px] text-[#86868b] mt-3">
                            Import from HuggingFace Spaces, Models, or GitHub
                          </p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Redesign Project Button */}
                  <div className="relative" ref={redesignDialogRef}>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowRedesignDialog(!showRedesignDialog);
                        setShowLanguageDropdown(false);
                        setShowModelDropdown(false);
                        setShowImportDialog(false);
                        setRedesignError('');
                      }}
                      className="relative px-3 py-1.5 bg-[#1d1d1f] text-[#f5f5f7] text-xs border border-[#424245] rounded-full hover:bg-[#2d2d2f] transition-all flex items-center gap-1.5 font-medium overflow-visible"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      <span>Redesign</span>
                      {/* Enhanced NEW Badge with glow effect */}
                      <span className="absolute -top-2 -right-2 px-2 py-0.5 bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500 text-white text-[9px] font-extrabold rounded-full shadow-lg animate-pulse">
                        <span className="relative z-10">NEW</span>
                        {/* Glow effect */}
                        <span className="absolute inset-0 bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500 rounded-full blur-sm opacity-75 animate-pulse"></span>
                      </span>
                    </button>
                    
                    {/* Redesign Dialog */}
                    {showRedesignDialog && (
                      <div 
                        className="absolute top-full left-0 mt-2 w-80 bg-[#1d1d1f] border border-[#424245] rounded-xl shadow-2xl overflow-hidden backdrop-blur-xl z-50"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="p-4">
                          <h3 className="text-sm font-medium text-[#f5f5f7] mb-3">Redesign Project</h3>
                          <input
                            type="text"
                            value={redesignUrl}
                            onChange={(e) => setRedesignUrl(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleRedesignProject()}
                            placeholder="https://huggingface.co/spaces/..."
                            className="w-full px-3 py-2 rounded-lg text-xs bg-[#2d2d30] text-[#f5f5f7] border border-[#424245] focus:outline-none focus:border-white/50 font-normal mb-3"
                            disabled={isRedesigning}
                          />
                          
                          {/* PR Option */}
                          <label className="flex items-center gap-2 mb-1 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={createPR}
                              onChange={(e) => setCreatePR(e.target.checked)}
                              disabled={isRedesigning}
                              className="w-4 h-4 rounded bg-[#2d2d30] border-[#424245] text-white focus:ring-white focus:ring-offset-0"
                            />
                            <span className="text-xs text-[#f5f5f7]">
                              Create Pull Request on original space
                            </span>
                          </label>
                          
                          {createPR && (
                            <p className="text-[10px] text-[#86868b] mb-2 ml-6">
                              ⚠️ Note: PR creation requires space owner to enable PRs. If disabled, uncheck this to duplicate the space instead.
                            </p>
                          )}
                          
                          {redesignError && (
                            <p className="text-xs text-red-400 mb-2">{redesignError}</p>
                          )}
                          <div className="flex gap-2">
                            <button
                              onClick={handleRedesignProject}
                              disabled={isRedesigning || !redesignUrl.trim()}
                              className="flex-1 px-3 py-2 bg-white text-black rounded-lg text-xs hover:bg-[#f5f5f7] disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                            >
                              {isRedesigning ? 'Redesigning...' : 'Redesign'}
                            </button>
                            <button
                              onClick={() => {
                                setShowRedesignDialog(false);
                                setRedesignUrl('');
                                setRedesignError('');
                              }}
                              className="px-3 py-2 bg-[#2d2d30] text-[#f5f5f7] rounded-lg text-xs hover:bg-[#3d3d3f] font-medium"
                            >
                              Cancel
                            </button>
                          </div>
                          <p className="text-[10px] text-[#86868b] mt-3">
                            {createPR 
                              ? 'Creates a Pull Request on the original space with your redesign'
                              : 'Import and automatically redesign with modern, mobile-friendly design'}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Send button on the right - Apple style */}
                <button
                  type="submit"
                  disabled={!prompt.trim() || !isAuthenticated}
                  className="p-2 bg-white text-[#1d1d1f] rounded-full hover:bg-[#f5f5f7] disabled:opacity-30 disabled:cursor-not-allowed transition-all active:scale-95 shadow-lg"
                  title="Send"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            </div>
            
            {!isAuthenticated && (
              <div className="mt-4 text-center">
                <p className="text-xs text-[#86868b]">
                  Sign in to get started
                </p>
              </div>
            )}
          </form>

          {/* Trending Apps Section */}
          {trendingApps.length > 0 && (
            <div className="mt-8 w-full">
              <h3 className="text-xl font-semibold text-white mb-4 text-center">
                Top Trending Apps Built with AnyCoder
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {trendingApps.map((app) => (
                  <a
                    key={app.id}
                    href={`https://huggingface.co/spaces/${app.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group bg-[#1d1d1f] border border-[#424245] rounded-xl p-4 hover:border-white/30 transition-all hover:shadow-xl hover:scale-[1.02]">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-xs font-medium text-[#f5f5f7] truncate group-hover:text-white transition-colors">
                          {app.id.split('/')[1]}
                        </h4>
                        <p className="text-[10px] text-[#86868b] mt-0.5">
                          by {app.id.split('/')[0]}
                        </p>
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                        <div className="flex items-center gap-0.5">
                          <svg className="w-3 h-3 text-[#86868b]" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                          <span className="text-[10px] text-[#86868b] font-medium">{app.likes}</span>
                        </div>
                        <div className="flex items-center gap-0.5">
                          <svg className="w-3 h-3 text-[#86868b]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                          </svg>
                          <span className="text-[10px] text-[#86868b] font-medium">{app.trendingScore}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      <span className="px-1.5 py-0.5 bg-[#2d2d30] text-[#86868b] text-[9px] rounded-full font-medium">
                        {app.sdk}
                      </span>
                      {app.tags?.slice(0, 2).map((tag: string) => 
                        tag !== 'anycoder' && tag !== app.sdk && tag !== 'region:us' && (
                          <span key={tag} className="px-1.5 py-0.5 bg-[#2d2d30] text-[#86868b] text-[9px] rounded-full font-medium">
                            {tag}
                          </span>
                        )
                      )}
                    </div>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}


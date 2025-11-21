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
  onStart: (prompt: string, language: Language, modelId: string) => void;
  isAuthenticated: boolean;
  initialLanguage?: Language;
  initialModel?: string;
  onAuthChange?: () => void;
}

export default function LandingPage({ 
  onStart, 
  isAuthenticated,
  initialLanguage = 'html',
  initialModel = 'MiniMaxAI/MiniMax-M2',
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
  const languageDropdownRef = useRef<HTMLDivElement>(null);
  const modelDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadData();
    handleOAuthInit();
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
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    await Promise.all([loadModels(), loadLanguages()]);
    setIsLoading(false);
  };

  const loadModels = async () => {
    try {
      const modelsList = await apiClient.getModels();
      setModels(modelsList);
    } catch (error) {
      console.error('Failed to load models:', error);
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
    return lang.charAt(0).toUpperCase() + lang.slice(1);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#000000] overflow-y-auto">
      {/* Header - Apple style */}
      <header className="flex items-center justify-between px-6 py-4 backdrop-blur-xl bg-[#000000]/80 border-b border-[#424245]/30 flex-shrink-0">
        <h1 className="text-sm font-medium text-[#f5f5f7]">
          AnyCoder
        </h1>
        
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
      <main className="flex-1 flex items-center justify-center px-4 py-12 min-h-0">
        <div className="w-full max-w-3xl">
          {/* Apple-style Headline */}
          <div className="text-center mb-12">
            <h2 className="text-5xl md:text-6xl lg:text-7xl font-semibold text-white mb-3 tracking-tight leading-[1.05]">
              Build with AnyCoder
            </h2>
            <p className="text-lg md:text-xl text-[#86868b] font-normal">
              Create apps and websites by chatting with AI
            </p>
          </div>

          {/* Simple prompt form */}
          <form onSubmit={handleSubmit} className="relative">
            <div className="relative bg-[#2d2d30] rounded-2xl border border-[#424245] shadow-2xl">
              {/* Textarea */}
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Message AnyCoder"
                className="w-full px-5 py-4 text-base text-[#f5f5f7] bg-transparent placeholder:text-[#86868b] resize-none focus:outline-none min-h-[56px] font-normal"
                rows={1}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
              />
              
              {/* Bottom controls - Apple style */}
              <div className="flex items-center justify-between px-4 pb-4 gap-3">
                {/* Compact dropdowns on the left */}
                <div className="flex items-center gap-2">
                  {/* Language Dropdown */}
                  <div className="relative" ref={languageDropdownRef}>
                    <button
                      type="button"
                      onClick={() => {
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
                      <div className="absolute bottom-full left-0 mb-2 w-48 bg-[#1d1d1f] border border-[#424245] rounded-xl shadow-2xl overflow-hidden backdrop-blur-xl">
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
                      onClick={() => {
                        setShowModelDropdown(!showModelDropdown);
                        setShowLanguageDropdown(false);
                      }}
                      disabled={isLoading}
                      className="px-3 py-1.5 bg-[#1d1d1f] text-[#f5f5f7] text-xs border border-[#424245] rounded-full hover:bg-[#2d2d2f] transition-all disabled:opacity-50 flex items-center gap-1.5 max-w-[200px] font-medium"
                    >
                      <span className="truncate">
                        {isLoading 
                          ? '...' 
                          : models.find(m => m.id === selectedModel)?.name || 'Model'
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
                    {showModelDropdown && !isLoading && models.length > 0 && (
                      <div className="absolute bottom-full left-0 mb-2 w-80 bg-[#1d1d1f] border border-[#424245] rounded-xl shadow-2xl overflow-hidden backdrop-blur-xl">
                        <div className="max-h-96 overflow-y-auto py-1">
                          {models.map((model) => (
                            <button
                              key={model.id}
                              type="button"
                              onClick={() => {
                                setSelectedModel(model.id);
                                setShowModelDropdown(false);
                              }}
                              className={`w-full px-4 py-2.5 text-left transition-colors ${
                                selectedModel === model.id 
                                  ? 'bg-[#2d2d2f]' 
                                  : 'hover:bg-[#2d2d2f]'
                              }`}
                            >
                              <div className="text-xs font-medium text-[#f5f5f7]">{model.name}</div>
                              {model.description && (
                                <div className="text-[10px] text-[#86868b] mt-1 leading-relaxed">
                                  {model.description}
                                </div>
                              )}
                            </button>
                          ))}
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
              <div className="mt-6 text-center">
                <p className="text-sm text-[#86868b]">
                  Sign in to get started
                </p>
              </div>
            )}
          </form>
        </div>
      </main>
    </div>
  );
}

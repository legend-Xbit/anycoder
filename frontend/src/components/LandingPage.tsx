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
  initialModel = 'zai-org/GLM-4.6',
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
  
  // Trending apps state
  const [trendingApps, setTrendingApps] = useState<any[]>([]);

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

  return (
    <div className="min-h-screen flex flex-col bg-[#000000] overflow-y-auto">
      {/* Header - Apple style */}
      <header className="flex items-center justify-between px-6 py-4 backdrop-blur-xl bg-[#000000]/80 border-b border-[#424245]/30 flex-shrink-0">
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
      <main className="flex-1 flex items-center justify-center px-4 py-12 min-h-0">
        <div className="w-full max-w-3xl">
          {/* Apple-style Headline */}
          <div className="text-center mb-12">
            <h2 className="text-5xl md:text-6xl lg:text-7xl font-semibold text-white mb-3 tracking-tight leading-[1.05]">
              Build with AnyCoder
            </h2>
            <p className="text-lg md:text-xl text-[#86868b] font-normal">
              Create apps with AI
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
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
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
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('Model button clicked!');
                        console.log('Current showModelDropdown:', showModelDropdown);
                        console.log('Models array:', models);
                        console.log('Models length:', models.length);
                        console.log('Selected model:', selectedModel);
                        setShowModelDropdown(!showModelDropdown);
                        setShowLanguageDropdown(false);
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

          {/* Trending Apps Section */}
          {trendingApps.length > 0 && (
            <div className="mt-16">
              <h3 className="text-2xl font-semibold text-white mb-6 text-center">
                Top Trending Apps Built with AnyCoder
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {trendingApps.map((app) => (
                  <a
                    key={app.id}
                    href={`https://huggingface.co/spaces/${app.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group bg-[#1d1d1f] border border-[#424245] rounded-xl p-5 hover:border-white/30 transition-all hover:shadow-xl hover:scale-[1.02]"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-[#f5f5f7] truncate group-hover:text-white transition-colors">
                          {app.id.split('/')[1]}
                        </h4>
                        <p className="text-xs text-[#86868b] mt-1">
                          by {app.id.split('/')[0]}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                        <div className="flex items-center gap-1">
                          <svg className="w-3.5 h-3.5 text-[#86868b]" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                          <span className="text-xs text-[#86868b] font-medium">{app.likes}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <svg className="w-3.5 h-3.5 text-[#86868b]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                          </svg>
                          <span className="text-xs text-[#86868b] font-medium">{app.trendingScore}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      <span className="px-2 py-0.5 bg-[#2d2d30] text-[#86868b] text-[10px] rounded-full font-medium">
                        {app.sdk}
                      </span>
                      {app.tags?.slice(0, 2).map((tag: string) => 
                        tag !== 'anycoder' && tag !== app.sdk && tag !== 'region:us' && (
                          <span key={tag} className="px-2 py-0.5 bg-[#2d2d30] text-[#86868b] text-[10px] rounded-full font-medium">
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

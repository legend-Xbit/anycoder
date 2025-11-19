'use client';

import { useState, useEffect, useRef } from 'react';
import { apiClient } from '@/lib/api';
import type { Model, Language } from '@/types';

interface LandingPageProps {
  onStart: (prompt: string, language: Language, modelId: string) => void;
  isAuthenticated: boolean;
  initialLanguage?: Language;
  initialModel?: string;
}

export default function LandingPage({ 
  onStart, 
  isAuthenticated,
  initialLanguage = 'html',
  initialModel = 'gemini-3.0-pro'
}: LandingPageProps) {
  const [prompt, setPrompt] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState<Language>(initialLanguage);
  const [selectedModel, setSelectedModel] = useState<string>(initialModel);
  const [models, setModels] = useState<Model[]>([]);
  const [languages, setLanguages] = useState<Language[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Dropdown states
  const [showLanguageDropdown, setShowLanguageDropdown] = useState(false);
  const [showModelDropdown, setShowModelDropdown] = useState(false);
  const languageDropdownRef = useRef<HTMLDivElement>(null);
  const modelDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadData();
  }, []);

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
    <div className="min-h-screen flex flex-col bg-[#1e1e1e] overflow-y-auto">
      {/* Header - Minimal Apple style */}
      <header className="flex items-center px-8 py-4 border-b border-[#3e3e42]/30 flex-shrink-0">
        <h1 className="text-base font-semibold text-[#cccccc] tracking-tight">
          AnyCoder
        </h1>
      </header>

      {/* Main Content - Centered with generous Apple spacing */}
      <main className="flex-1 flex items-center justify-center px-6 md:px-8 py-8 md:py-12 min-h-0">
        <div className="w-full max-w-4xl">
          {/* Headline - Apple typography with VS Code colors */}
          <div className="text-center mb-8 md:mb-10">
            <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-[#cccccc] mb-4 tracking-[-0.02em] leading-[1.1]">
              Build with AnyCoder
            </h2>
            <p className="text-base md:text-lg text-[#858585] font-light tracking-tight">
              Create apps and websites by chatting with AI
            </p>
          </div>

          {/* Prompt Input - VS Code style with Apple polish */}
          <form onSubmit={handleSubmit} className="relative">
            <div className="relative bg-[#252526] rounded-2xl border border-[#3e3e42] overflow-hidden shadow-2xl shadow-black/60">
              {/* Options Row - Language and Model dropdowns */}
              <div className="flex items-center gap-3 px-6 pt-5 pb-4 border-b border-[#3e3e42]/40">
                {/* Language Dropdown */}
                <div className="relative flex-1" ref={languageDropdownRef}>
                  <button
                    type="button"
                    onClick={() => {
                      setShowLanguageDropdown(!showLanguageDropdown);
                      setShowModelDropdown(false);
                    }}
                    disabled={isLoading}
                    className="w-full px-4 py-2.5 bg-[#2d2d30] text-[#cccccc] text-sm border border-[#3e3e42] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#007acc]/50 focus:border-[#007acc] disabled:opacity-50 font-medium flex items-center justify-between hover:bg-[#323233] transition-all duration-150"
                  >
                    <span className="text-[#cccccc]">{isLoading ? 'Loading...' : formatLanguageName(selectedLanguage)}</span>
                    <svg 
                      className={`w-4 h-4 text-[#858585] transition-transform duration-200 ${showLanguageDropdown ? 'rotate-180' : ''}`}
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  
                  {/* Language Dropdown Tray */}
                  {showLanguageDropdown && !isLoading && languages.length > 0 && (
                    <div className="absolute z-50 w-full mt-1.5 bg-[#252526] border border-[#3e3e42] rounded-lg shadow-2xl shadow-black/70 overflow-hidden">
                      <div className="max-h-64 overflow-y-auto">
                        {languages.map((lang) => (
                          <button
                            key={lang}
                            type="button"
                            onClick={() => {
                              setSelectedLanguage(lang);
                              setShowLanguageDropdown(false);
                            }}
                            className={`w-full px-4 py-2.5 text-left text-sm text-[#cccccc] hover:bg-[#2a2d2e] transition-colors duration-150 ${
                              selectedLanguage === lang ? 'bg-[#264f78] hover:bg-[#264f78] text-[#ffffff]' : ''
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
                <div className="relative flex-1" ref={modelDropdownRef}>
                  <button
                    type="button"
                    onClick={() => {
                      setShowModelDropdown(!showModelDropdown);
                      setShowLanguageDropdown(false);
                    }}
                    disabled={isLoading}
                    className="w-full px-4 py-2.5 bg-[#2d2d30] text-[#cccccc] text-sm border border-[#3e3e42] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#007acc]/50 focus:border-[#007acc] disabled:opacity-50 font-medium flex items-center justify-between hover:bg-[#323233] transition-all duration-150"
                  >
                    <span className="truncate text-[#cccccc]">
                      {isLoading 
                        ? 'Loading...' 
                        : models.find(m => m.id === selectedModel)?.name || 'Select model'
                      }
                    </span>
                    <svg 
                      className={`w-4 h-4 text-[#858585] transition-transform duration-200 flex-shrink-0 ml-2 ${showModelDropdown ? 'rotate-180' : ''}`}
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  
                  {/* Model Dropdown Tray */}
                  {showModelDropdown && !isLoading && models.length > 0 && (
                    <div className="absolute z-50 w-full mt-1.5 bg-[#252526] border border-[#3e3e42] rounded-lg shadow-2xl shadow-black/70 overflow-hidden">
                      <div className="max-h-80 overflow-y-auto">
                        {models.map((model) => (
                          <button
                            key={model.id}
                            type="button"
                            onClick={() => {
                              setSelectedModel(model.id);
                              setShowModelDropdown(false);
                            }}
                            className={`w-full px-4 py-3 text-left transition-colors duration-150 ${
                              selectedModel === model.id 
                                ? 'bg-[#264f78] hover:bg-[#264f78]' 
                                : 'hover:bg-[#2a2d2e]'
                            }`}
                          >
                            <div className="text-sm font-medium text-[#cccccc]">{model.name}</div>
                            {model.description && (
                              <div className="text-xs text-[#858585] mt-1 leading-relaxed">
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

              {/* Textarea */}
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ask AnyCoder to create a landing page for my..."
                className="w-full px-6 py-5 text-base md:text-lg text-[#cccccc] bg-transparent placeholder:text-[#858585] resize-none focus:outline-none min-h-[120px] md:min-h-[140px] font-normal leading-relaxed"
                rows={3}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                    handleSubmit(e);
                  }
                }}
              />
              
              {/* Input Controls - Apple style button */}
              <div className="flex items-center justify-end px-6 pb-5 pt-4 border-t border-[#3e3e42]/40">
                <button
                  type="submit"
                  disabled={!prompt.trim() || !isAuthenticated}
                  className="px-8 py-3 bg-[#007acc] text-white text-sm font-semibold rounded-lg hover:bg-[#0066b3] disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 shadow-lg shadow-[#007acc]/20 hover:shadow-[#007acc]/30 active:scale-[0.97] flex items-center space-x-2 tracking-tight"
                  title="Send (⌘+Enter)"
                >
                  <span>Send</span>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </button>
              </div>
            </div>
            
            {!isAuthenticated && (
              <div className="mt-6 text-center">
                <p className="text-sm text-[#858585] font-medium">
                  Please sign in to get started
                </p>
              </div>
            )}
          </form>
        </div>
      </main>
    </div>
  );
}

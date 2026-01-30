'use client';

import { useState, useEffect, useRef } from 'react';
import { apiClient } from '@/lib/api';
import type { Model, Language } from '@/types';

interface ControlPanelProps {
  selectedLanguage: Language;
  selectedModel: string;
  onLanguageChange: (language: Language) => void;
  onModelChange: (modelId: string) => void;
  onClear: () => void;
  isGenerating: boolean;
}

export default function ControlPanel({
  selectedLanguage,
  selectedModel,
  onLanguageChange,
  onModelChange,
  onClear,
  isGenerating,
}: ControlPanelProps) {
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
      console.log('Loading models...');
      const modelsList = await apiClient.getModels();
      console.log('Models loaded:', modelsList);
      setModels(modelsList);
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  };

  const loadLanguages = async () => {
    try {
      console.log('Loading languages...');
      const { languages: languagesList } = await apiClient.getLanguages();
      console.log('Languages loaded:', languagesList);
      setLanguages(languagesList);
    } catch (error) {
      console.error('Failed to load languages:', error);
    }
  };

  const formatLanguageName = (lang: Language) => {
    if (lang === 'html') return 'HTML';
    if (lang === 'transformers.js') return 'Transformers.js';
    if (lang === 'comfyui') return 'ComfyUI';
    if (lang === 'daggr') return 'Daggr';
    return lang.charAt(0).toUpperCase() + lang.slice(1);
  };

  return (
    <div className="bg-[#000000] h-full flex flex-col">
      {/* Panel Header */}
      <div className="flex items-center px-4 py-3 border-b border-[#424245]/30">
        <h3 className="text-sm font-medium text-[#f5f5f7]">Settings</h3>
      </div>

      {/* Content */}
      <div className="flex-1 p-4 space-y-5 overflow-y-auto">

        {/* Language Selection */}
        <div className="relative" ref={languageDropdownRef}>
          <label className="block text-xs font-medium text-[#f5f5f7] mb-2">
            Language
          </label>
          <button
            type="button"
            onClick={() => {
              setShowLanguageDropdown(!showLanguageDropdown);
              setShowModelDropdown(false);
            }}
            disabled={isGenerating || isLoading}
            className="w-full px-3 py-2 bg-[#1d1d1f] text-[#f5f5f7] text-sm border border-[#424245]/50 rounded-lg focus:outline-none focus:border-[#424245] disabled:opacity-40 flex items-center justify-between hover:bg-[#2d2d2f] transition-colors"
          >
            <span>{isLoading ? 'Loading...' : formatLanguageName(selectedLanguage)}</span>
            <svg
              className={`w-3.5 h-3.5 text-[#86868b] transition-transform ${showLanguageDropdown ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* Language Dropdown Tray */}
          {showLanguageDropdown && !isLoading && languages.length > 0 && (
            <div className="absolute z-50 w-full mt-1 bg-[#1d1d1f] border border-[#424245] rounded-lg shadow-xl overflow-hidden">
              <div className="max-h-64 overflow-y-auto py-1">
                {languages.map((lang) => (
                  <button
                    key={lang}
                    type="button"
                    onClick={() => {
                      onLanguageChange(lang);
                      setShowLanguageDropdown(false);
                    }}
                    className={`w-full px-3 py-2 text-left text-sm text-[#f5f5f7] hover:bg-[#2d2d2f] transition-colors ${selectedLanguage === lang ? 'bg-[#2d2d2f]' : ''
                      }`}
                  >
                    {formatLanguageName(lang)}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Model Selection */}
        <div className="relative" ref={modelDropdownRef}>
          <label className="block text-xs font-medium text-[#f5f5f7] mb-2">
            AI Model
          </label>
          <button
            type="button"
            onClick={() => {
              setShowModelDropdown(!showModelDropdown);
              setShowLanguageDropdown(false);
            }}
            disabled={isGenerating}
            className="w-full px-3 py-2 bg-[#1d1d1f] text-[#f5f5f7] text-sm border border-[#424245]/50 rounded-lg focus:outline-none focus:border-[#424245] disabled:opacity-40 flex items-center justify-between hover:bg-[#2d2d2f] transition-colors"
          >
            <span className="truncate">
              {isLoading
                ? 'Loading...'
                : models.find(m => m.id === selectedModel)?.name || selectedModel || 'Select model'
              }
            </span>
            <svg
              className={`w-3.5 h-3.5 text-[#86868b] flex-shrink-0 ml-2 transition-transform ${showModelDropdown ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* Model Dropdown Tray */}
          {showModelDropdown && models.length > 0 && (
            <div className="absolute z-50 w-full mt-1 bg-[#1d1d1f] border border-[#424245] rounded-lg shadow-xl overflow-hidden">
              <div className="max-h-96 overflow-y-auto py-1">
                {models.map((model) => (
                  <button
                    key={model.id}
                    type="button"
                    onClick={() => {
                      onModelChange(model.id);
                      setShowModelDropdown(false);
                    }}
                    className={`w-full px-3 py-2 text-left transition-colors ${selectedModel === model.id
                      ? 'bg-[#2d2d2f]'
                      : 'hover:bg-[#2d2d2f]'
                      }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm text-[#f5f5f7]">{model.name}</span>
                      {['moonshotai/Kimi-K2.5'].includes(model.id) && (
                        <span className="px-1.5 py-0.5 bg-gradient-to-r from-purple-500 to-pink-500 text-white text-[9px] font-bold rounded uppercase flex-shrink-0">
                          NEW
                        </span>
                      )}
                    </div>
                    {model.description && (
                      <div className="text-[10px] text-[#86868b] mt-0.5 leading-relaxed">
                        {model.description}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Model Description */}
          {!isLoading && models.find(m => m.id === selectedModel) && (
            <p className="text-[10px] text-[#86868b] mt-2 leading-relaxed">
              {models.find(m => m.id === selectedModel)?.description}
            </p>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col space-y-2">
          <button
            onClick={onClear}
            disabled={isGenerating}
            className="w-full px-3 py-2.5 bg-[#1d1d1f] text-[#f5f5f7] text-sm rounded-full hover:bg-[#2d2d2f] disabled:opacity-30 disabled:cursor-not-allowed transition-all font-medium border border-[#424245]/50 flex items-center justify-center active:scale-95"
          >
            New Chat
          </button>
        </div>
      </div>
    </div>
  );
}

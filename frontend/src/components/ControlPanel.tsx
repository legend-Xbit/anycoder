'use client';

import { useState, useEffect, useRef } from 'react';
import { apiClient } from '@/lib/api';
import type { Model, Language } from '@/types';

interface ControlPanelProps {
  selectedLanguage: Language;
  selectedModel: string;
  onLanguageChange: (language: Language) => void;
  onModelChange: (modelId: string) => void;
  onDeploy: () => void;
  onClear: () => void;
  onImport?: (code: string, language: Language, importUrl?: string) => void;
  isGenerating: boolean;
}

export default function ControlPanel({
  selectedLanguage,
  selectedModel,
  onLanguageChange,
  onModelChange,
  onDeploy,
  onClear,
  onImport,
  isGenerating,
}: ControlPanelProps) {
  const [models, setModels] = useState<Model[]>([]);
  const [languages, setLanguages] = useState<Language[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importUrl, setImportUrl] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  
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

  const handleImport = async () => {
    if (!importUrl.trim()) {
      setImportError('Please enter a valid URL');
      return;
    }

    setIsImporting(true);
    setImportError(null);

    try {
      console.log('Importing from:', importUrl);
      const result = await apiClient.importProject(importUrl);
      
      if (result.status === 'success') {
        console.log('Import successful:', result);
        
        // Call the onImport callback if provided
        if (onImport && result.code) {
          onImport(result.code, result.language || 'html', importUrl);
        }
        
        // Close modal and reset
        setShowImportModal(false);
        setImportUrl('');
        setImportError(null);
      } else {
        setImportError(result.message || 'Import failed');
      }
    } catch (error: any) {
      console.error('Import error:', error);
      setImportError(error.response?.data?.message || error.message || 'Failed to import project');
    } finally {
      setIsImporting(false);
    }
  };

  const formatLanguageName = (lang: Language) => {
    if (lang === 'html') return 'HTML';
    if (lang === 'transformers.js') return 'Transformers.js';
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
                  className={`w-full px-3 py-2 text-left text-sm text-[#f5f5f7] hover:bg-[#2d2d2f] transition-colors ${
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
          disabled={isGenerating || isLoading}
          className="w-full px-3 py-2 bg-[#1d1d1f] text-[#f5f5f7] text-sm border border-[#424245]/50 rounded-lg focus:outline-none focus:border-[#424245] disabled:opacity-40 flex items-center justify-between hover:bg-[#2d2d2f] transition-colors"
        >
          <span className="truncate">
            {isLoading 
              ? 'Loading...' 
              : models.find(m => m.id === selectedModel)?.name || 'Select model'
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
        {showModelDropdown && !isLoading && models.length > 0 && (
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
                  className={`w-full px-3 py-2 text-left transition-colors ${
                    selectedModel === model.id 
                      ? 'bg-[#2d2d2f]' 
                      : 'hover:bg-[#2d2d2f]'
                  }`}
                >
                  <div className="text-sm text-[#f5f5f7]">{model.name}</div>
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
          onClick={() => setShowImportModal(true)}
          disabled={isGenerating}
          className="w-full px-3 py-2.5 bg-white text-black text-sm rounded-full hover:bg-[#f5f5f7] disabled:opacity-30 disabled:cursor-not-allowed transition-all font-medium flex items-center justify-center active:scale-95"
        >
          Import Project
        </button>
        <button
          onClick={onDeploy}
          disabled={isGenerating}
          className="w-full px-3 py-2.5 bg-white text-black text-sm rounded-full hover:bg-[#f5f5f7] disabled:opacity-30 disabled:cursor-not-allowed transition-all font-medium flex items-center justify-center active:scale-95"
        >
          Publish
        </button>
        <button
          onClick={onClear}
          disabled={isGenerating}
          className="w-full px-3 py-2.5 bg-[#1d1d1f] text-[#f5f5f7] text-sm rounded-full hover:bg-[#2d2d2f] disabled:opacity-30 disabled:cursor-not-allowed transition-all font-medium border border-[#424245]/50 flex items-center justify-center active:scale-95"
        >
          Clear
        </button>
      </div>
      </div>

      {/* Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-50 p-4">
          <div className="bg-[#1d1d1f] border border-[#424245] rounded-2xl p-5 max-w-md w-full shadow-2xl">
            <h3 className="text-base font-medium text-[#f5f5f7] mb-4">Import Project</h3>
            
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-[#f5f5f7] mb-2">
                  Project URL
                </label>
                <input
                  type="text"
                  value={importUrl}
                  onChange={(e) => setImportUrl(e.target.value)}
                  placeholder="https://huggingface.co/spaces/..."
                  disabled={isImporting}
                  className="w-full px-3 py-2.5 bg-[#000000] text-[#f5f5f7] text-sm border border-[#424245] rounded-lg focus:outline-none focus:border-[#424245] disabled:opacity-40 placeholder-[#86868b]"
                  onKeyDown={(e) => e.key === 'Enter' && handleImport()}
                />
                <p className="text-[10px] text-[#86868b] mt-1.5">
                  Supported: HF Spaces, HF Models, GitHub repos
                </p>
              </div>

              {importError && (
                <div className="p-2.5 bg-[#ff3b30]/10 border border-[#ff3b30]/50 rounded-lg">
                  <p className="text-xs text-[#ff3b30]">{importError}</p>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  onClick={handleImport}
                  disabled={isImporting || !importUrl.trim()}
                  className="flex-1 px-3 py-2.5 bg-white text-black text-sm rounded-full hover:bg-[#f5f5f7] disabled:opacity-30 disabled:cursor-not-allowed transition-all font-medium active:scale-95"
                >
                  {isImporting ? '⏳ Importing...' : '✓ Import'}
                </button>
                <button
                  onClick={() => {
                    setShowImportModal(false);
                    setImportUrl('');
                    setImportError(null);
                  }}
                  disabled={isImporting}
                  className="flex-1 px-3 py-2.5 bg-[#000000] text-[#f5f5f7] text-sm rounded-full hover:bg-[#2d2d2f] disabled:opacity-30 disabled:cursor-not-allowed transition-all font-medium border border-[#424245] active:scale-95"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

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
    <div className="bg-[#252526] p-6 space-y-6 h-full">
      <h3 className="text-2xl font-bold text-[#cccccc] tracking-tight mb-6">Configuration</h3>
      
      {/* Language Selection */}
      <div className="relative" ref={languageDropdownRef}>
        <label className="block text-sm font-semibold text-[#cccccc] mb-3 tracking-tight">
          Language
        </label>
        <button
          type="button"
          onClick={() => {
            setShowLanguageDropdown(!showLanguageDropdown);
            setShowModelDropdown(false);
          }}
          disabled={isGenerating || isLoading}
          className="w-full px-4 py-3 bg-[#3a3a3c] text-[#cccccc] text-sm border border-[#3e3e42] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#007acc] focus:border-transparent disabled:opacity-50 font-medium shadow-sm flex items-center justify-between hover:bg-[#404040] transition-colors"
        >
          <span>{isLoading ? 'Loading...' : formatLanguageName(selectedLanguage)}</span>
          <svg 
            className={`w-4 h-4 text-[#cccccc] transition-transform ${showLanguageDropdown ? 'rotate-180' : ''}`}
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        
        {/* Language Dropdown Tray */}
        {showLanguageDropdown && !isLoading && languages.length > 0 && (
          <div className="absolute z-50 w-full mt-2 bg-[#252526] border border-[#3e3e42] rounded-lg shadow-2xl shadow-black/50 overflow-hidden">
            <div className="max-h-64 overflow-y-auto">
              {languages.map((lang) => (
                <button
                  key={lang}
                  type="button"
                  onClick={() => {
                    onLanguageChange(lang);
                    setShowLanguageDropdown(false);
                  }}
                  className={`w-full px-4 py-3 text-left text-sm text-[#cccccc] hover:bg-[#2a2d2e] transition-colors ${
                    selectedLanguage === lang ? 'bg-[#264f78] hover:bg-[#264f78]' : ''
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
        <label className="block text-sm font-semibold text-[#cccccc] mb-3 tracking-tight">
          AI Model
        </label>
        <button
          type="button"
          onClick={() => {
            setShowModelDropdown(!showModelDropdown);
            setShowLanguageDropdown(false);
          }}
          disabled={isGenerating || isLoading}
          className="w-full px-4 py-3 bg-[#3a3a3c] text-[#cccccc] text-sm border border-[#3e3e42] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#007acc] focus:border-transparent disabled:opacity-50 font-medium shadow-sm flex items-center justify-between hover:bg-[#404040] transition-colors"
        >
          <span>
            {isLoading 
              ? 'Loading...' 
              : models.find(m => m.id === selectedModel)?.name || 'Select model'
            }
          </span>
          <svg 
            className={`w-4 h-4 text-[#cccccc] transition-transform ${showModelDropdown ? 'rotate-180' : ''}`}
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        
        {/* Model Dropdown Tray */}
        {showModelDropdown && !isLoading && models.length > 0 && (
          <div className="absolute z-50 w-full mt-2 bg-[#252526] border border-[#3e3e42] rounded-lg shadow-2xl shadow-black/50 overflow-hidden">
            <div className="max-h-80 overflow-y-auto">
              {models.map((model) => (
                <button
                  key={model.id}
                  type="button"
                  onClick={() => {
                    onModelChange(model.id);
                    setShowModelDropdown(false);
                  }}
                  className={`w-full px-4 py-3 text-left transition-colors ${
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
        
        {/* Model Description */}
        {!isLoading && models.find(m => m.id === selectedModel) && (
          <p className="text-xs text-[#858585] mt-3 leading-relaxed">
            {models.find(m => m.id === selectedModel)?.description}
          </p>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col space-y-3 pt-4">
        <button
          onClick={() => setShowImportModal(true)}
          disabled={isGenerating}
          className="w-full px-4 py-3.5 bg-[#34c759] text-white text-sm rounded-xl hover:bg-[#30b350] disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold flex items-center justify-center space-x-2 shadow-md active:scale-95"
        >
          <span>📥</span>
          <span>Import Project</span>
        </button>
        <button
          onClick={onDeploy}
          disabled={isGenerating}
          className="w-full px-4 py-3.5 bg-[#007aff] text-white text-sm rounded-xl hover:bg-[#0051d5] disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold flex items-center justify-center space-x-2 shadow-md active:scale-95"
        >
          <span>🚀</span>
          <span>Publish</span>
        </button>
        <button
          onClick={onClear}
          disabled={isGenerating}
          className="w-full px-4 py-3.5 bg-[#3a3a3c] text-[#e5e5e7] text-sm rounded-xl hover:bg-[#48484a] disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold border border-[#48484a] flex items-center justify-center space-x-2 shadow-sm active:scale-95"
        >
          <span>🗑️</span>
          <span>Clear</span>
        </button>
      </div>

      {/* Info Panel */}
      <div className="mt-6 p-4 bg-[#2c2c2e] border border-[#48484a] rounded-xl shadow-sm">
        <h4 className="text-sm font-semibold text-[#e5e5e7] mb-3 tracking-tight">💡 Tips</h4>
        <ul className="text-xs text-[#86868b] space-y-2 leading-relaxed">
          <li>• Import projects from HF/GitHub</li>
          <li>• Be specific in your requirements</li>
          <li>• Try different AI models</li>
          <li>• Publish to HF Spaces</li>
        </ul>
      </div>

      {/* Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-[#2c2c2e] border border-[#48484a] rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-semibold text-[#e5e5e7] mb-4 tracking-tight">📥 Import Project</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#e5e5e7] mb-2">
                  Project URL
                </label>
                <input
                  type="text"
                  value={importUrl}
                  onChange={(e) => setImportUrl(e.target.value)}
                  placeholder="https://huggingface.co/spaces/..."
                  disabled={isImporting}
                  className="w-full px-4 py-3 bg-[#3a3a3c] text-[#e5e5e7] text-sm border border-[#48484a] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#34c759] focus:border-transparent disabled:opacity-50 placeholder-[#86868b] font-medium"
                  onKeyDown={(e) => e.key === 'Enter' && handleImport()}
                />
                <p className="text-xs text-[#86868b] mt-2">
                  Supported: HF Spaces, HF Models, GitHub repos
                </p>
              </div>

              {importError && (
                <div className="p-3 bg-[#ff3b30] bg-opacity-10 border border-[#ff3b30] rounded-xl">
                  <p className="text-sm text-[#ff3b30]">{importError}</p>
                </div>
              )}

              <div className="flex space-x-3">
                <button
                  onClick={handleImport}
                  disabled={isImporting || !importUrl.trim()}
                  className="flex-1 px-4 py-3 bg-[#34c759] text-white text-sm rounded-xl hover:bg-[#30b350] disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold active:scale-95"
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
                  className="flex-1 px-4 py-3 bg-[#3a3a3c] text-[#e5e5e7] text-sm rounded-xl hover:bg-[#48484a] disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold border border-[#48484a] active:scale-95"
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

'use client';

import { useState, useEffect } from 'react';
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

  useEffect(() => {
    loadData();
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

  return (
    <div className="bg-[#28282a] p-5 space-y-6 h-full">
      <h3 className="text-base font-semibold text-[#e5e5e7] tracking-tight mb-2">Configuration</h3>
      
      {/* Language Selection */}
      <div>
        <label className="block text-sm font-semibold text-[#e5e5e7] mb-3 tracking-tight">
          Language
        </label>
        <select
          value={selectedLanguage}
          onChange={(e) => onLanguageChange(e.target.value as Language)}
          disabled={isGenerating || isLoading}
          className="w-full px-4 py-3 bg-[#3a3a3c] text-[#e5e5e7] text-sm border border-[#48484a] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#007aff] focus:border-transparent disabled:opacity-50 font-medium shadow-sm"
        >
          {isLoading ? (
            <option value="">Loading...</option>
          ) : languages.length === 0 ? (
            <option value="">No languages available</option>
          ) : (
            languages.map((lang) => (
              <option key={lang} value={lang} className="bg-[#3a3a3c]">
                {lang === 'html' ? 'HTML' : lang.charAt(0).toUpperCase() + lang.slice(1)}
              </option>
            ))
          )}
        </select>
      </div>

      {/* Model Selection */}
      <div>
        <label className="block text-sm font-semibold text-[#e5e5e7] mb-3 tracking-tight">
          AI Model
        </label>
        <select
          value={selectedModel}
          onChange={(e) => onModelChange(e.target.value)}
          disabled={isGenerating || isLoading}
          className="w-full px-4 py-3 bg-[#3a3a3c] text-[#e5e5e7] text-sm border border-[#48484a] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#007aff] focus:border-transparent disabled:opacity-50 font-medium shadow-sm"
        >
          {isLoading ? (
            <option value="">Loading...</option>
          ) : models.length === 0 ? (
            <option value="">No models available</option>
          ) : (
            models.map((model) => (
              <option key={model.id} value={model.id} className="bg-[#3a3a3c]">
                {model.name}
              </option>
            ))
          )}
        </select>
        {!isLoading && models.find(m => m.id === selectedModel) && (
          <p className="text-xs text-[#86868b] mt-3 leading-relaxed">
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
          <span>Deploy</span>
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
          <li>• Deploy to HF Spaces</li>
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


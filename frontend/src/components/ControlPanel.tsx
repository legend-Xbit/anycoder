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
  isGenerating: boolean;
}

export default function ControlPanel({
  selectedLanguage,
  selectedModel,
  onLanguageChange,
  onModelChange,
  onDeploy,
  onClear,
  isGenerating,
}: ControlPanelProps) {
  const [models, setModels] = useState<Model[]>([]);
  const [languages, setLanguages] = useState<Language[]>([]);

  useEffect(() => {
    loadModels();
    loadLanguages();
  }, []);

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
          disabled={isGenerating}
          className="w-full px-4 py-3 bg-[#3a3a3c] text-[#e5e5e7] text-sm border border-[#48484a] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#007aff] focus:border-transparent disabled:opacity-50 font-medium shadow-sm"
        >
          {languages.map((lang) => (
            <option key={lang} value={lang} className="bg-[#3a3a3c]">
              {lang.charAt(0).toUpperCase() + lang.slice(1)}
            </option>
          ))}
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
          disabled={isGenerating}
          className="w-full px-4 py-3 bg-[#3a3a3c] text-[#e5e5e7] text-sm border border-[#48484a] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#007aff] focus:border-transparent disabled:opacity-50 font-medium shadow-sm"
        >
          {models.map((model) => (
            <option key={model.id} value={model.id} className="bg-[#3a3a3c]">
              {model.name}
            </option>
          ))}
        </select>
        {models.find(m => m.id === selectedModel) && (
          <p className="text-xs text-[#86868b] mt-3 leading-relaxed">
            {models.find(m => m.id === selectedModel)?.description}
          </p>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col space-y-3 pt-4">
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
          <li>• Be specific in your requirements</li>
          <li>• Try different AI models</li>
          <li>• Edit code in the editor</li>
          <li>• Deploy to HF Spaces</li>
        </ul>
      </div>
    </div>
  );
}


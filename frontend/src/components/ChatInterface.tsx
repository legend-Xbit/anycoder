'use client';

import { useState, useRef, useEffect } from 'react';
import type { Message } from '@/types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatInterfaceProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isGenerating: boolean;
  isAuthenticated?: boolean;
}

export default function ChatInterface({ messages, onSendMessage, isGenerating, isAuthenticated = false }: ChatInterfaceProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isGenerating) {
      onSendMessage(input);
      setInput('');
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#1d1d1f]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-[#a1a1a6] mt-12">
            <div className="text-5xl mb-5">💬</div>
            {isAuthenticated ? (
              <>
                <p className="text-lg font-semibold text-[#e5e5e7] tracking-tight">Start a conversation</p>
                <p className="text-sm mt-3 text-[#86868b] leading-relaxed">Describe what you want to build and I'll generate the code</p>
              </>
            ) : (
              <>
                <p className="text-lg font-semibold text-[#ff9f0a]">🔒 Sign in to get started</p>
                <p className="text-sm mt-3 text-[#86868b] leading-relaxed">Use Dev Login or sign in with Hugging Face</p>
              </>
            )}
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl p-4 shadow-sm ${
                  message.role === 'user'
                    ? 'bg-[#007aff] text-white'
                    : 'bg-[#2c2c2e] text-[#e5e5e7] border border-[#48484a]'
                }`}
              >
                <div className="flex items-start space-x-3">
                  <div className="text-base flex-shrink-0">
                    {message.role === 'user' ? '👤' : '🤖'}
                  </div>
                  <div className="flex-1 text-sm leading-relaxed">
                    {message.role === 'assistant' ? (
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        className="prose prose-invert prose-sm max-w-none"
                      >
                        {message.content}
                      </ReactMarkdown>
                    ) : (
                      <p className="whitespace-pre-wrap font-medium">{message.content}</p>
                    )}
                  </div>
                </div>
                {message.timestamp && (
                  <div className="text-xs opacity-50 mt-2 text-right font-medium">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-[#48484a] p-4 bg-[#28282a]">
        <form onSubmit={handleSubmit} className="flex space-x-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isAuthenticated ? "Message AnyCoder..." : "🔒 Please sign in first..."}
            disabled={isGenerating || !isAuthenticated}
            className="flex-1 px-4 py-3 bg-[#3a3a3c] text-[#e5e5e7] text-sm border border-[#48484a] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#007aff] focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed placeholder-[#86868b] font-medium shadow-sm"
          />
          <button
            type="submit"
            disabled={isGenerating || !input.trim() || !isAuthenticated}
            className="px-5 py-3 bg-[#007aff] text-white text-sm rounded-xl hover:bg-[#0051d5] disabled:bg-[#48484a] disabled:cursor-not-allowed transition-all font-semibold shadow-md disabled:shadow-none active:scale-95"
          >
            {isGenerating ? '⏳' : '↑'}
          </button>
        </form>
      </div>
    </div>
  );
}


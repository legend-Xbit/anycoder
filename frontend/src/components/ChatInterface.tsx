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
    <div className="flex flex-col h-full bg-[#000000]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <div className="text-center text-[#86868b] mt-12">
            {isAuthenticated ? (
              <>
                <p className="text-lg font-medium text-[#f5f5f7]">Start a conversation</p>
                <p className="text-sm mt-2 text-[#86868b]">Describe what you want to build</p>
              </>
            ) : (
              <>
                <p className="text-lg font-medium text-[#f5f5f7]">Sign in to get started</p>
                <p className="text-sm mt-2 text-[#86868b]">Use Dev Login or sign in with Hugging Face</p>
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
                className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-white text-black'
                    : 'bg-[#2d2d2f] text-[#f5f5f7]'
                }`}
              >
                <div className="text-sm leading-relaxed">
                  {message.role === 'assistant' ? (
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      className="prose prose-invert prose-sm max-w-none [&>p]:my-0 [&>ul]:my-1 [&>ol]:my-1"
                      components={{
                        a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  ) : (
                    <p className="whitespace-pre-wrap break-words">{message.content}</p>
                  )}
                </div>
                {message.timestamp && (
                  <div className="text-[10px] opacity-40 mt-2 text-right">
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
      <div className="border-t border-[#424245]/30 p-3 bg-[#000000]">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isAuthenticated ? "Message AnyCoder..." : "Sign in first..."}
            disabled={isGenerating || !isAuthenticated}
            className="flex-1 px-4 py-2.5 bg-[#2d2d2f] text-[#f5f5f7] text-sm border border-[#424245]/50 rounded-full focus:outline-none focus:border-[#424245] disabled:opacity-40 disabled:cursor-not-allowed placeholder-[#86868b]"
          />
          <button
            type="submit"
            disabled={isGenerating || !input.trim() || !isAuthenticated}
            className="p-2.5 bg-white text-black rounded-full hover:bg-[#f5f5f7] disabled:bg-[#2d2d2f] disabled:text-[#86868b] disabled:cursor-not-allowed transition-all active:scale-95 flex-shrink-0"
          >
            {isGenerating ? (
              <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}


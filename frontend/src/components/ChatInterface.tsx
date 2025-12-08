'use client';

import { useState, useRef, useEffect } from 'react';
import type { Message } from '@/types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Image from 'next/image';

interface ChatInterfaceProps {
  messages: Message[];
  onSendMessage: (message: string, imageUrl?: string) => void;
  isGenerating: boolean;
  isAuthenticated?: boolean;
  supportsImages?: boolean;
}

export default function ChatInterface({ messages, onSendMessage, isGenerating, isAuthenticated = false, supportsImages = false }: ChatInterfaceProps) {
  const [input, setInput] = useState('');
  const [uploadedImageUrl, setUploadedImageUrl] = useState<string | null>(null);
  const [uploadedImageFile, setUploadedImageFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
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
      onSendMessage(input, uploadedImageUrl || undefined);
      setInput('');
      setUploadedImageUrl(null);
      setUploadedImageFile(null);
    }
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Create a data URL for the image
      const reader = new FileReader();
      reader.onload = (event) => {
        const imageUrl = event.target?.result as string;
        setUploadedImageUrl(imageUrl);
        setUploadedImageFile(file);
      };
      reader.readAsDataURL(file);
    }
  };

  const removeImage = () => {
    setUploadedImageUrl(null);
    setUploadedImageFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
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
                {message.image_url && message.role === 'user' && (
                  <div className="mb-2">
                    <Image 
                      src={message.image_url} 
                      alt="Uploaded image" 
                      width={200} 
                      height={200} 
                      className="rounded-lg object-cover max-w-full h-auto"
                      unoptimized
                    />
                  </div>
                )}
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
        {/* Image Preview */}
        {uploadedImageUrl && (
          <div className="mb-2 relative inline-block">
            <Image 
              src={uploadedImageUrl} 
              alt="Upload preview" 
              width={120} 
              height={120} 
              className="rounded-lg object-cover"
              unoptimized
            />
            <button
              type="button"
              onClick={removeImage}
              className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full hover:bg-red-600 transition-all flex items-center justify-center text-xs font-bold"
            >
              ×
            </button>
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isAuthenticated ? "Message AnyCoder..." : "Sign in first..."}
            disabled={isGenerating || !isAuthenticated}
            className="flex-1 px-4 py-2.5 bg-[#2d2d2f] text-[#f5f5f7] text-sm border border-[#424245]/50 rounded-full focus:outline-none focus:border-[#424245] disabled:opacity-40 disabled:cursor-not-allowed placeholder-[#86868b]"
          />
          
          {/* Image Upload Button (only show if model supports images) */}
          {supportsImages && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
                disabled={isGenerating || !isAuthenticated}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isGenerating || !isAuthenticated}
                className="p-2.5 bg-[#2d2d2f] text-[#f5f5f7] rounded-full hover:bg-[#424245] disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95 flex-shrink-0"
                title="Upload image"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                </svg>
              </button>
            </>
          )}
          
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


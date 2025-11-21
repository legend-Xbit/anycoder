// API client for AnyCoder backend

import axios, { AxiosInstance } from 'axios';
import type {
  Model,
  AuthStatus,
  CodeGenerationRequest,
  DeploymentRequest,
  DeploymentResponse,
  Language,
} from '@/types';

// Use relative URLs in production (Next.js rewrites will proxy to backend)
// In local dev, use localhost:8000 for direct backend access
const getApiUrl = () => {
  // If explicitly set via env var, use it (for development)
  if (process.env.NEXT_PUBLIC_API_URL) {
    console.log('[API Client] Using explicit API URL:', process.env.NEXT_PUBLIC_API_URL);
    return process.env.NEXT_PUBLIC_API_URL;
  }
  
  // For server-side rendering, always use relative URLs
  if (typeof window === 'undefined') {
    console.log('[API Client] SSR mode: using relative URLs');
    return '';
  }
  
  // On localhost (dev mode), use direct backend URL  
  const hostname = window.location.hostname;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    console.log('[API Client] Localhost dev mode: using http://localhost:8000');
    return 'http://localhost:8000';
  }
  
  // In production (HF Space), use relative URLs (Next.js proxies to backend)
  console.log('[API Client] Production mode: using relative URLs (proxied by Next.js)');
  return '';
};

const API_URL = getApiUrl();

class ApiClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 10000, // 10 second timeout to prevent hanging connections
    });

    // Add auth token to requests if available
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });

    // Add response interceptor to handle authentication errors
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        // Handle 401 errors (expired/invalid authentication)
        if (error.response && error.response.status === 401) {
          // Clear authentication data
          if (typeof window !== 'undefined') {
            localStorage.removeItem('hf_oauth_token');
            localStorage.removeItem('hf_user_info');
            this.token = null;
            
            // Dispatch custom event to notify UI components
            window.dispatchEvent(new CustomEvent('auth-expired', {
              detail: { message: 'Your session has expired. Please sign in again.' }
            }));
          }
        }
        return Promise.reject(error);
      }
    );

    // Load token from localStorage on client side
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('hf_oauth_token');
    }
  }

  setToken(token: string | null) {
    this.token = token;
    // Note: OAuth token is stored by auth.ts, not here
    // We just keep it in memory for API calls
  }

  getToken(): string | null {
    return this.token;
  }

  async getModels(): Promise<Model[]> {
    try {
      const response = await this.client.get<Model[]>('/api/models');
      return response.data;
    } catch (error: any) {
      // Handle connection errors gracefully
      const isConnectionError = 
        error.code === 'ECONNABORTED' || 
        error.code === 'ECONNRESET' || 
        error.code === 'ECONNREFUSED' ||
        error.message?.includes('socket hang up') ||
        error.message?.includes('timeout') ||
        error.message?.includes('Network Error') ||
        error.response?.status === 503 ||
        error.response?.status === 502;
      
      if (isConnectionError) {
        // Backend is not available - return empty array instead of throwing
        console.warn('Backend not available, cannot load models');
        return [];
      }
      // Re-throw other errors
      throw error;
    }
  }

  async getLanguages(): Promise<{ languages: Language[] }> {
    try {
      const response = await this.client.get<{ languages: Language[] }>('/api/languages');
      return response.data;
    } catch (error: any) {
      // Handle connection errors gracefully
      const isConnectionError = 
        error.code === 'ECONNABORTED' || 
        error.code === 'ECONNRESET' || 
        error.code === 'ECONNREFUSED' ||
        error.message?.includes('socket hang up') ||
        error.message?.includes('timeout') ||
        error.message?.includes('Network Error') ||
        error.response?.status === 503 ||
        error.response?.status === 502;
      
      if (isConnectionError) {
        // Backend is not available - return default languages instead of throwing
        console.warn('Backend not available, using default languages');
        return { languages: ['html', 'gradio', 'transformers.js', 'streamlit', 'comfyui', 'react'] };
      }
      // Re-throw other errors
      throw error;
    }
  }

  async getAuthStatus(): Promise<AuthStatus> {
    try {
      const response = await this.client.get<AuthStatus>('/api/auth/status');
      return response.data;
    } catch (error: any) {
      // Silently handle connection errors - don't spam console
      if (error.code === 'ECONNABORTED' || error.code === 'ECONNRESET' || error.message?.includes('socket hang up')) {
        // Connection error - backend may not be ready
        return {
          authenticated: false,
          username: undefined,
          message: 'Connection error',
        };
      }
      // For other errors, return not authenticated
      return {
        authenticated: false,
        username: undefined,
        message: 'Not authenticated',
      };
    }
  }

  // Stream-based code generation using Fetch API with streaming (supports POST)
  generateCodeStream(
    request: CodeGenerationRequest,
    onChunk: (content: string) => void,
    onComplete: (code: string) => void,
    onError: (error: string) => void
  ): () => void {
    // Build the URL correctly whether we have a base URL or not
    const baseUrl = API_URL || window.location.origin;
    const url = new URL('/api/generate', baseUrl);
    
    let abortController = new AbortController();
    let accumulatedCode = '';
    let buffer = ''; // Buffer for incomplete SSE lines
    
    // Use fetch with POST to support large payloads
    fetch(url.toString(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { 'Authorization': `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify(request),
      signal: abortController.signal,
    })
      .then(async (response) => {
        // Handle rate limit errors before parsing response
        if (response.status === 429) {
          onError('⏱️ Rate limit exceeded. Free tier allows up to 20 requests per minute. Please wait a moment and try again.');
          return;
        }
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        if (!response.body) {
          throw new Error('Response body is null');
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            console.log('[Stream] Stream ended, total code length:', accumulatedCode.length);
            if (accumulatedCode) {
              onComplete(accumulatedCode);
            }
            break;
          }
          
          // Decode chunk and add to buffer
          buffer += decoder.decode(value, { stream: true });
          
          // Process complete SSE messages (ending with \n\n)
          const messages = buffer.split('\n\n');
          
          // Keep the last incomplete message in the buffer
          buffer = messages.pop() || '';
          
          // Process each complete message
          for (const message of messages) {
            if (!message.trim()) continue;
            
            // Parse SSE format: "data: {...}"
            const lines = message.split('\n');
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const jsonStr = line.substring(6);
                  const data = JSON.parse(jsonStr);
                  console.log('[Stream] Received event:', data.type, data.content?.substring(0, 50));
                  
                  if (data.type === 'chunk' && data.content) {
                    accumulatedCode += data.content;
                    onChunk(data.content);
                  } else if (data.type === 'complete') {
                    console.log('[Stream] Generation complete, total code length:', data.code?.length || accumulatedCode.length);
                    // Use the complete code from the message if available, otherwise use accumulated
                    const finalCode = data.code || accumulatedCode;
                    onComplete(finalCode);
                    return; // Exit the processing loop
                  } else if (data.type === 'error') {
                    console.error('[Stream] Error:', data.message);
                    onError(data.message || 'Unknown error occurred');
                    return; // Exit the processing loop
                  }
                } catch (error) {
                  console.error('Error parsing SSE data:', error, 'Line:', line);
                }
              }
            }
          }
        }
      })
      .catch((error) => {
        if (error.name === 'AbortError') {
          console.log('[Stream] Request aborted');
          return;
        }
        console.error('[Stream] Fetch error:', error);
        onError(error.message || 'Connection error occurred');
      });

    // Return cleanup function
    return () => {
      abortController.abort();
    };
  }

  // Alternative: WebSocket-based generation
  generateCodeWebSocket(
    request: CodeGenerationRequest,
    onChunk: (content: string) => void,
    onComplete: (code: string) => void,
    onError: (error: string) => void
  ): WebSocket {
    // Build WebSocket URL correctly for both dev and production
    const baseUrl = API_URL || window.location.origin;
    const wsUrl = baseUrl.replace('http', 'ws') + '/ws/generate';
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      ws.send(JSON.stringify(request));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'chunk' && data.content) {
          onChunk(data.content);
        } else if (data.type === 'complete' && data.code) {
          onComplete(data.code);
          ws.close();
        } else if (data.type === 'error') {
          onError(data.message || 'Unknown error occurred');
          ws.close();
        }
      } catch (error) {
        console.error('Error parsing WebSocket data:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      onError('Connection error occurred');
    };

    return ws;
  }

  async deploy(request: DeploymentRequest): Promise<DeploymentResponse> {
    console.log('[API Client] Deploy request:', {
      endpoint: '/api/deploy',
      method: 'POST',
      baseURL: API_URL,
      hasToken: !!this.token,
      language: request.language,
      code_length: request.code?.length,
      space_name: request.space_name,
      existing_repo_id: request.existing_repo_id,
    });
    
    try {
      const response = await this.client.post<DeploymentResponse>('/api/deploy', request);
      console.log('[API Client] Deploy response:', response.status, response.data);
      return response.data;
    } catch (error: any) {
      console.error('[API Client] Deploy error:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        message: error.message,
      });
      throw error;
    }
  }

  async importProject(url: string, preferLocal: boolean = false): Promise<any> {
    const response = await this.client.post('/api/import', { url, prefer_local: preferLocal });
    return response.data;
  }

  async importSpace(username: string, spaceName: string): Promise<any> {
    const response = await this.client.get(`/api/import/space/${username}/${spaceName}`);
    return response.data;
  }

  async importModel(modelId: string, preferLocal: boolean = false): Promise<any> {
    const response = await this.client.get(`/api/import/model/${modelId}`, {
      params: { prefer_local: preferLocal }
    });
    return response.data;
  }

  async importGithub(owner: string, repo: string): Promise<any> {
    const response = await this.client.get(`/api/import/github/${owner}/${repo}`);
    return response.data;
  }

  logout() {
    this.token = null;
  }

  async getTrendingAnycoderApps(): Promise<any[]> {
    try {
      // Fetch from HuggingFace API directly
      const response = await axios.get('https://huggingface.co/api/spaces', {
        timeout: 5000,
      });
      
      // Filter for apps with 'anycoder' tag and sort by trendingScore
      const anycoderApps = response.data
        .filter((space: any) => space.tags && space.tags.includes('anycoder'))
        .sort((a: any, b: any) => (b.trendingScore || 0) - (a.trendingScore || 0))
        .slice(0, 6);
      
      return anycoderApps;
    } catch (error) {
      console.error('Failed to fetch trending anycoder apps:', error);
      return [];
    }
  }
}

// Export singleton instance
export const apiClient = new ApiClient();


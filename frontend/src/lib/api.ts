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
    });

    // Add auth token to requests if available
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });

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
    const response = await this.client.get<Model[]>('/api/models');
    return response.data;
  }

  async getLanguages(): Promise<{ languages: Language[] }> {
    const response = await this.client.get<{ languages: Language[] }>('/api/languages');
    return response.data;
  }

  async getAuthStatus(): Promise<AuthStatus> {
    try {
      const response = await this.client.get<AuthStatus>('/api/auth/status');
      return response.data;
    } catch (error) {
      return {
        authenticated: false,
        message: 'Not authenticated',
      };
    }
  }

  // Stream-based code generation using EventSource (Server-Sent Events)
  generateCodeStream(
    request: CodeGenerationRequest,
    onChunk: (content: string) => void,
    onComplete: (code: string) => void,
    onError: (error: string) => void
  ): () => void {
    // Build the URL correctly whether we have a base URL or not
    const baseUrl = API_URL || window.location.origin;
    const url = new URL('/api/generate', baseUrl);
    url.search = new URLSearchParams({
      query: request.query,
      language: request.language,
      model_id: request.model_id,
      provider: request.provider,
    }).toString();
    
    const eventSource = new EventSource(url.toString());

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'chunk' && data.content) {
          onChunk(data.content);
        } else if (data.type === 'complete' && data.code) {
          onComplete(data.code);
          eventSource.close();
        } else if (data.type === 'error') {
          onError(data.message || 'Unknown error occurred');
          eventSource.close();
        }
      } catch (error) {
        console.error('Error parsing SSE data:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('EventSource error:', error);
      onError('Connection error occurred');
      eventSource.close();
    };

    // Return cleanup function
    return () => {
      eventSource.close();
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
    const response = await this.client.post<DeploymentResponse>('/api/deploy', request);
    return response.data;
  }

  logout() {
    this.token = null;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();


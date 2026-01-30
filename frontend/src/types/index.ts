// Type definitions for AnyCoder frontend

export interface Model {
  name: string;
  id: string;
  description: string;
  supports_images?: boolean;
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  image_url?: string;  // For vision models
}

export interface CodeGenerationRequest {
  query: string;
  language: string;
  model_id: string;
  provider: string;
  history: string[][];
  agent_mode: boolean;
  existing_repo_id?: string;  // For auto-deploy to update existing space
  skip_auto_deploy?: boolean;  // Skip auto-deploy (for PR creation)
  image_url?: string;  // For vision models like GLM-4.6V
}

export interface CodeGenerationResponse {
  code: string;
  history: string[][];
  status: string;
}

export interface StreamChunk {
  type: 'chunk' | 'complete' | 'error' | 'status';
  content?: string;
  code?: string;
  message?: string;
  progress?: number;
  timestamp?: string;
}

export interface AuthStatus {
  authenticated: boolean;
  username?: string;
  message: string;
}

export interface DeploymentRequest {
  code: string;
  space_name?: string;
  language: string;
  requirements?: string;
  existing_repo_id?: string;  // For updating existing spaces
  commit_message?: string;
  history?: Array<{ role: string; content: string }>;  // Chat history for tracking
}

export interface DeploymentResponse {
  success: boolean;
  space_url?: string;
  message: string;
  dev_mode?: boolean;
  repo_id?: string;
}

export type Language = 'html' | 'gradio' | 'transformers.js' | 'streamlit' | 'comfyui' | 'react' | 'daggr';


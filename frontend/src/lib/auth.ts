// HuggingFace OAuth authentication utilities
import { oauthLoginUrl, oauthHandleRedirectIfPresent } from "@huggingface/hub";

const STORAGE_KEY = 'hf_oauth_token';
const USER_INFO_KEY = 'hf_user_info';
const DEV_MODE_KEY = 'hf_dev_mode';

// Check if we're in development mode (localhost)
const isDevelopment = typeof window !== 'undefined' && 
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

export interface OAuthUserInfo {
  id: string;
  name: string;
  preferredUsername?: string;
  avatarUrl?: string;
}

export interface OAuthResult {
  accessToken: string;
  accessTokenExpiresAt: Date;
  userInfo: OAuthUserInfo;
}

/**
 * Initialize OAuth and check if user is logged in
 * Returns OAuth result if user is already logged in
 */
export async function initializeOAuth(): Promise<OAuthResult | null> {
  try {
    // In development mode, check for dev mode login first
    if (isDevelopment && isDevModeEnabled()) {
      const storedToken = getStoredToken();
      const storedUserInfo = getStoredUserInfo();
      
      if (storedToken && storedUserInfo) {
        return {
          accessToken: storedToken,
          accessTokenExpiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
          userInfo: storedUserInfo,
        };
      }
      return null;
    }
    
    // Check if we're handling an OAuth redirect
    const oauthResult = await oauthHandleRedirectIfPresent();
    
    if (oauthResult) {
      // Store the OAuth result
      storeOAuthData(oauthResult);
      return oauthResult;
    }
    
    // Check if we have stored credentials
    const storedToken = getStoredToken();
    const storedUserInfo = getStoredUserInfo();
    
    if (storedToken && storedUserInfo) {
      return {
        accessToken: storedToken,
        accessTokenExpiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // Assume 24h
        userInfo: storedUserInfo,
      };
    }
    
    return null;
  } catch (error) {
    console.error('OAuth initialization error:', error);
    return null;
  }
}

/**
 * Redirect to HuggingFace OAuth login page
 */
export async function loginWithHuggingFace(): Promise<void> {
  try {
    const loginUrl = await oauthLoginUrl({
      // Redirect back to the current page
      redirectUrl: window.location.href,
      // Request scopes - adjust as needed
      scopes: "openid profile inference-api",
    });
    
    window.location.href = loginUrl;
  } catch (error) {
    console.error('Failed to initiate OAuth login:', error);
    throw new Error('Failed to start login process');
  }
}

/**
 * Logout and clear stored credentials
 */
export function logout(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(USER_INFO_KEY);
    localStorage.removeItem(DEV_MODE_KEY);
  }
}

/**
 * Store OAuth data in localStorage
 */
function storeOAuthData(result: OAuthResult): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, result.accessToken);
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(result.userInfo));
  }
}

/**
 * Get stored access token
 */
export function getStoredToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(STORAGE_KEY);
  }
  return null;
}

/**
 * Get stored user info
 */
export function getStoredUserInfo(): OAuthUserInfo | null {
  if (typeof window !== 'undefined') {
    const userInfoStr = localStorage.getItem(USER_INFO_KEY);
    if (userInfoStr) {
      try {
        return JSON.parse(userInfoStr);
      } catch {
        return null;
      }
    }
  }
  return null;
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return getStoredToken() !== null;
}

/**
 * Development mode login (mock authentication)
 */
export function loginDevMode(username: string): OAuthResult {
  const mockToken = `dev_token_${username}_${Date.now()}`;
  const mockUserInfo: OAuthUserInfo = {
    id: `dev_${Date.now()}`,
    name: username,
    preferredUsername: username.toLowerCase().replace(/\s+/g, '_'),
    avatarUrl: `https://ui-avatars.com/api/?name=${encodeURIComponent(username)}&background=random&size=128`,
  };
  
  const result: OAuthResult = {
    accessToken: mockToken,
    accessTokenExpiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
    userInfo: mockUserInfo,
  };
  
  // Store the mock data
  storeOAuthData(result);
  // Mark as dev mode
  if (typeof window !== 'undefined') {
    localStorage.setItem(DEV_MODE_KEY, 'true');
  }
  
  return result;
}

/**
 * Check if dev mode is enabled
 */
export function isDevModeEnabled(): boolean {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(DEV_MODE_KEY) === 'true';
  }
  return false;
}

/**
 * Check if we're in development environment
 */
export function isDevelopmentMode(): boolean {
  return isDevelopment;
}


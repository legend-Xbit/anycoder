// HuggingFace OAuth authentication utilities (Server-side flow for Docker Spaces)

const STORAGE_KEY = 'hf_oauth_token';
const SESSION_KEY = 'hf_session_token';  // NEW: Store session UUID
const USER_INFO_KEY = 'hf_user_info';
const DEV_MODE_KEY = 'hf_dev_mode';
const API_BASE = '/api';

// Check if we're in development mode (localhost)
const isDevelopment = typeof window !== 'undefined' && 
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

export interface OAuthUserInfo {
  id?: string;
  sub?: string;
  name: string;
  preferred_username?: string;
  preferredUsername?: string;
  picture?: string;
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
    
    // Check if we're handling an OAuth callback (session parameter in URL)
    const urlParams = new URLSearchParams(window.location.search);
    const sessionToken = urlParams.get('session');
    
    if (sessionToken) {
      // Fetch session data from backend
      try {
        const response = await fetch(`${API_BASE}/auth/session?session=${sessionToken}`);
        if (response.ok) {
          const data = await response.json();
          
          // Normalize user info
          const userInfo: OAuthUserInfo = {
            id: data.user_info.sub || data.user_info.id,
            name: data.user_info.name,
            preferredUsername: data.user_info.preferred_username || data.user_info.preferredUsername,
            avatarUrl: data.user_info.picture || data.user_info.avatarUrl,
          };
          
          const oauthResult: OAuthResult = {
            accessToken: data.access_token,
            accessTokenExpiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
            userInfo,
          };
          
          // Store the OAuth result AND session token
          storeOAuthData(oauthResult);
          storeSessionToken(sessionToken);  // NEW: Store session UUID
          
          // Clean up URL
          window.history.replaceState({}, document.title, window.location.pathname);
          
          return oauthResult;
        }
      } catch (error) {
        console.error('Failed to fetch session:', error);
      }
    }
    
    // Check if we have stored credentials
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
  } catch (error) {
    console.error('OAuth initialization error:', error);
    return null;
  }
}

/**
 * Redirect to HuggingFace OAuth login page (via backend)
 */
export async function loginWithHuggingFace(): Promise<void> {
  try {
    // Call backend to get OAuth URL
    const response = await fetch(`${API_BASE}/auth/login`);
    if (!response.ok) {
      throw new Error('Failed to get login URL');
    }
    
    const data = await response.json();
    // Redirect to the OAuth authorization URL
    window.location.href = data.login_url;
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
    localStorage.removeItem(SESSION_KEY);  // NEW: Clear session token
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
 * Store session token in localStorage
 */
function storeSessionToken(sessionToken: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(SESSION_KEY, sessionToken);
  }
}

/**
 * Get stored session token
 */
export function getStoredSessionToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(SESSION_KEY);
  }
  return null;
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
 * Validate authentication with backend
 * Returns true if authenticated, false if session expired
 */
export async function validateAuthentication(): Promise<boolean> {
  const token = getStoredToken();
  if (!token) {
    return false;
  }

  // Skip validation for dev mode tokens
  if (isDevelopment && token.startsWith('dev_token_')) {
    return true;
  }

  try {
    const response = await fetch(`${API_BASE}/auth/status`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (response.status === 401) {
      // Session expired, clean up
      logout();
      return false;
    }

    if (!response.ok) {
      return false;
    }

    const data = await response.json();
    return data.authenticated === true;
  } catch (error) {
    console.error('Failed to validate authentication:', error);
    return false;
  }
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


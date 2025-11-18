'use client';

import { useState, useEffect } from 'react';
import { 
  initializeOAuth, 
  loginWithHuggingFace, 
  loginDevMode,
  logout, 
  getStoredUserInfo, 
  isAuthenticated,
  isDevelopmentMode 
} from '@/lib/auth';
import { apiClient } from '@/lib/api';
import type { OAuthUserInfo } from '@/lib/auth';

export default function Header() {
  const [userInfo, setUserInfo] = useState<OAuthUserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showDevLogin, setShowDevLogin] = useState(false);
  const [devUsername, setDevUsername] = useState('');
  const isDevMode = isDevelopmentMode();

  useEffect(() => {
    handleOAuthInit();
  }, []);

  const handleOAuthInit = async () => {
    setIsLoading(true);
    try {
      const oauthResult = await initializeOAuth();
      
      if (oauthResult) {
        setUserInfo(oauthResult.userInfo);
        // Set token in API client
        apiClient.setToken(oauthResult.accessToken);
      } else {
        // Check if we have stored user info
        const storedUserInfo = getStoredUserInfo();
        if (storedUserInfo) {
          setUserInfo(storedUserInfo);
        }
      }
    } catch (error) {
      console.error('OAuth initialization error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogin = async () => {
    try {
      await loginWithHuggingFace();
    } catch (error) {
      console.error('Login failed:', error);
      alert('Failed to start login process. Please try again.');
    }
  };

  const handleLogout = () => {
    logout();
    apiClient.logout();
    setUserInfo(null);
    // Reload page to clear state
    window.location.reload();
  };

  const handleDevLogin = () => {
    if (!devUsername.trim()) {
      alert('Please enter a username');
      return;
    }
    
    try {
      const result = loginDevMode(devUsername);
      setUserInfo(result.userInfo);
      apiClient.setToken(result.accessToken);
      setShowDevLogin(false);
      setDevUsername('');
    } catch (error) {
      console.error('Dev login failed:', error);
      alert('Failed to login in dev mode');
    }
  };

  return (
    <header className="bg-[#28282a] text-white border-b border-[#48484a]">
      <div className="flex items-center justify-between px-3 md:px-5 h-12 md:h-14">
          <div className="flex items-center space-x-2 md:space-x-3">
            <h1 className="text-sm md:text-base font-semibold text-[#e5e5e7] tracking-tight">AnyCoder</h1>
          </div>
          
          <div className="flex items-center space-x-4">
            {isLoading ? (
              <div className="px-4 py-2">
                <span className="text-xs text-[#86868b] font-medium">Loading...</span>
              </div>
            ) : userInfo ? (
              <div className="flex items-center space-x-2 md:space-x-3">
                {userInfo.avatarUrl && (
                  <img 
                    src={userInfo.avatarUrl} 
                    alt={userInfo.name}
                    className="w-6 h-6 md:w-7 md:h-7 rounded-full ring-2 ring-[#48484a]"
                  />
                )}
                <span className="hidden sm:inline text-xs md:text-sm text-[#e5e5e7] font-medium truncate max-w-[100px] md:max-w-none">
                  {userInfo.preferredUsername || userInfo.name}
                </span>
                <button
                  onClick={handleLogout}
                  className="px-3 md:px-4 py-1.5 md:py-2 bg-[#3a3a3c] text-[#e5e5e7] text-xs rounded-lg hover:bg-[#48484a] transition-all border border-[#48484a] font-semibold shadow-sm active:scale-95"
                >
                  Logout
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-2 md:space-x-3">
                {/* Dev Mode Login (only on localhost) */}
                {isDevMode && (
                  <>
                    {showDevLogin ? (
                      <div className="flex items-center space-x-2 bg-[#3a3a3c] px-2 md:px-3 py-1.5 md:py-2 rounded-lg border border-[#ff9f0a] shadow-lg">
                        <span className="hidden sm:inline text-xs text-[#ff9f0a] font-semibold">DEV</span>
                        <input
                          type="text"
                          value={devUsername}
                          onChange={(e) => setDevUsername(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && handleDevLogin()}
                          placeholder="username"
                          className="px-3 py-1.5 rounded-lg text-xs bg-[#2c2c2e] text-[#e5e5e7] border border-[#48484a] focus:outline-none focus:ring-2 focus:ring-[#ff9f0a] focus:border-transparent w-28 font-medium"
                          autoFocus
                        />
                        <button
                          onClick={handleDevLogin}
                          className="px-3 py-1.5 bg-[#ff9f0a] text-white rounded-lg hover:bg-[#ff8800] text-xs font-semibold shadow-sm active:scale-95"
                        >
                          OK
                        </button>
                        <button
                          onClick={() => {
                            setShowDevLogin(false);
                            setDevUsername('');
                          }}
                          className="text-[#86868b] hover:text-[#e5e5e7] text-sm transition-colors"
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setShowDevLogin(true)}
                        className="px-4 py-2 bg-[#ff9f0a] text-white rounded-lg hover:bg-[#ff8800] transition-all text-xs flex items-center space-x-2 font-semibold shadow-sm active:scale-95"
                        title="Dev Mode (localhost)"
                      >
                        <span>🔧</span>
                        <span>Dev Login</span>
                      </button>
                    )}
                    <span className="text-[#86868b] text-xs font-medium">or</span>
                  </>
                )}
                
                {/* OAuth Login */}
                <button
                  onClick={handleLogin}
                  className="px-3 md:px-4 py-1.5 md:py-2 bg-[#007aff] text-white rounded-lg hover:bg-[#0051d5] transition-all text-xs flex items-center space-x-1.5 md:space-x-2 font-semibold shadow-md active:scale-95"
                >
                  <span>🤗</span>
                  <span className="hidden xs:inline">Sign in</span>
                  <span className="xs:hidden">Login</span>
                </button>
              </div>
            )}
          </div>
        </div>
    </header>
  );
}


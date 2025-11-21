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
    <header className="bg-[#000000]/80 backdrop-blur-xl text-white border-b border-[#424245]/30">
      <div className="flex items-center justify-between px-3 md:px-6 h-12 md:h-14">
          <div className="flex items-center space-x-2 md:space-x-3">
            <h1 className="text-sm md:text-base font-medium text-[#f5f5f7]">AnyCoder</h1>
          </div>
          
          <div className="flex items-center space-x-3">
            {isLoading ? (
              <span className="text-xs text-[#86868b]">Loading...</span>
            ) : userInfo ? (
              <div className="flex items-center space-x-2 md:space-x-3">
                {userInfo.avatarUrl && (
                  <img 
                    src={userInfo.avatarUrl} 
                    alt={userInfo.name}
                    className="w-6 h-6 md:w-7 md:h-7 rounded-full"
                  />
                )}
                <span className="hidden sm:inline text-xs md:text-sm text-[#f5f5f7] font-medium truncate max-w-[100px] md:max-w-none">
                  {userInfo.preferredUsername || userInfo.name}
                </span>
                <button
                  onClick={handleLogout}
                  className="px-3 md:px-3 py-1.5 md:py-1.5 text-[#f5f5f7] text-sm hover:text-white transition-colors"
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
                      <div className="flex items-center space-x-2">
                        <input
                          type="text"
                          value={devUsername}
                          onChange={(e) => setDevUsername(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && handleDevLogin()}
                          placeholder="username"
                          className="px-3 py-1.5 rounded-lg text-sm bg-[#1d1d1f] text-[#f5f5f7] border border-[#424245] focus:outline-none focus:border-white/50 w-32 font-medium"
                          autoFocus
                        />
                        <button
                          onClick={handleDevLogin}
                          className="px-3 py-1.5 bg-white text-black rounded-lg text-sm hover:bg-[#f5f5f7] font-medium"
                        >
                          OK
                        </button>
                        <button
                          onClick={() => {
                            setShowDevLogin(false);
                            setDevUsername('');
                          }}
                          className="text-[#86868b] hover:text-[#f5f5f7] text-sm"
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                    <button
                      onClick={() => setShowDevLogin(true)}
                      className="px-3 py-1.5 text-sm text-[#f5f5f7] hover:text-white transition-colors"
                      title="Dev Mode"
                    >
                      Dev
                    </button>
                    )}
                    <span className="text-[#86868b] text-sm">or</span>
                  </>
                )}
                
                {/* OAuth Login */}
                <button
                  onClick={handleLogin}
                  className="px-3 md:px-4 py-1.5 md:py-2 bg-white text-black rounded-full text-sm hover:bg-[#f5f5f7] transition-all font-medium"
                >
                  Sign in
                </button>
              </div>
            )}
          </div>
        </div>
    </header>
  );
}


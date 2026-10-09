import React, { useState, useEffect } from 'react';
import { WifiOff, ServerCrash, RefreshCw } from 'lucide-react';
import api from '../api/client';

const NetworkStatus: React.FC = () => {
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [isBackendDown, setIsBackendDown] = useState(false);
  const [isChecking, setIsChecking] = useState(false);

  useEffect(() => {
    const handleOffline = () => setIsOffline(true);
    const handleOnline = () => {
      setIsOffline(false);
      checkBackend();
    };

    const handleBackendError = () => {
      // Only show backend down if we are actually online
      if (navigator.onLine) {
        setIsBackendDown(true);
      }
    };

    window.addEventListener('offline', handleOffline);
    window.addEventListener('online', handleOnline);
    window.addEventListener('backend-error', handleBackendError);

    return () => {
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('backend-error', handleBackendError);
    };
  }, []);

  const checkBackend = async () => {
    if (!navigator.onLine) return;
    
    setIsChecking(true);
    try {
      // Hit a lightweight endpoint or healthcheck to verify backend is up
      await api.get('/health', {
        // bypass cache for this request
        cache: false,
        timeout: 3000
      } as any);
      setIsBackendDown(false);
    } catch (err) {
      setIsBackendDown(true);
    } finally {
      setIsChecking(false);
    }
  };

  if (!isOffline && !isBackendDown) {
    return null; // Everything is fine
  }

  return (
    <div className="fixed inset-0 z-[9999] bg-slate-900/95 backdrop-blur-sm flex flex-col items-center justify-center text-slate-100 font-sans p-6">
      <div className="max-w-md w-full bg-slate-800 rounded-2xl shadow-2xl p-8 border border-slate-700 text-center animate-in fade-in zoom-in duration-300">
        <div className="w-20 h-20 bg-slate-900/50 rounded-full flex items-center justify-center mx-auto mb-6 shadow-inner">
          {isOffline ? (
            <WifiOff className="w-10 h-10 text-rose-500" />
          ) : (
            <ServerCrash className="w-10 h-10 text-orange-500" />
          )}
        </div>
        
        <h2 className="text-2xl font-bold text-white mb-2">
          {isOffline ? 'You are offline' : 'Cannot reach server'}
        </h2>
        
        <p className="text-slate-400 mb-8 leading-relaxed">
          {isOffline 
            ? 'Please check your internet connection. The application will automatically resume when you are back online.'
            : 'We are having trouble connecting to the backend server. It might be down or experiencing issues.'}
        </p>

        <button
          onClick={isOffline ? () => window.location.reload() : checkBackend}
          disabled={isChecking || (isOffline && !navigator.onLine)}
          className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-medium py-3 px-4 rounded-xl transition-all flex items-center justify-center gap-2 group"
        >
          <RefreshCw className={`w-5 h-5 ${isChecking ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
          {isChecking ? 'Checking connection...' : 'Try Again'}
        </button>
      </div>
    </div>
  );
};

export default NetworkStatus;

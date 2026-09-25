import { useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Menu } from 'lucide-react';
import Sidebar from './Sidebar';

export default function MainLayout() {
  const { isAuthenticated } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return (
    <div className="flex h-screen overflow-hidden bg-bg-primary">
      <Sidebar isOpen={isMobileMenuOpen} setIsOpen={setIsMobileMenuOpen} />
      
      <main className="flex flex-1 flex-col min-w-0 overflow-y-auto bg-bg-primary">
        {/* Mobile Header */}
        <header className="md:hidden flex items-center justify-between border-b border-border bg-white/85 p-4 backdrop-blur-md sticky top-0 z-30">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-600 to-indigo-500 shadow-sm">
              <span className="text-white font-bold text-xs">RP</span>
            </div>
            <h1 className="text-sm font-bold text-text-primary">RetailPOS</h1>
          </div>
          <button 
            onClick={() => setIsMobileMenuOpen(true)} 
            className="rounded-md p-1.5 text-text-muted hover:bg-bg-hover hover:text-text-primary"
          >
            <Menu className="h-6 w-6" />
          </button>
        </header>

        <div className="mx-auto w-full max-w-[1600px] p-4 sm:p-6 md:p-8 animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard,
  ShoppingCart,
  Package,
  PackagePlus,
  Warehouse,
  Receipt,
  BarChart3,
  Users,
  Settings,
  LogOut,
  Store,
  X,
} from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', roles: ['admin', 'staff', 'inventory'] },
  { to: '/pos', icon: ShoppingCart, label: 'New Bill (POS)', roles: ['admin', 'staff'] },
  { to: '/products', icon: Package, label: 'Products', roles: ['admin', 'staff', 'inventory'] },
  { to: '/add-stock', icon: PackagePlus, label: 'Add Stock', roles: ['admin', 'inventory'] },
  { to: '/inventory', icon: Warehouse, label: 'Inventory', roles: ['admin', 'inventory'] },
  { to: '/sales', icon: Receipt, label: 'Sales History', roles: ['admin', 'staff'] },
  { to: '/reports', icon: BarChart3, label: 'Reports', roles: ['admin'] },
  { to: '/users', icon: Users, label: 'Users', roles: ['admin'] },
  { to: '/settings', icon: Settings, label: 'Settings', roles: ['admin'] },
];

interface SidebarProps {
  isOpen?: boolean;
  setIsOpen?: (isOpen: boolean) => void;
}

export default function Sidebar({ isOpen = false, setIsOpen }: SidebarProps) {
  const { user, logout, hasRole } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const filteredNav = navItems.filter((item) =>
    item.roles.some((role) => hasRole(role))
  );

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm transition-opacity md:hidden"
          onClick={() => setIsOpen?.(false)}
        />
      )}

      <aside className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-white/85 backdrop-blur-lg shadow-sm transition-transform duration-300 ease-in-out md:static md:shrink-0 md:translate-x-0 ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        {/* Logo / Store Name */}
        <div className="flex items-center justify-between border-b border-border px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 overflow-hidden items-center justify-center rounded-lg shadow-md">
              <img src="/logo.jpg" alt="Moira Luxe Logo" className="h-full w-full object-cover" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-text-primary">Moira Luxe</h1>
              <p className="text-xs text-text-muted">Billing & Inventory</p>
            </div>
          </div>
          <button onClick={() => setIsOpen?.(false)} className="rounded-md p-1 text-text-muted hover:bg-bg-hover hover:text-text-primary md:hidden">
            <X className="h-5 w-5" />
          </button>
        </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <div className="space-y-1">
          {filteredNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200
                ${isActive
                  ? 'bg-accent text-white shadow-md shadow-accent/25'
                  : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                }`
              }
            >
              <item.icon className="h-4.5 w-4.5" />
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* User / Logout */}
      <div className="border-t border-border p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-600/15 text-sm font-bold text-indigo-600">
            {user?.name?.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="truncate text-sm font-medium text-text-primary">{user?.name}</p>
            <p className="text-xs text-text-muted capitalize">{user?.role}</p>
          </div>
          <button
            onClick={handleLogout}
            className="rounded-lg p-2 text-text-muted transition-colors hover:bg-danger/10 hover:text-danger"
            title="Logout"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
    </>
  );
}

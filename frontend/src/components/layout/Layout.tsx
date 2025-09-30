import React from 'react';
import { Home, MessageSquare, BarChart3, Users, Settings } from 'lucide-react';
import Sidebar from './Sidebar';
import Header from './Header';
import { useNavigation } from '../../hooks/useNavigation';

export interface LayoutProps {
  children: React.ReactNode;
  className?: string;
}

const Layout: React.FC<LayoutProps> = ({ children, className }) => {
  const {
    activeRoute,
    setActiveRoute,
    sidebarCollapsed,
    setSidebarCollapsed,
    toggleSidebar,
    isMobile
  } = useNavigation();

  // Create enhanced sidebar navigation items with navigation handlers
  const enhancedNavigationItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: <Home />,
      href: '/',
      active: activeRoute === '/',
      onClick: () => setActiveRoute('/'),
    },
    {
      id: 'campaigns',
      label: 'Criar Disparo',
      icon: <MessageSquare />,
      href: '/campaigns',
      active: activeRoute === '/campaigns',
      onClick: () => setActiveRoute('/campaigns'),
    },
    {
      id: 'analytics',
      label: 'Analytics',
      icon: <BarChart3 />,
      href: '/analytics',
      active: activeRoute === '/analytics',
      onClick: () => setActiveRoute('/analytics'),
    },
    {
      id: 'contacts',
      label: 'Contatos',
      icon: <Users />,
      href: '/contacts',
      active: activeRoute === '/contacts',
      onClick: () => setActiveRoute('/contacts'),
    },
    {
      id: 'settings',
      label: 'Configurações',
      icon: <Settings />,
      href: '/settings',
      active: activeRoute === '/settings',
      onClick: () => setActiveRoute('/settings'),
    },
  ];

  const mainClasses = [
    'min-h-screen bg-gray-50 transition-all duration-300 ease-in-out',
    sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64',
    className
  ].filter(Boolean).join(' ');

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebar}
        navigationItems={enhancedNavigationItems}
      />

      {/* Main content area */}
      <div className={mainClasses}>
        {/* Header */}
        <Header
          onToggleSidebar={toggleSidebar}
          sidebarCollapsed={sidebarCollapsed}
        />

        {/* Main content */}
        <main className="flex-1 overflow-x-hidden">
          <div className="p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
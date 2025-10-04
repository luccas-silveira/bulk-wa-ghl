import React from 'react';
import Header from './Header';

export interface LayoutProps {
  children: React.ReactNode;
  className?: string;
  currentRoute?: string;
  onNavigate?: (route: string) => void;
}

const Layout: React.FC<LayoutProps> = ({ children, className, currentRoute, onNavigate }) => {
  const containerClasses = [
    'min-h-screen bg-gray-50',
    className
  ].filter(Boolean).join(' ');

  return (
    <div className={containerClasses}>
      <Header currentRoute={currentRoute} onNavigate={onNavigate} />

      <main className="max-w-6xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>
    </div>
  );
};

export default Layout;

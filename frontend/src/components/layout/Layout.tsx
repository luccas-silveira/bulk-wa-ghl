import React from 'react';
import Header from './Header';

export interface LayoutProps {
  children: React.ReactNode;
  className?: string;
}

const Layout: React.FC<LayoutProps> = ({ children, className }) => {
  const containerClasses = [
    'min-h-screen bg-gray-50',
    className
  ].filter(Boolean).join(' ');

  return (
    <div className={containerClasses}>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-white focus:rounded focus:shadow-ghl"
      >
        Pular para conteúdo
      </a>

      <Header />

      <main id="main-content" className="max-w-6xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>
    </div>
  );
};

export default Layout;

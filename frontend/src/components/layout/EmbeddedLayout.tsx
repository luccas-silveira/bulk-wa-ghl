import React from 'react';
import { X } from 'lucide-react';

interface EmbeddedLayoutProps {
  children: React.ReactNode;
}

const EmbeddedLayout: React.FC<EmbeddedLayoutProps> = ({ children }) => {
  const handleClose = () => {
    window.parent.postMessage('wpp:close', '*');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <div className="bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between">
        <span className="text-sm font-semibold uppercase tracking-wide text-primary-600">
          WPP Manager
        </span>
        <button
          onClick={handleClose}
          aria-label="Fechar"
          className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors"
        >
          <X size={18} />
        </button>
      </div>
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>
    </div>
  );
};

export default EmbeddedLayout;

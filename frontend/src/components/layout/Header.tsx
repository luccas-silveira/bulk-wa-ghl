import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export interface HeaderProps {
  className?: string;
}

const Header: React.FC<HeaderProps> = ({ className }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const currentRoute = location.pathname;

  const headerClasses = [
    'bg-white border-b border-gray-200',
    className
  ].filter(Boolean).join(' ');

  const isActive = (route: string) => currentRoute === route;

  const buttonBaseClasses = 'px-4 py-2 font-medium transition-colors';
  const activeClasses = 'text-blue-600 border-b-2 border-blue-600';
  const inactiveClasses = 'text-gray-600 hover:text-blue-600 hover:border-b-2 hover:border-blue-600';

  return (
    <header className={headerClasses}>
      <div className="px-4 sm:px-6 lg:px-8 py-3">
        <div className="flex items-center justify-between">
          {/* Logo/Brand */}
          <span className="text-sm font-semibold uppercase tracking-wide text-primary-600">
            WPP Manager
          </span>

          {/* Navigation Tabs */}
          <nav className="flex gap-2 border-b border-gray-200">
            <button
              onClick={() => navigate('/')}
              className={`${buttonBaseClasses} ${isActive('/') ? activeClasses : inactiveClasses}`}
            >
              Estatísticas
            </button>
            <button
              onClick={() => navigate('/campaigns')}
              className={`${buttonBaseClasses} ${isActive('/campaigns') ? activeClasses : inactiveClasses}`}
            >
              Gerenciar Campanhas
            </button>
            <button
              onClick={() => navigate('/campaigns/new')}
              className={`${buttonBaseClasses} ${isActive('/campaigns/new') ? activeClasses : inactiveClasses}`}
            >
              Criar Campanha
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
};

export default Header;

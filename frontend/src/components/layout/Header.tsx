import React from 'react';
import {
  Search,
  Bell,
  Settings,
  User,
  ChevronDown,
  Menu,
  HelpCircle,
  LogOut
} from 'lucide-react';
import Button from '../ui/Button';
import { SearchInput } from '../ui/Input';
import Avatar from '../ui/Avatar';
import Badge from '../ui/Badge';

export interface HeaderProps {
  onToggleSidebar?: () => void;
  sidebarCollapsed?: boolean;
  className?: string;
}

export interface BreadcrumbItem {
  label: string;
  href?: string;
  current?: boolean;
}

const Header: React.FC<HeaderProps> = ({
  onToggleSidebar,
  sidebarCollapsed = false,
  className,
}) => {
  const [searchValue, setSearchValue] = React.useState('');
  const [showUserMenu, setShowUserMenu] = React.useState(false);
  const [showNotifications, setShowNotifications] = React.useState(false);

  const breadcrumbs: BreadcrumbItem[] = [
    { label: 'Dashboard', href: '/' },
    { label: 'WhatsApp Campaigns', current: true },
  ];

  const notifications = [
    {
      id: 1,
      title: 'Nova campanha criada',
      message: 'A campanha "Promoção Black Friday" foi criada com sucesso',
      time: '2 min atrás',
      unread: true,
    },
    {
      id: 2,
      title: 'Sessão WAHA conectada',
      message: 'WhatsApp Principal está agora conectado',
      time: '5 min atrás',
      unread: true,
    },
    {
      id: 3,
      title: 'Relatório mensal disponível',
      message: 'Seu relatório de setembro está pronto',
      time: '1 hora atrás',
      unread: false,
    },
  ];

  const unreadCount = notifications.filter(n => n.unread).length;

  const headerClasses = [
    'bg-white border-b border-gray-200 z-30',
    'transition-all duration-300 ease-in-out',
    sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64',
    className
  ].filter(Boolean).join(' ');

  return (
    <header className={headerClasses}>
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left section */}
          <div className="flex items-center space-x-4">
            {/* Mobile menu button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggleSidebar}
              className="lg:hidden"
            >
              <Menu className="w-5 h-5" />
            </Button>

            {/* Breadcrumbs */}
            <nav className="hidden sm:flex" aria-label="Breadcrumb">
              <ol className="flex items-center space-x-2">
                {breadcrumbs.map((item, index) => (
                  <li key={index} className="flex items-center">
                    {index > 0 && (
                      <ChevronDown className="w-4 h-4 text-gray-400 mx-2 rotate-[-90deg]" />
                    )}
                    {item.current ? (
                      <span className="text-sm font-medium text-gray-900">
                        {item.label}
                      </span>
                    ) : (
                      <a
                        href={item.href}
                        className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
                      >
                        {item.label}
                      </a>
                    )}
                  </li>
                ))}
              </ol>
            </nav>
          </div>

          {/* Center section - Search */}
          <div className="flex-1 max-w-lg mx-4">
            <SearchInput
              placeholder="Buscar campanhas, contatos..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              onClear={() => setSearchValue('')}
              size="sm"
            />
          </div>

          {/* Right section */}
          <div className="flex items-center space-x-3">
            {/* Help button */}
            <Button variant="ghost" size="sm">
              <HelpCircle className="w-5 h-5" />
            </Button>

            {/* Notifications */}
            <div className="relative">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative"
              >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                  <Badge
                    variant="error"
                    size="sm"
                    className="absolute -top-1 -right-1 min-w-[1.25rem] h-5 flex items-center justify-center text-xs"
                  >
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </Badge>
                )}
              </Button>

              {/* Notifications dropdown */}
              {showNotifications && (
                <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
                  <div className="p-4 border-b border-gray-200">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-gray-900">
                        Notificações
                      </h3>
                      {unreadCount > 0 && (
                        <Badge variant="primary" size="sm">
                          {unreadCount} novas
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="max-h-96 overflow-y-auto">
                    {notifications.map((notification) => (
                      <div
                        key={notification.id}
                        className={`p-4 border-b border-gray-100 hover:bg-gray-50 cursor-pointer ${
                          notification.unread ? 'bg-blue-50' : ''
                        }`}
                      >
                        <div className="flex items-start space-x-3">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900">
                              {notification.title}
                            </p>
                            <p className="text-sm text-gray-600 mt-1">
                              {notification.message}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                              {notification.time}
                            </p>
                          </div>
                          {notification.unread && (
                            <div className="w-2 h-2 bg-primary-500 rounded-full mt-2" />
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="p-3 border-t border-gray-200">
                    <Button variant="ghost" size="sm" fullWidth>
                      Ver todas as notificações
                    </Button>
                  </div>
                </div>
              )}
            </div>

            {/* User menu */}
            <div className="relative">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center space-x-2 pl-2"
              >
                <Avatar
                  size="sm"
                  fallback="U"
                  status="online"
                  showStatus
                />
                <ChevronDown className="w-4 h-4" />
              </Button>

              {/* User dropdown */}
              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
                  <div className="p-3 border-b border-gray-200">
                    <div className="flex items-center space-x-3">
                      <Avatar size="md" fallback="U" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900">
                          Usuário
                        </p>
                        <p className="text-xs text-gray-500 truncate">
                          usuario@empresa.com
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="py-1">
                    <a
                      href="/profile"
                      className="flex items-center px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <User className="w-4 h-4 mr-3" />
                      Meu Perfil
                    </a>
                    <a
                      href="/settings"
                      className="flex items-center px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <Settings className="w-4 h-4 mr-3" />
                      Configurações
                    </a>
                  </div>

                  <div className="py-1 border-t border-gray-200">
                    <button className="flex items-center w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-100">
                      <LogOut className="w-4 h-4 mr-3" />
                      Sair
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Click outside handlers */}
      {(showUserMenu || showNotifications) && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => {
            setShowUserMenu(false);
            setShowNotifications(false);
          }}
        />
      )}
    </header>
  );
};

export default Header;
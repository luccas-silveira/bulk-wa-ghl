import React from 'react';
import {
  BarChart3,
  MessageSquare,
  Users,
  Settings,
  Menu,
  ChevronLeft,
  ChevronRight,
  Home
} from 'lucide-react';
import Button from '../ui/Button';

export interface SidebarProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  className?: string;
  navigationItems?: NavigationItem[];
}

export interface NavigationItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  href?: string;
  onClick?: () => void;
  badge?: string | number;
  active?: boolean;
  children?: NavigationItem[];
}

const defaultNavigationItems: NavigationItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: <Home />,
    href: '/',
    active: true,
  },
  {
    id: 'campaigns',
    label: 'Criar Disparo',
    icon: <MessageSquare />,
    href: '/campaigns',
  },
  {
    id: 'analytics',
    label: 'Analytics',
    icon: <BarChart3 />,
    href: '/analytics',
  },
  {
    id: 'contacts',
    label: 'Contatos',
    icon: <Users />,
    href: '/contacts',
  },
  {
    id: 'settings',
    label: 'Configurações',
    icon: <Settings />,
    href: '/settings',
  },
];

const Sidebar: React.FC<SidebarProps> = ({
  collapsed = false,
  onToggleCollapse,
  className,
  navigationItems = defaultNavigationItems,
}) => {
  const handleItemClick = (item: NavigationItem) => {
    if (item.onClick) {
      item.onClick();
    }
  };

  const sidebarClasses = [
    'fixed left-0 top-0 h-full bg-white border-r border-gray-200 z-40',
    'transition-all duration-300 ease-in-out',
    'flex flex-col',
    collapsed ? 'w-16' : 'w-64',
    className
  ].filter(Boolean).join(' ');

  return (
    <>
      {/* Mobile Overlay */}
      {!collapsed && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-30 lg:hidden" />
      )}

      <div className={sidebarClasses}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          {!collapsed && (
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
                <MessageSquare className="w-5 h-5 text-white" />
              </div>
              <span className="font-semibold text-gray-900 text-lg">
                WPP Manager
              </span>
            </div>
          )}

          {collapsed && (
            <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center mx-auto">
              <MessageSquare className="w-5 h-5 text-white" />
            </div>
          )}

          {onToggleCollapse && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggleCollapse}
              className="p-1.5 hover:bg-gray-100"
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {collapsed ? (
                <ChevronRight className="w-4 h-4" />
              ) : (
                <ChevronLeft className="w-4 h-4" />
              )}
            </Button>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto overflow-x-hidden min-h-0">
          {navigationItems.map((item) => (
            <SidebarItem
              key={item.id}
              item={item}
              collapsed={collapsed}
              active={item.active || false}
              onClick={() => handleItemClick(item)}
            />
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200">
          {!collapsed ? (
            <div className="text-xs text-gray-500 text-center">
              v0.1.0 - WAHA Integration
            </div>
          ) : (
            <div className="w-2 h-2 bg-success-400 rounded-full mx-auto" />
          )}
        </div>
      </div>
    </>
  );
};

// Sidebar Item Component
interface SidebarItemProps {
  item: NavigationItem;
  collapsed: boolean;
  active: boolean;
  onClick: () => void;
  depth?: number;
}

const SidebarItem: React.FC<SidebarItemProps> = ({
  item,
  collapsed,
  active,
  onClick,
  depth = 0,
}) => {
  const [expanded, setExpanded] = React.useState(false);
  const hasChildren = item.children && item.children.length > 0;

  const handleClick = () => {
    if (hasChildren && !collapsed) {
      setExpanded(!expanded);
    } else {
      onClick();
    }
  };

  const itemClasses = [
    'flex items-center w-full text-left rounded-lg transition-colors duration-200',
    'hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500',
    collapsed ? 'p-3 justify-center' : 'p-3',
    active ? 'bg-primary-50 text-primary-700 border-r-2 border-primary-500' : 'text-gray-700',
    depth > 0 ? 'ml-4' : '',
  ].filter(Boolean).join(' ');

  if (collapsed) {
    return (
      <div className="relative group">
        <button className={itemClasses} onClick={handleClick} aria-label={item.label}>
          {React.cloneElement(item.icon as React.ReactElement, {
            className: 'w-5 h-5'
          })}
          {item.badge && (
            <span className="absolute -top-1 -right-1 w-5 h-5 bg-error-500 text-white text-xs rounded-full flex items-center justify-center">
              {typeof item.badge === 'number' && item.badge > 99 ? '99+' : item.badge}
            </span>
          )}
        </button>

        {/* Tooltip for collapsed state */}
        <div className="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-sm rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-50">
          {item.label}
        </div>
      </div>
    );
  }

  return (
    <div>
      <button className={itemClasses} onClick={handleClick}>
        <div className="flex items-center flex-1 min-w-0">
          {React.cloneElement(item.icon as React.ReactElement, {
            className: 'w-5 h-5 flex-shrink-0'
          })}
          <span className="ml-3 font-medium truncate">
            {item.label}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {item.badge && (
            <span className="px-2 py-0.5 bg-error-500 text-white text-xs rounded-full">
              {typeof item.badge === 'number' && item.badge > 99 ? '99+' : item.badge}
            </span>
          )}

          {hasChildren && (
            <ChevronRight
              className={`w-4 h-4 transition-transform duration-200 ${
                expanded ? 'rotate-90' : ''
              }`}
            />
          )}
        </div>
      </button>

      {/* Children */}
      {hasChildren && expanded && !collapsed && (
        <div className="mt-1 space-y-1">
          {item.children!.map((child) => (
            <SidebarItem
              key={child.id}
              item={child}
              collapsed={collapsed}
              active={active}
              onClick={onClick}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default Sidebar;
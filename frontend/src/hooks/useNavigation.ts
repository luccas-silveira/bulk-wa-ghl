import { useState, useEffect, useMemo } from 'react';

export interface NavigationState {
  activeRoute: string;
  sidebarCollapsed: boolean;
  isMobile: boolean;
  breadcrumbs: BreadcrumbItem[];
}

export interface BreadcrumbItem {
  label: string;
  href?: string;
  current?: boolean;
}

export interface UseNavigationReturn extends NavigationState {
  setActiveRoute: (route: string) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setBreadcrumbs: (breadcrumbs: BreadcrumbItem[]) => void;
}

// Route configuration
const ROUTES_CONFIG = {
  '/': {
    label: 'Dashboard',
    breadcrumbs: [{ label: 'Dashboard', current: true }]
  },
  '/campaigns': {
    label: 'Criar Disparo',
    breadcrumbs: [
      { label: 'Dashboard', href: '/' },
      { label: 'Criar Disparo', current: true }
    ]
  },
  '/analytics': {
    label: 'Analytics',
    breadcrumbs: [
      { label: 'Dashboard', href: '/' },
      { label: 'Analytics', current: true }
    ]
  },
  '/contacts': {
    label: 'Contatos',
    breadcrumbs: [
      { label: 'Dashboard', href: '/' },
      { label: 'Contatos', current: true }
    ]
  },
  '/settings': {
    label: 'Configurações',
    breadcrumbs: [
      { label: 'Dashboard', href: '/' },
      { label: 'Configurações', current: true }
    ]
  }
};

export const useNavigation = (initialRoute: string = '/'): UseNavigationReturn => {
  const [activeRoute, setActiveRoute] = useState(initialRoute);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [customBreadcrumbs, setCustomBreadcrumbs] = useState<BreadcrumbItem[] | null>(null);

  // Handle responsive behavior
  useEffect(() => {
    const checkMobile = () => {
      const isMobileSize = window.innerWidth < 1024;
      setIsMobile(isMobileSize);

      // Auto-collapse sidebar on mobile
      if (isMobileSize && !sidebarCollapsed) {
        setSidebarCollapsed(true);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [sidebarCollapsed]);

  // Generate breadcrumbs based on current route
  const breadcrumbs = useMemo(() => {
    if (customBreadcrumbs) {
      return customBreadcrumbs;
    }

    const routeConfig = ROUTES_CONFIG[activeRoute as keyof typeof ROUTES_CONFIG];
    return routeConfig?.breadcrumbs || [{ label: 'Dashboard', current: true }];
  }, [activeRoute, customBreadcrumbs]);

  // Handle route changes
  const handleSetActiveRoute = (route: string) => {
    setActiveRoute(route);
    setCustomBreadcrumbs(null); // Reset custom breadcrumbs when route changes
  };

  // Toggle sidebar
  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  // Set custom breadcrumbs (useful for dynamic pages)
  const setBreadcrumbs = (breadcrumbs: BreadcrumbItem[]) => {
    setCustomBreadcrumbs(breadcrumbs);
  };

  return {
    activeRoute,
    sidebarCollapsed,
    isMobile,
    breadcrumbs,
    setActiveRoute: handleSetActiveRoute,
    toggleSidebar,
    setSidebarCollapsed,
    setBreadcrumbs,
  };
};

// Hook for managing page title based on route
export const usePageTitle = (route: string, customTitle?: string) => {
  useEffect(() => {
    const routeConfig = ROUTES_CONFIG[route as keyof typeof ROUTES_CONFIG];
    const title = customTitle || routeConfig?.label || 'Dashboard';
    document.title = `${title} - WhatsApp Campaign Management`;
  }, [route, customTitle]);
};

// Hook for route-based component visibility
export const useRouteVisibility = (targetRoute: string, currentRoute: string) => {
  return useMemo(() => {
    if (targetRoute === currentRoute) return 'visible';
    if (targetRoute.startsWith(currentRoute) && currentRoute !== '/') return 'nested';
    return 'hidden';
  }, [targetRoute, currentRoute]);
};
import React from 'react';
import {
  MessageSquare,
  Plus,
  Users,
  BarChart3,
  Settings,
  Zap,
  FileText,
  Download,
  Upload,
  ArrowRight
} from 'lucide-react';
import Button from '../ui/Button';
import Card from '../ui/Card';

export interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  action: () => void;
  variant?: 'primary' | 'secondary' | 'success' | 'warning';
  disabled?: boolean;
  badge?: string | number;
}

export interface QuickActionsProps {
  onNavigate: (route: string) => void;
  className?: string;
}

const QuickActions: React.FC<QuickActionsProps> = ({
  onNavigate,
  className,
}) => {
  const primaryActions: QuickAction[] = [
    {
      id: 'create-campaign',
      title: 'Nova Campanha',
      description: 'Criar um novo disparo em massa',
      icon: <Plus className="w-5 h-5" />,
      action: () => onNavigate('/campaigns'),
      variant: 'primary',
    },
    {
      id: 'import-contacts',
      title: 'Importar Contatos',
      description: 'Carregar lista de contatos via CSV',
      icon: <Upload className="w-5 h-5" />,
      action: () => onNavigate('/contacts'),
      variant: 'secondary',
    },
    {
      id: 'view-analytics',
      title: 'Ver Analytics',
      description: 'Relatórios de performance',
      icon: <BarChart3 className="w-5 h-5" />,
      action: () => onNavigate('/analytics'),
      variant: 'secondary',
    },
  ];

  const quickShortcuts: QuickAction[] = [
    {
      id: 'templates',
      title: 'Templates',
      description: 'Gerenciar modelos de mensagem',
      icon: <FileText className="w-4 h-4" />,
      action: () => console.log('Templates'),
    },
    {
      id: 'export-data',
      title: 'Exportar Dados',
      description: 'Download de relatórios',
      icon: <Download className="w-4 h-4" />,
      action: () => console.log('Export'),
    },
    {
      id: 'waha-sessions',
      title: 'Sessões WAHA',
      description: 'Gerenciar conexões WhatsApp',
      icon: <MessageSquare className="w-4 h-4" />,
      action: () => onNavigate('/settings'),
    },
    {
      id: 'settings',
      title: 'Configurações',
      description: 'Preferências do sistema',
      icon: <Settings className="w-4 h-4" />,
      action: () => onNavigate('/settings'),
    },
  ];

  const getVariantClasses = (variant: QuickAction['variant']) => {
    switch (variant) {
      case 'primary':
        return 'bg-primary-50 border-primary-200 hover:bg-primary-100 hover:border-primary-300';
      case 'success':
        return 'bg-success-50 border-success-200 hover:bg-success-100 hover:border-success-300';
      case 'warning':
        return 'bg-warning-50 border-warning-200 hover:bg-warning-100 hover:border-warning-300';
      case 'secondary':
      default:
        return 'bg-gray-50 border-gray-200 hover:bg-gray-100 hover:border-gray-300';
    }
  };

  const getIconClasses = (variant: QuickAction['variant']) => {
    switch (variant) {
      case 'primary':
        return 'text-primary-600 bg-primary-100';
      case 'success':
        return 'text-success-600 bg-success-100';
      case 'warning':
        return 'text-warning-600 bg-warning-100';
      case 'secondary':
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Primary Actions */}
      <Card>
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Ações Rápidas
            </h3>
            <Zap className="w-5 h-5 text-primary-600" />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {primaryActions.map((action) => (
              <button
                key={action.id}
                onClick={action.action}
                disabled={action.disabled}
                className={`
                  relative p-4 rounded-lg border-2 transition-all duration-200
                  ${getVariantClasses(action.variant)}
                  ${action.disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                  focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
                `}
              >
                <div className="flex items-start space-x-3">
                  <div className={`
                    p-2 rounded-lg ${getIconClasses(action.variant)}
                  `}>
                    {action.icon}
                  </div>
                  <div className="flex-1 text-left">
                    <h4 className="font-medium text-gray-900 mb-1">
                      {action.title}
                    </h4>
                    <p className="text-sm text-gray-600">
                      {action.description}
                    </p>
                  </div>
                  {action.badge && (
                    <div className="absolute -top-2 -right-2 bg-error-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                      {action.badge}
                    </div>
                  )}
                </div>
                <ArrowRight className="w-4 h-4 text-gray-400 absolute bottom-3 right-3" />
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Quick Shortcuts */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Atalhos Rápidos
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {quickShortcuts.map((shortcut) => (
              <button
                key={shortcut.id}
                onClick={shortcut.action}
                disabled={shortcut.disabled}
                className={`
                  flex items-center space-x-3 p-3 rounded-lg border transition-all duration-200
                  ${getVariantClasses('secondary')}
                  ${shortcut.disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                  focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
                `}
              >
                <div className={`
                  p-1.5 rounded ${getIconClasses('secondary')}
                `}>
                  {shortcut.icon}
                </div>
                <div className="flex-1 text-left">
                  <h4 className="font-medium text-gray-900 text-sm">
                    {shortcut.title}
                  </h4>
                  <p className="text-xs text-gray-600">
                    {shortcut.description}
                  </p>
                </div>
                <ArrowRight className="w-3 h-3 text-gray-400" />
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Recent Campaign Quick Start */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Início Rápido
          </h3>

          <div className="bg-gradient-to-r from-primary-50 to-primary-100 rounded-lg p-4 border border-primary-200">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-gray-900 mb-1">
                  Primeira Campanha
                </h4>
                <p className="text-sm text-gray-600">
                  Configure sua primeira campanha em poucos cliques
                </p>
              </div>
              <Button
                variant="primary"
                size="sm"
                onClick={() => onNavigate('/campaigns')}
                className="flex-shrink-0"
              >
                Começar
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <span className="text-sm font-semibold text-primary-600">1</span>
              </div>
              <p className="text-xs text-gray-600">Conectar WAHA</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <span className="text-sm font-semibold text-primary-600">2</span>
              </div>
              <p className="text-xs text-gray-600">Importar Contatos</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <span className="text-sm font-semibold text-primary-600">3</span>
              </div>
              <p className="text-xs text-gray-600">Criar Campanha</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default QuickActions;
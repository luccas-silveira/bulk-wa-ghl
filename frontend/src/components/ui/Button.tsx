import React from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({
    className,
    variant = 'primary',
    size = 'md',
    loading = false,
    icon,
    iconPosition = 'left',
    fullWidth = false,
    children,
    disabled,
    ...props
  }, ref) => {
    const baseClasses = [
      'inline-flex items-center justify-center rounded-md font-medium transition-colors duration-200',
      'focus:outline-none focus:ring-2 focus:ring-offset-2',
      'disabled:opacity-50 disabled:pointer-events-none',
      fullWidth ? 'w-full' : '',
    ].filter(Boolean).join(' ');

    const variants = {
      primary: [
        'bg-primary-500 text-white hover:bg-primary-600',
        'focus:ring-primary-500',
        'shadow-sm border border-transparent'
      ].join(' '),
      secondary: [
        'bg-white text-gray-700 hover:bg-gray-50',
        'focus:ring-primary-500',
        'shadow-sm border border-gray-300'
      ].join(' '),
      ghost: [
        'text-gray-700 hover:text-gray-900 hover:bg-gray-100',
        'focus:ring-primary-500',
        'border border-transparent'
      ].join(' '),
      danger: [
        'bg-error-500 text-white hover:bg-error-600',
        'focus:ring-error-500',
        'shadow-sm border border-transparent'
      ].join(' '),
    };

    const sizes = {
      sm: 'text-sm px-3 py-2 gap-1.5',
      md: 'text-sm px-4 py-2 gap-2',
      lg: 'text-base px-6 py-3 gap-2.5',
    };

    const iconSizes = {
      sm: 'h-4 w-4',
      md: 'h-4 w-4',
      lg: 'h-5 w-5',
    };

    const combinedClassName = [
      baseClasses,
      variants[variant],
      sizes[size],
      className
    ].filter(Boolean).join(' ');

    const renderIcon = () => {
      if (loading) {
        return <Loader2 className={`${iconSizes[size]} animate-spin`} />;
      }
      if (React.isValidElement(icon)) {
        return React.cloneElement(icon as React.ReactElement, {
          className: iconSizes[size]
        });
      }
      return null;
    };

    const iconElement = renderIcon();

    if (process.env.NODE_ENV !== 'production' && !children && !props['aria-label']) {
      console.warn('[Button] Botão sem texto visível e sem aria-label. Adicione aria-label para acessibilidade.');
    }

    return (
      <button
        className={combinedClassName}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {iconElement && iconPosition === 'left' && iconElement}
        {children}
        {iconElement && iconPosition === 'right' && iconElement}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
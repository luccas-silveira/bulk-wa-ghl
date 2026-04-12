import React from 'react';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'warning' | 'error' | 'info' | 'gray' | 'primary';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
  removable?: boolean;
  onRemove?: () => void;
}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({
    className,
    variant = 'gray',
    size = 'md',
    dot = false,
    removable = false,
    onRemove,
    children,
    ...props
  }, ref) => {
    const variants = {
      success: 'bg-success-100 text-success-800',
      warning: 'bg-warning-100 text-warning-800',
      error: 'bg-error-100 text-error-800',
      info: 'bg-blue-100 text-blue-800',
      gray: 'bg-gray-100 text-gray-800',
      primary: 'bg-primary-100 text-primary-800',
    };

    const sizes = {
      sm: dot ? 'text-xs px-1.5 py-0.5' : 'text-xs px-2 py-0.5',
      md: dot ? 'text-xs px-2 py-1' : 'text-xs px-2.5 py-0.5',
      lg: dot ? 'text-sm px-2.5 py-1' : 'text-sm px-3 py-1',
    };

    const baseClasses = [
      'inline-flex items-center rounded-full font-medium',
      variants[variant],
      sizes[size],
      className
    ].filter(Boolean).join(' ');

    return (
      <span className={baseClasses} ref={ref} {...props}>
        {dot && (
          <span
            className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
              variant === 'success' ? 'bg-success-400' :
              variant === 'warning' ? 'bg-warning-400' :
              variant === 'error' ? 'bg-error-400' :
              variant === 'info' ? 'bg-blue-400' :
              variant === 'primary' ? 'bg-primary-400' :
              'bg-gray-400'
            }`}
          />
        )}
        {children}
        {removable && onRemove && (
          <button
            type="button"
            aria-label="Remover"
            onClick={onRemove}
            className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full hover:bg-black hover:bg-opacity-10 focus:outline-none"
          >
            <svg aria-hidden="true" className="w-3 h-3" viewBox="0 0 12 12" fill="currentColor">
              <path d="M6 5.293l2.146-2.147a.5.5 0 01.708.708L6.707 6l2.147 2.146a.5.5 0 01-.708.708L6 6.707 3.854 8.854a.5.5 0 01-.708-.708L5.293 6 3.146 3.854a.5.5 0 01.708-.708L6 5.293z" />
            </svg>
          </button>
        )}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

export default Badge;
import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'outlined' | 'ghost';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hover?: boolean;
  clickable?: boolean;
}

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  border?: boolean;
}

export interface CardBodyProps extends React.HTMLAttributes<HTMLDivElement> {
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  border?: boolean;
  align?: 'left' | 'center' | 'right' | 'between';
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({
    className,
    variant = 'default',
    padding = 'md',
    hover = false,
    clickable = false,
    children,
    onClick,
    onKeyDown,
    ...props
  }, ref) => {
    const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (clickable && (e.key === 'Enter' || e.key === ' ')) {
        e.preventDefault();
        onClick?.(e as unknown as React.MouseEvent<HTMLDivElement>);
      }
      onKeyDown?.(e);
    };

    const baseClasses = [
      'rounded-lg overflow-hidden transition-all duration-200',
      clickable ? 'cursor-pointer' : '',
      hover ? 'hover:shadow-ghl-lg hover:-translate-y-0.5' : '',
    ].filter(Boolean).join(' ');

    const variants = {
      default: 'bg-white border border-gray-200 shadow-ghl',
      elevated: 'bg-white shadow-ghl-lg border border-gray-100',
      outlined: 'bg-white border-2 border-gray-300 shadow-none',
      ghost: 'bg-transparent border-none shadow-none',
    };

    const paddings = {
      none: '',
      sm: 'p-4',
      md: 'p-6',
      lg: 'p-8',
    };

    const combinedClassName = [
      baseClasses,
      variants[variant],
      paddings[padding],
      className
    ].filter(Boolean).join(' ');

    return (
      <div
        className={combinedClassName}
        ref={ref}
        role={clickable ? 'button' : undefined}
        tabIndex={clickable ? 0 : undefined}
        onClick={onClick}
        onKeyDown={clickable ? handleKeyDown : onKeyDown}
        {...props}
      >
        {children}
      </div>
    );
  }
);

const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, border = true, children, ...props }, ref) => {
    const combinedClassName = [
      'px-6 py-4',
      border ? 'border-b border-gray-200 bg-gray-50' : '',
      className
    ].filter(Boolean).join(' ');

    return (
      <div className={combinedClassName} ref={ref} {...props}>
        {children}
      </div>
    );
  }
);

const CardBody = React.forwardRef<HTMLDivElement, CardBodyProps>(
  ({ className, padding = 'md', children, ...props }, ref) => {
    const paddings = {
      none: '',
      sm: 'p-4',
      md: 'p-6',
      lg: 'p-8',
    };

    const combinedClassName = [
      paddings[padding],
      className
    ].filter(Boolean).join(' ');

    return (
      <div className={combinedClassName} ref={ref} {...props}>
        {children}
      </div>
    );
  }
);

const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({
    className,
    border = true,
    align = 'left',
    children,
    ...props
  }, ref) => {
    const alignments = {
      left: 'justify-start',
      center: 'justify-center',
      right: 'justify-end',
      between: 'justify-between',
    };

    const combinedClassName = [
      'px-6 py-4 flex items-center',
      alignments[align],
      border ? 'border-t border-gray-200 bg-gray-50' : '',
      className
    ].filter(Boolean).join(' ');

    return (
      <div className={combinedClassName} ref={ref} {...props}>
        {children}
      </div>
    );
  }
);

// Metric Card - specialized card for dashboard metrics
export interface MetricCardProps extends CardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: number;
    isPositive: boolean;
    label?: string;
  };
  icon?: React.ReactNode;
  loading?: boolean;
}

const MetricCard = React.forwardRef<HTMLDivElement, MetricCardProps>(
  ({
    title,
    value,
    subtitle,
    trend,
    icon,
    loading = false,
    className,
    ...props
  }, ref) => {
    if (loading) {
      return (
        <Card className={className} ref={ref} {...props}>
          <CardBody>
            <div className="animate-pulse">
              <div className="flex items-center justify-between mb-4">
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                <div className="h-5 w-5 bg-gray-200 rounded"></div>
              </div>
              <div className="h-8 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-gray-200 rounded w-1/3"></div>
            </div>
          </CardBody>
        </Card>
      );
    }

    return (
      <Card className={className} ref={ref} {...props}>
        <CardBody>
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">{title}</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {typeof value === 'number' ? value.toLocaleString() : value}
              </p>
              {subtitle && (
                <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
              )}
              {trend && (
                <div className="flex items-center mt-2">
                  <span
                    className={`text-xs font-medium ${
                      trend.isPositive ? 'text-success-600' : 'text-error-600'
                    }`}
                  >
                    {trend.isPositive ? '+' : ''}{trend.value}%
                  </span>
                  {trend.label && (
                    <span className="text-xs text-gray-500 ml-1">
                      {trend.label}
                    </span>
                  )}
                </div>
              )}
            </div>
            {React.isValidElement(icon) && (
              <div className="flex-shrink-0">
                <div className="p-3 bg-primary-50 rounded-lg">
                  {React.cloneElement(icon as React.ReactElement, {
                    className: 'h-6 w-6 text-primary-600'
                  })}
                </div>
              </div>
            )}
          </div>
        </CardBody>
      </Card>
    );
  }
);

Card.displayName = 'Card';
CardHeader.displayName = 'CardHeader';
CardBody.displayName = 'CardBody';
CardFooter.displayName = 'CardFooter';
MetricCard.displayName = 'MetricCard';

export default Card;
export { CardHeader, CardBody, CardFooter, MetricCard };
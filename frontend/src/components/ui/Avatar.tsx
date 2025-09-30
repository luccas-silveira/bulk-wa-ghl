import React from 'react';
import { User } from 'lucide-react';

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string;
  alt?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  fallback?: string;
  status?: 'online' | 'offline' | 'away' | 'busy';
  showStatus?: boolean;
  rounded?: boolean;
}

const Avatar = React.forwardRef<HTMLDivElement, AvatarProps>(
  ({
    className,
    src,
    alt,
    size = 'md',
    fallback,
    status,
    showStatus = false,
    rounded = true,
    ...props
  }, ref) => {
    const [imageError, setImageError] = React.useState(false);
    const [imageLoaded, setImageLoaded] = React.useState(false);

    const sizes = {
      xs: 'w-6 h-6 text-xs',
      sm: 'w-8 h-8 text-sm',
      md: 'w-10 h-10 text-base',
      lg: 'w-12 h-12 text-lg',
      xl: 'w-16 h-16 text-xl',
      '2xl': 'w-20 h-20 text-2xl',
    };

    const statusSizes = {
      xs: 'w-2 h-2',
      sm: 'w-2.5 h-2.5',
      md: 'w-3 h-3',
      lg: 'w-3.5 h-3.5',
      xl: 'w-4 h-4',
      '2xl': 'w-5 h-5',
    };

    const statusColors = {
      online: 'bg-success-400',
      offline: 'bg-gray-400',
      away: 'bg-warning-400',
      busy: 'bg-error-400',
    };

    const baseClasses = [
      'relative inline-flex items-center justify-center overflow-hidden bg-gray-100',
      rounded ? 'rounded-full' : 'rounded-lg',
      sizes[size],
      className
    ].filter(Boolean).join(' ');

    const handleImageError = () => {
      setImageError(true);
    };

    const handleImageLoad = () => {
      setImageLoaded(true);
    };

    const renderFallback = () => {
      if (fallback) {
        return (
          <span className="font-medium text-gray-600 uppercase">
            {fallback.charAt(0)}
          </span>
        );
      }
      return <User className="w-1/2 h-1/2 text-gray-400" />;
    };

    const shouldShowImage = src && !imageError;

    return (
      <div className={baseClasses} ref={ref} {...props}>
        {shouldShowImage && (
          <img
            src={src}
            alt={alt || 'Avatar'}
            className={`w-full h-full object-cover transition-opacity duration-200 ${
              imageLoaded ? 'opacity-100' : 'opacity-0'
            }`}
            onError={handleImageError}
            onLoad={handleImageLoad}
          />
        )}
        {(!shouldShowImage || !imageLoaded) && (
          <div className="absolute inset-0 flex items-center justify-center">
            {renderFallback()}
          </div>
        )}

        {showStatus && status && (
          <span
            className={`absolute bottom-0 right-0 block rounded-full ring-2 ring-white ${
              statusSizes[size]
            } ${statusColors[status]}`}
          />
        )}
      </div>
    );
  }
);

// Avatar Group Component
export interface AvatarGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  max?: number;
  size?: AvatarProps['size'];
  spacing?: 'tight' | 'normal' | 'loose';
}

const AvatarGroup = React.forwardRef<HTMLDivElement, AvatarGroupProps>(
  ({
    className,
    max = 4,
    size = 'md',
    spacing = 'normal',
    children,
    ...props
  }, ref) => {
    const childrenArray = React.Children.toArray(children);
    const visibleChildren = max ? childrenArray.slice(0, max) : childrenArray;
    const hiddenCount = max ? Math.max(0, childrenArray.length - max) : 0;

    const spacings = {
      tight: '-space-x-1',
      normal: '-space-x-2',
      loose: '-space-x-1',
    };

    const baseClasses = [
      'flex items-center',
      spacings[spacing],
      className
    ].filter(Boolean).join(' ');

    return (
      <div className={baseClasses} ref={ref} {...props}>
        {visibleChildren.map((child, index) => (
          <div key={index} className="ring-2 ring-white">
            {React.cloneElement(child as React.ReactElement, {
              size,
            })}
          </div>
        ))}
        {hiddenCount > 0 && (
          <div className="ring-2 ring-white">
            <Avatar
              size={size}
              fallback={`+${hiddenCount}`}
              className="bg-gray-200 text-gray-600"
            />
          </div>
        )}
      </div>
    );
  }
);

Avatar.displayName = 'Avatar';
AvatarGroup.displayName = 'AvatarGroup';

export default Avatar;
export { AvatarGroup };
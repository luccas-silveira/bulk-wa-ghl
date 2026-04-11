import React from 'react';
import { Eye, EyeOff, Search, AlertCircle } from 'lucide-react';

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'filled';
  fullWidth?: boolean;
}

export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  label?: string;
  error?: string;
  helperText?: string;
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
  placeholder?: string;
}

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
  resize?: 'none' | 'vertical' | 'horizontal' | 'both';
  fullWidth?: boolean;
}

// Input Component
const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({
    className,
    type = 'text',
    label,
    error,
    helperText,
    leftIcon,
    rightIcon,
    size = 'md',
    variant = 'default',
    fullWidth = false,
    disabled,
    id: idProp,
    ...props
  }, ref) => {
    const [showPassword, setShowPassword] = React.useState(false);
    const generatedId = React.useId();
    // Se o consumidor passar id explicitamente via props, usar o dele; caso contrário, usar o gerado
    const id = idProp ?? generatedId;
    const isPassword = type === 'password';
    const inputType = isPassword && showPassword ? 'text' : type;

    const sizes = {
      sm: 'text-sm px-3 py-2',
      md: 'text-sm px-3 py-2.5',
      lg: 'text-base px-4 py-3',
    };

    const variants = {
      default: [
        'bg-white border border-gray-300',
        'focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
        error ? 'border-error-300 focus:border-error-500 focus:ring-error-500' : ''
      ].filter(Boolean).join(' '),
      filled: [
        'bg-gray-50 border border-transparent',
        'focus:bg-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
        error ? 'bg-error-50 focus:border-error-500 focus:ring-error-500' : ''
      ].filter(Boolean).join(' '),
    };

    const baseInputClasses = [
      'w-full rounded-md shadow-sm placeholder-gray-400',
      'focus:outline-none transition-colors duration-200',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50',
      sizes[size],
      variants[variant],
      leftIcon ? 'pl-10' : '',
      rightIcon || isPassword ? 'pr-10' : '',
      className
    ].filter(Boolean).join(' ');

    return (
      <div className={fullWidth ? 'w-full' : ''}>
        {label && (
          <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              {React.cloneElement(leftIcon as React.ReactElement, {
                className: 'h-5 w-5 text-gray-400'
              })}
            </div>
          )}
          <input
            id={id}
            type={inputType}
            className={baseInputClasses}
            ref={ref}
            disabled={disabled}
            {...props}
          />
          {(rightIcon || isPassword) && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
              {isPassword ? (
                <button
                  type="button"
                  className="text-gray-400 hover:text-gray-600 focus:outline-none"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              ) : rightIcon ? (
                React.cloneElement(rightIcon as React.ReactElement, {
                  className: 'h-5 w-5 text-gray-400'
                })
              ) : null}
            </div>
          )}
        </div>
        {(error || helperText) && (
          <div className="mt-1">
            {error && (
              <p className="text-sm text-error-600 flex items-center gap-1">
                <AlertCircle className="h-4 w-4" />
                {error}
              </p>
            )}
            {helperText && !error && (
              <p className="text-sm text-gray-500">{helperText}</p>
            )}
          </div>
        )}
      </div>
    );
  }
);

// Select Component
const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({
    className,
    label,
    error,
    helperText,
    size = 'md',
    fullWidth = false,
    placeholder,
    children,
    disabled,
    ...props
  }, ref) => {
    const sizes = {
      sm: 'text-sm px-3 py-2',
      md: 'text-sm px-3 py-2.5',
      lg: 'text-base px-4 py-3',
    };

    const baseSelectClasses = [
      'w-full bg-white border border-gray-300 rounded-md shadow-sm',
      'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
      'transition-colors duration-200',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50',
      error ? 'border-error-300 focus:border-error-500 focus:ring-error-500' : '',
      sizes[size],
      className
    ].filter(Boolean).join(' ');

    return (
      <div className={fullWidth ? 'w-full' : ''}>
        {label && (
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {label}
          </label>
        )}
        <select
          className={baseSelectClasses}
          ref={ref}
          disabled={disabled}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {children}
        </select>
        {(error || helperText) && (
          <div className="mt-1">
            {error && (
              <p className="text-sm text-error-600 flex items-center gap-1">
                <AlertCircle className="h-4 w-4" />
                {error}
              </p>
            )}
            {helperText && !error && (
              <p className="text-sm text-gray-500">{helperText}</p>
            )}
          </div>
        )}
      </div>
    );
  }
);

// Textarea Component
const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({
    className,
    label,
    error,
    helperText,
    resize = 'vertical',
    fullWidth = false,
    disabled,
    ...props
  }, ref) => {
    const resizeClasses = {
      none: 'resize-none',
      vertical: 'resize-y',
      horizontal: 'resize-x',
      both: 'resize',
    };

    const baseTextareaClasses = [
      'w-full bg-white border border-gray-300 rounded-md shadow-sm',
      'px-3 py-2.5 text-sm placeholder-gray-400',
      'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
      'transition-colors duration-200',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50',
      error ? 'border-error-300 focus:border-error-500 focus:ring-error-500' : '',
      resizeClasses[resize],
      className
    ].filter(Boolean).join(' ');

    return (
      <div className={fullWidth ? 'w-full' : ''}>
        {label && (
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {label}
          </label>
        )}
        <textarea
          className={baseTextareaClasses}
          ref={ref}
          disabled={disabled}
          {...props}
        />
        {(error || helperText) && (
          <div className="mt-1">
            {error && (
              <p className="text-sm text-error-600 flex items-center gap-1">
                <AlertCircle className="h-4 w-4" />
                {error}
              </p>
            )}
            {helperText && !error && (
              <p className="text-sm text-gray-500">{helperText}</p>
            )}
          </div>
        )}
      </div>
    );
  }
);

// Search Input - specialized input for search functionality
export interface SearchInputProps extends Omit<InputProps, 'leftIcon' | 'type'> {
  onClear?: () => void;
  showClearButton?: boolean;
}

const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  ({
    onClear,
    showClearButton = true,
    value,
    ...props
  }, ref) => {
    const handleClear = () => {
      if (onClear) {
        onClear();
      }
    };

    return (
      <Input
        ref={ref}
        type="text"
        leftIcon={<Search />}
        rightIcon={
          showClearButton && value ? (
            <button
              type="button"
              onClick={handleClear}
              className="text-gray-400 hover:text-gray-600 focus:outline-none"
            >
              ×
            </button>
          ) : undefined
        }
        value={value}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';
Select.displayName = 'Select';
Textarea.displayName = 'Textarea';
SearchInput.displayName = 'SearchInput';

export default Input;
export { Select, Textarea, SearchInput };
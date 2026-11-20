import React, { forwardRef } from 'react';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'subtle';
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'icon';
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading = false, children, disabled, ...props }, ref) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium transition-all duration-150 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50 disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98] select-none cursor-pointer';

    const variants = {
      primary:
        'bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white shadow-[0_1px_8px_var(--accent-subtle)] hover:shadow-[0_2px_12px_var(--accent-glow)]',
      secondary:
        'bg-[#1B202C] hover:bg-[#252B36] text-[#F5F7FA] border border-[#252B36] hover:border-[#323A4A]',
      outline:
        'bg-transparent hover:bg-[#151922] text-[#F5F7FA] border border-[#252B36] hover:border-[#374151]',
      ghost:
        'bg-transparent hover:bg-[#1B202C] text-[#929AAA] hover:text-[#F5F7FA]',
      danger:
        'bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 hover:border-red-500/40',
      subtle:
        'bg-[var(--accent-subtle)] text-[var(--accent)] hover:opacity-90 border border-[var(--accent-subtle)]',
    };

    const sizes = {
      xs: 'h-7 px-2.5 text-xs gap-1.5 rounded-md',
      sm: 'h-8 px-3 text-xs gap-1.5 rounded-md',
      md: 'h-9 px-4 text-sm gap-2',
      lg: 'h-11 px-5 text-base gap-2.5 rounded-xl',
      icon: 'h-9 w-9 p-0',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading && <Loader2 className="w-4 h-4 animate-spin shrink-0" />}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

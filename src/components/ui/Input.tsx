import React, { forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', label, error, icon, ...props }, ref) => {
    return (
      <div className="w-full space-y-1.5">
        {label && <label className="block text-xs font-medium text-[#929AAA]">{label}</label>}
        <div className="relative flex items-center">
          {icon && <div className="absolute left-3 text-[#929AAA] pointer-events-none">{icon}</div>}
          <input
            ref={ref}
            type={type}
            className={cn(
              'w-full h-9 bg-[#10131A] border border-[#252B36] rounded-lg px-3 py-1.5 text-sm text-[#F5F7FA] placeholder:text-[#929AAA]/50 focus:outline-none focus:border-[#8B7CFF] focus:ring-1 focus:ring-[#8B7CFF] transition-all disabled:opacity-50 disabled:cursor-not-allowed',
              icon && 'pl-9',
              error && 'border-red-500 focus:border-red-500 focus:ring-red-500/20',
              className
            )}
            {...props}
          />
        </div>
        {error && <p className="text-xs text-red-400 font-medium">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, ...props }, ref) => {
    return (
      <div className="w-full space-y-1.5">
        {label && <label className="block text-xs font-medium text-[#929AAA]">{label}</label>}
        <textarea
          ref={ref}
          className={cn(
            'w-full min-h-[90px] bg-[#10131A] border border-[#252B36] rounded-lg p-3 text-sm text-[#F5F7FA] placeholder:text-[#929AAA]/50 focus:outline-none focus:border-[#8B7CFF] focus:ring-1 focus:ring-[#8B7CFF] transition-all disabled:opacity-50 disabled:cursor-not-allowed resize-y',
            error && 'border-red-500 focus:border-red-500',
            className
          )}
          {...props}
        />
        {error && <p className="text-xs text-red-400 font-medium">{error}</p>}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

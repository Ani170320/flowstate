import React, { forwardRef } from 'react';
import { cn } from '@/lib/utils';
import { ChevronDown } from 'lucide-react';

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, children, ...props }, ref) => {
    return (
      <div className="w-full space-y-1.5">
        {label && <label className="block text-xs font-medium text-[#929AAA]">{label}</label>}
        <div className="relative flex items-center">
          <select
            ref={ref}
            className={cn(
              'w-full h-9 bg-[#10131A] border border-[#252B36] rounded-lg px-3 py-1.5 text-sm text-[#F5F7FA] focus:outline-none focus:border-[#8B7CFF] focus:ring-1 focus:ring-[#8B7CFF] transition-all appearance-none cursor-pointer pr-8',
              error && 'border-red-500 focus:border-red-500',
              className
            )}
            {...props}
          >
            {children}
          </select>
          <ChevronDown className="absolute right-3 w-4 h-4 text-[#929AAA] pointer-events-none" />
        </div>
        {error && <p className="text-xs text-red-400 font-medium">{error}</p>}
      </div>
    );
  }
);

Select.displayName = 'Select';

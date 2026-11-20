'use client';

import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  description?: string;
  children: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl';
  showCloseButton?: boolean;
}

export function Modal({
  isOpen,
  onClose,
  title,
  description,
  children,
  maxWidth = 'lg',
  showCloseButton = true,
}: ModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const maxWidths = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    '3xl': 'max-w-3xl',
    '4xl': 'max-w-4xl',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-[#0B0D12]/80 backdrop-blur-sm transition-opacity animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Dialog Window */}
      <div
        className={cn(
          'relative w-full bg-[#151922] border border-[#252B36] rounded-2xl shadow-2xl overflow-hidden z-10 animate-in zoom-in-95 fade-in duration-200 flex flex-col max-h-[90vh]',
          maxWidths[maxWidth]
        )}
      >
        {(title || showCloseButton) && (
          <div className="flex items-center justify-between px-6 py-4 border-b border-[#252B36]/80 shrink-0">
            <div>
              {typeof title === 'string' ? (
                <h3 className="text-lg font-semibold text-[#F5F7FA] tracking-tight">{title}</h3>
              ) : (
                title
              )}
              {description && <p className="text-xs text-[#929AAA] mt-0.5">{description}</p>}
            </div>
            {showCloseButton && (
              <button
                onClick={onClose}
                className="text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#1B202C] p-1.5 rounded-lg transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        )}

        <div className="p-6 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}

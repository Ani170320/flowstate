'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  title: string;
  message?: string;
  type: ToastType;
  duration?: number;
}

interface ToastContextType {
  toast: (options: { title: string; message?: string; type?: ToastType; duration?: number }) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    ({ title, message, type = 'info', duration = 4000 }: { title: string; message?: string; type?: ToastType; duration?: number }) => {
      const id = `toast_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
      const newToast: Toast = { id, title, message, type, duration };

      setToasts((prev) => [...prev, newToast]);

      if (duration > 0) {
        setTimeout(() => {
          dismiss(id);
        }, duration);
      }
    },
    [dismiss]
  );

  const success = useCallback((title: string, message?: string) => toast({ title, message, type: 'success' }), [toast]);
  const error = useCallback((title: string, message?: string) => toast({ title, message, type: 'error' }), [toast]);
  const warning = useCallback((title: string, message?: string) => toast({ title, message, type: 'warning' }), [toast]);
  const info = useCallback((title: string, message?: string) => toast({ title, message, type: 'info' }), [toast]);

  return (
    <ToastContext.Provider value={{ toast, success, error, warning, info, dismiss }}>
      {children}
      {/* Toast Notification Container */}
      <div className="fixed bottom-5 right-5 z-[100] flex flex-col gap-2 max-w-sm w-full pointer-events-none px-4 sm:px-0">
        {toasts.map((t) => {
          const icons = {
            success: <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />,
            error: <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />,
            warning: <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />,
            info: <Info className="w-5 h-5 text-[#8B7CFF] shrink-0" />,
          };

          return (
            <div
              key={t.id}
              className="pointer-events-auto flex items-start gap-3 p-3.5 bg-[#151922] border border-[#252B36] rounded-xl shadow-2xl backdrop-blur-md animate-in slide-in-from-bottom-3 duration-200"
            >
              <div className="mt-0.5">{icons[t.type]}</div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[#F5F7FA] leading-tight">{t.title}</p>
                {t.message && <p className="text-xs text-[#929AAA] mt-1 leading-relaxed">{t.message}</p>}
              </div>
              <button
                onClick={() => dismiss(t.id)}
                className="text-[#929AAA] hover:text-[#F5F7FA] p-1 rounded-md transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

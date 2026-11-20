import React from 'react';
import { Button } from './Button';
import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({ icon: Icon, title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-[#252B36] rounded-2xl bg-[#10131A]/40 my-6">
      <div className="w-12 h-12 rounded-xl bg-[#151922] border border-[#252B36] flex items-center justify-center text-[#8B7CFF] mb-4">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-[#F5F7FA] mb-1">{title}</h3>
      <p className="text-sm text-[#929AAA] max-w-sm mb-6 leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <Button onClick={onAction} variant="primary" size="sm">
          {actionLabel}
        </Button>
      )}
    </div>
  );
}

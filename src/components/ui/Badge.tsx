import React from 'react';
import { cn, getPriorityMeta, getStatusMeta, getProjectStatusMeta } from '@/lib/utils';
import { Priority, TaskStatus, ProjectStatus } from '@/types';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'outline' | 'subtle';
  size?: 'sm' | 'md';
}

export function Badge({ className, variant = 'default', size = 'sm', children, ...props }: BadgeProps) {
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 font-medium rounded-md border tracking-wide select-none',
        variant === 'default' && 'bg-[#1A202C] text-[#F5F7FA] border-[#252B36]',
        sizeClasses,
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

export function PriorityBadge({ priority, className }: { priority: Priority; className?: string }) {
  const meta = getPriorityMeta(priority);
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium border uppercase tracking-wider',
        meta.badgeClass,
        className
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: meta.color }} />
      {meta.label}
    </span>
  );
}

export function TaskStatusBadge({ status, className }: { status: TaskStatus; className?: string }) {
  const meta = getStatusMeta(status);
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium border',
        meta.badgeClass,
        className
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: meta.color }} />
      {meta.label}
    </span>
  );
}

export function ProjectStatusBadge({ status, className }: { status: ProjectStatus; className?: string }) {
  const meta = getProjectStatusMeta(status);
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-medium',
        meta.badgeClass,
        className
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: meta.color }} />
      {meta.label}
    </span>
  );
}

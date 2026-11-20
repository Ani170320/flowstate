import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, formatDistanceToNow, parseISO, isAfter, isBefore, startOfDay } from 'date-fns';
import { Priority, TaskStatus, ProjectStatus } from '@/types';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isValidUuid(id: string | null | undefined): boolean {
  return typeof id === 'string' && UUID_REGEX.test(id);
}

export const DEFAULT_ORG_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';

export function formatReadableDate(dateString: string | undefined): string {
  if (!dateString) return 'No date';
  try {
    const d = parseISO(dateString);
    return format(d, 'MMM d, yyyy');
  } catch {
    return dateString;
  }
}

export function formatShortDate(dateString: string | undefined): string {
  if (!dateString) return '-';
  try {
    const d = parseISO(dateString);
    return format(d, 'MMM d');
  } catch {
    return dateString;
  }
}

export function getNow(): Date {
  return new Date();
}

export function formatRelativeTime(dateString: string | undefined): string {
  if (!dateString) return '';
  try {
    const d = parseISO(dateString);
    return formatDistanceToNow(d, { addSuffix: true });
  } catch {
    return dateString;
  }
}

export function isTaskOverdue(dueDateString: string | undefined, status: TaskStatus): boolean {
  if (!dueDateString || status === 'done') return false;
  try {
    const dueDate = parseISO(dueDateString);
    const today = startOfDay(getNow());
    return isBefore(dueDate, today);
  } catch {
    return false;
  }
}

export function getInitials(name: string): string {
  if (!name) return '??';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function getPriorityMeta(priority: Priority) {
  switch (priority) {
    case 'urgent':
      return {
        label: 'Urgent',
        color: '#EF4444',
        textColor: 'text-red-400',
        bgColor: 'bg-red-500/10 border-red-500/20 text-red-400',
        badgeClass: 'bg-red-950/60 text-red-400 border border-red-800/50',
      };
    case 'high':
      return {
        label: 'High',
        color: '#F59E0B',
        textColor: 'text-amber-400',
        bgColor: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
        badgeClass: 'bg-amber-950/60 text-amber-400 border border-amber-800/50',
      };
    case 'medium':
      return {
        label: 'Medium',
        color: '#8B7CFF',
        textColor: 'text-indigo-400',
        bgColor: 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400',
        badgeClass: 'bg-indigo-950/60 text-indigo-400 border border-indigo-800/50',
      };
    case 'low':
      return {
        label: 'Low',
        color: '#929AAA',
        textColor: 'text-neutral-400',
        bgColor: 'bg-neutral-500/10 border-neutral-500/20 text-neutral-400',
        badgeClass: 'bg-neutral-800/60 text-neutral-400 border border-neutral-700/50',
      };
  }
}

export function getStatusMeta(status: TaskStatus) {
  switch (status) {
    case 'backlog':
      return {
        label: 'Backlog',
        color: '#6B7280',
        columnTitle: 'Backlog',
        badgeClass: 'bg-neutral-800/70 text-neutral-400 border-neutral-700/50',
      };
    case 'todo':
      return {
        label: 'To Do',
        color: '#3B82F6',
        columnTitle: 'To Do',
        badgeClass: 'bg-blue-950/50 text-blue-400 border-blue-800/40',
      };
    case 'in_progress':
      return {
        label: 'In Progress',
        color: '#8B7CFF',
        columnTitle: 'In Progress',
        badgeClass: 'bg-indigo-950/50 text-indigo-300 border-indigo-700/40',
      };
    case 'in_review':
      return {
        label: 'In Review',
        color: '#F59E0B',
        columnTitle: 'In Review',
        badgeClass: 'bg-amber-950/50 text-amber-300 border-amber-700/40',
      };
    case 'done':
      return {
        label: 'Done',
        color: '#22C55E',
        columnTitle: 'Done',
        badgeClass: 'bg-emerald-950/50 text-emerald-400 border-emerald-800/40',
      };
  }
}

export function getProjectStatusMeta(status: ProjectStatus) {
  switch (status) {
    case 'planning':
      return {
        label: 'Planning',
        color: '#8B7CFF',
        badgeClass: 'bg-indigo-950/50 text-indigo-300 border border-indigo-800/40',
      };
    case 'in_progress':
      return {
        label: 'In Progress',
        color: '#3B82F6',
        badgeClass: 'bg-blue-950/50 text-blue-300 border border-blue-800/40',
      };
    case 'in_review':
      return {
        label: 'In Review',
        color: '#F59E0B',
        badgeClass: 'bg-amber-950/50 text-amber-300 border border-amber-800/40',
      };
    case 'completed':
      return {
        label: 'Completed',
        color: '#22C55E',
        badgeClass: 'bg-emerald-950/50 text-emerald-300 border border-emerald-800/40',
      };
    case 'on_hold':
      return {
        label: 'On Hold',
        color: '#EF4444',
        badgeClass: 'bg-red-950/50 text-red-300 border border-red-800/40',
      };
  }
}

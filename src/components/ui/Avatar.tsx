import React, { useState } from 'react';
import { cn, getInitials } from '@/lib/utils';
import { User } from '@/types';

interface AvatarProps {
  user?: User | null;
  name?: string;
  avatarUrl?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  showStatus?: boolean;
  statusOnline?: boolean;
}

export function Avatar({
  user,
  name = user?.name || 'User',
  avatarUrl = user?.avatar,
  size = 'md',
  className,
  showStatus = false,
  statusOnline = true,
}: AvatarProps) {
  const [imageError, setImageError] = useState(false);

  const sizes = {
    xs: 'w-5 h-5 text-[10px]',
    sm: 'w-6 h-6 text-xs',
    md: 'w-8 h-8 text-xs',
    lg: 'w-10 h-10 text-sm font-semibold',
    xl: 'w-16 h-16 text-lg font-bold',
  };

  const statusSizes = {
    xs: 'w-1.5 h-1.5 bottom-0 right-0',
    sm: 'w-2 h-2 bottom-0 right-0',
    md: 'w-2.5 h-2.5 bottom-0 right-0',
    lg: 'w-3 h-3 bottom-0 right-0',
    xl: 'w-4 h-4 bottom-0.5 right-0.5',
  };

  return (
    <div className={cn('relative inline-flex shrink-0 select-none', className)} suppressHydrationWarning>
      <div
        className={cn(
          'rounded-full overflow-hidden flex items-center justify-center bg-[#1B202C] border border-[#252B36] text-[#F5F7FA] font-medium transition-all',
          sizes[size]
        )}
        suppressHydrationWarning
      >
        {avatarUrl && !imageError ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={avatarUrl}
            alt={name}
            onError={() => setImageError(true)}
            className="w-full h-full object-cover"
            suppressHydrationWarning
          />
        ) : (
          <span suppressHydrationWarning>{getInitials(name)}</span>
        )}
      </div>
      {showStatus && (
        <span
          className={cn(
            'absolute rounded-full ring-2 ring-[#0B0D12]',
            statusOnline ? 'bg-emerald-500' : 'bg-neutral-500',
            statusSizes[size]
          )}
        />
      )}
    </div>
  );
}

export function AvatarGroup({ users = [], max = 4, size = 'sm' }: { users: (User | undefined)[]; max?: number; size?: 'xs' | 'sm' | 'md' }) {
  const validUsers = users.filter(Boolean) as User[];
  const displayed = validUsers.slice(0, max);
  const remaining = validUsers.length - max;

  return (
    <div className="flex items-center -space-x-2 overflow-hidden py-0.5">
      {displayed.map((u, i) => (
        <Avatar key={u.id || i} user={u} size={size} className="ring-2 ring-[#10131A] hover:z-10 hover:scale-105 transition-transform" />
      ))}
      {remaining > 0 && (
        <div
          className={cn(
            'rounded-full bg-[#1A202C] border border-[#252B36] text-[#929AAA] flex items-center justify-center font-medium ring-2 ring-[#10131A]',
            size === 'xs' ? 'w-5 h-5 text-[9px]' : size === 'sm' ? 'w-6 h-6 text-[10px]' : 'w-8 h-8 text-xs'
          )}
        >
          +{remaining}
        </div>
      )}
    </div>
  );
}

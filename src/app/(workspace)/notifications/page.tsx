'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { Notification } from '@/types';
import { Avatar } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { formatRelativeTime } from '@/lib/utils';
import {
  Bell,
  CheckCheck,
  Calendar,
  MessageSquare,
  Sparkles,
  AlertTriangle,
  FolderKanban,
  CheckSquare,
  ArrowRight,
} from 'lucide-react';

export default function NotificationsPage() {
  const { user } = useAuth();
  const { notifications, markNotificationRead, markAllNotificationsRead } = useWorkspace();

  const [activeFilter, setActiveFilter] = useState<'all' | 'unread' | 'assignment' | 'deadline' | 'mention'>('all');

  const filteredNotifications = useMemo(() => {
    let result = [...notifications];

    if (activeFilter === 'unread') {
      result = result.filter((n) => !n.isRead);
    } else if (activeFilter !== 'all') {
      result = result.filter((n) => n.type === activeFilter);
    }

    return result;
  }, [notifications, activeFilter]);

  const unreadCount = notifications.filter((n) => !n.isRead).length;

  const getNotifIcon = (type: Notification['type']) => {
    switch (type) {
      case 'assignment':
        return <CheckSquare className="w-4 h-4 text-[#8B7CFF]" />;
      case 'deadline':
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case 'mention':
        return <MessageSquare className="w-4 h-4 text-blue-400" />;
      case 'project_update':
        return <FolderKanban className="w-4 h-4 text-emerald-400" />;
      default:
        return <Sparkles className="w-4 h-4 text-purple-400" />;
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#252B36]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-[#F5F7FA]">Notifications</h1>
            {unreadCount > 0 && (
              <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-[#8B7CFF] text-white">
                {unreadCount} unread
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-[#929AAA] mt-1">
            Task assignments, @mentions, project milestones, and urgent deadline alerts.
          </p>
        </div>

        {unreadCount > 0 && (
          <Button
            onClick={() => markAllNotificationsRead()}
            variant="outline"
            size="sm"
            className="gap-1.5 cursor-pointer"
          >
            <CheckCheck className="w-4 h-4 text-emerald-400" />
            <span>Mark All as Read</span>
          </Button>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-1.5 p-1 bg-[#10131A] border border-[#252B36] rounded-xl overflow-x-auto">
        <button
          onClick={() => setActiveFilter('all')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer shrink-0 ${
            activeFilter === 'all'
              ? 'bg-[#151922] text-[#F5F7FA] border border-[#252B36]'
              : 'text-[#929AAA] hover:text-[#F5F7FA]'
          }`}
        >
          All ({notifications.length})
        </button>
        <button
          onClick={() => setActiveFilter('unread')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer shrink-0 ${
            activeFilter === 'unread'
              ? 'bg-[#151922] text-[#F5F7FA] border border-[#252B36]'
              : 'text-[#929AAA] hover:text-[#F5F7FA]'
          }`}
        >
          Unread ({unreadCount})
        </button>
        <button
          onClick={() => setActiveFilter('assignment')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer shrink-0 ${
            activeFilter === 'assignment'
              ? 'bg-[#151922] text-[#F5F7FA] border border-[#252B36]'
              : 'text-[#929AAA] hover:text-[#F5F7FA]'
          }`}
        >
          Assignments
        </button>
        <button
          onClick={() => setActiveFilter('deadline')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer shrink-0 ${
            activeFilter === 'deadline'
              ? 'bg-[#151922] text-[#F5F7FA] border border-[#252B36]'
              : 'text-[#929AAA] hover:text-[#F5F7FA]'
          }`}
        >
          Deadlines
        </button>
        <button
          onClick={() => setActiveFilter('mention')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer shrink-0 ${
            activeFilter === 'mention'
              ? 'bg-[#151922] text-[#F5F7FA] border border-[#252B36]'
              : 'text-[#929AAA] hover:text-[#F5F7FA]'
          }`}
        >
          Mentions
        </button>
      </div>

      {/* Notifications List */}
      <div className="bg-[#151922] border border-[#252B36] rounded-2xl overflow-hidden divide-y divide-[#252B36]/60">
        {filteredNotifications.length === 0 ? (
          <div className="py-16 text-center text-xs text-[#929AAA]">
            You have no notifications in this view.
          </div>
        ) : (
          filteredNotifications.map((notif) => (
            <div
              key={notif.id}
              onClick={() => markNotificationRead(notif.id)}
              className={`p-4 transition-colors cursor-pointer flex items-start gap-3.5 hover:bg-[#1B202C] ${
                !notif.isRead ? 'bg-[#8B7CFF]/5 border-l-2 border-l-[#8B7CFF]' : ''
              }`}
            >
              <div className="w-8 h-8 rounded-lg bg-[#10131A] border border-[#252B36] flex items-center justify-center shrink-0 mt-0.5">
                {getNotifIcon(notif.type)}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <h4 className="text-xs font-semibold text-[#F5F7FA]">{notif.title}</h4>
                  <span className="text-[10px] text-[#929AAA] shrink-0 font-mono">
                    {formatRelativeTime(notif.createdAt)}
                  </span>
                </div>
                <p className="text-xs text-[#929AAA] leading-relaxed">{notif.message}</p>
                {notif.link && (
                  <Link
                    href={notif.link}
                    className="inline-flex items-center gap-1 text-[11px] text-[#8B7CFF] hover:underline font-medium mt-2"
                  >
                    <span>View item</span>
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                )}
              </div>

              {!notif.isRead && (
                <span className="w-2 h-2 rounded-full bg-[#8B7CFF] shrink-0 mt-1.5" />
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

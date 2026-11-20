'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  Search,
  Plus,
  Bell,
  ChevronRight,
  Menu,
  CheckCheck,
  ExternalLink,
  FolderKanban,
  CheckSquare,
  LogOut,
  Settings,
  Sparkles,
  UserCircle2,
  Building2,
} from 'lucide-react';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { Avatar } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { formatRelativeTime } from '@/lib/utils';

export function TopNav({ onMobileMenuToggle }: { onMobileMenuToggle?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, activeOrg, logout } = useAuth();
  const { success } = useToast();
  const {
    openSearch,
    openCreateTask,
    openCreateProject,
    notifications,
    unreadNotificationsCount,
    markNotificationRead,
    markAllNotificationsRead,
    projects,
  } = useWorkspace();

  const [isNotifPopoverOpen, setIsNotifPopoverOpen] = useState(false);
  const [isCreateDropdownOpen, setIsCreateDropdownOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  const handleSignOut = async () => {
    setIsUserMenuOpen(false);
    try {
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('flowstate_prevent_auto_login', 'true');
      }
      await logout();
      success('Signed Out', 'You have been safely signed out of FLOWSTATE.');
      router.push('/login');
    } catch {
      router.push('/login');
    }
  };

  // Generate breadcrumb items
  const pathParts = pathname.split('/').filter(Boolean);
  const breadcrumbItems = pathParts.map((part, index) => {
    const href = '/' + pathParts.slice(0, index + 1).join('/');
    let label = part.charAt(0).toUpperCase() + part.slice(1).replace('-', ' ');

    // If part matches a project ID, display the project's actual name
    if (part.startsWith('proj_')) {
      const p = projects.find((proj) => proj.id === part);
      if (p) label = p.name;
    }

    return { href, label };
  });

  return (
    <header className="h-14 border-b border-[#252B36] bg-[#0B0D12]/95 backdrop-blur-md sticky top-0 z-20 flex items-center justify-between px-4 sm:px-6">
      {/* Left: Mobile hamburger + Breadcrumbs */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMobileMenuToggle}
          className="md:hidden text-[#929AAA] hover:text-[#F5F7FA] p-1.5 rounded-lg hover:bg-[#151922] cursor-pointer"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Breadcrumb Trail */}
        <nav className="flex items-center gap-1.5 text-xs text-[#929AAA] min-w-0">
          <Link
            href="/dashboard"
            className="hover:text-[#F5F7FA] font-medium transition-colors shrink-0"
          >
            Flowstate
          </Link>
          {breadcrumbItems.length > 0 && (
            <>
              {breadcrumbItems.map((item, idx) => (
                <React.Fragment key={item.href}>
                  <ChevronRight className="w-3.5 h-3.5 text-[#929AAA]/60 shrink-0" />
                  {idx === breadcrumbItems.length - 1 ? (
                    <span className="text-[#F5F7FA] font-medium truncate max-w-[200px] sm:max-w-xs">
                      {item.label}
                    </span>
                  ) : (
                    <Link
                      href={item.href}
                      className="hover:text-[#F5F7FA] transition-colors truncate max-w-[150px]"
                    >
                      {item.label}
                    </Link>
                  )}
                </React.Fragment>
              ))}
            </>
          )}
        </nav>
      </div>

      {/* Right: Global Search, Create Button, Notifications, Avatar */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {/* Global Search Bar Trigger */}
        <button
          onClick={openSearch}
          className="flex items-center gap-2 px-3 py-1.5 bg-[#151922] hover:bg-[#1A202C] border border-[#252B36] hover:border-[#323A4A] rounded-lg text-xs text-[#929AAA] hover:text-[#F5F7FA] transition-all cursor-pointer shadow-sm group"
        >
          <Search className="w-3.5 h-3.5 group-hover:text-[#8B7CFF] transition-colors" />
          <span className="hidden sm:inline">Search anything...</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] bg-[#10131A] text-[#929AAA] border border-[#252B36] rounded font-mono">
            <span className="text-[11px]">⌘</span>K
          </kbd>
        </button>

        {/* Quick Create Dropdown */}
        <div className="relative">
          <Button
            size="sm"
            onClick={() => setIsCreateDropdownOpen(!isCreateDropdownOpen)}
            className="gap-1.5 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">Create</span>
          </Button>

          {isCreateDropdownOpen && (
            <div className="absolute right-0 mt-2 w-48 bg-[#151922] border border-[#252B36] rounded-xl shadow-2xl py-1.5 z-40 animate-in fade-in zoom-in-95 duration-150">
              <button
                onClick={() => {
                  setIsCreateDropdownOpen(false);
                  openCreateTask();
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-[#F5F7FA] hover:bg-[#1B202C] transition-colors text-left cursor-pointer"
              >
                <CheckSquare className="w-4 h-4 text-[#8B7CFF]" />
                <div className="flex-1">
                  <p className="font-medium">New Task</p>
                  <p className="text-[10px] text-[#929AAA]">Press &apos;C&apos; anywhere</p>
                </div>
              </button>
              <button
                onClick={() => {
                  setIsCreateDropdownOpen(false);
                  openCreateProject();
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-[#F5F7FA] hover:bg-[#1B202C] transition-colors text-left cursor-pointer"
              >
                <FolderKanban className="w-4 h-4 text-emerald-400" />
                <div className="flex-1">
                  <p className="font-medium">New Project</p>
                  <p className="text-[10px] text-[#929AAA]">Manage roadmaps</p>
                </div>
              </button>
            </div>
          )}
        </div>

        {/* Notifications Icon with popover preview */}
        <div className="relative">
          <button
            onClick={() => setIsNotifPopoverOpen(!isNotifPopoverOpen)}
            className="relative p-2 rounded-lg bg-[#151922] hover:bg-[#1B202C] border border-[#252B36] text-[#929AAA] hover:text-[#F5F7FA] transition-colors cursor-pointer"
            aria-label="View notifications"
          >
            <Bell className="w-4 h-4" />
            {unreadNotificationsCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#8B7CFF] text-white text-[10px] font-bold rounded-full flex items-center justify-center animate-pulse">
                {unreadNotificationsCount}
              </span>
            )}
          </button>

          {isNotifPopoverOpen && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-[#151922] border border-[#252B36] rounded-xl shadow-2xl z-40 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between p-3.5 border-b border-[#252B36]">
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-semibold text-[#F5F7FA] uppercase tracking-wider">
                    Notifications
                  </h4>
                  {unreadNotificationsCount > 0 && (
                    <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-[#8B7CFF]/20 text-[#8B7CFF] font-semibold">
                      {unreadNotificationsCount} unread
                    </span>
                  )}
                </div>
                {unreadNotificationsCount > 0 && (
                  <button
                    onClick={() => markAllNotificationsRead()}
                    className="text-[11px] text-[#8B7CFF] hover:underline flex items-center gap-1 cursor-pointer"
                  >
                    <CheckCheck className="w-3.5 h-3.5" />
                    <span>Mark all read</span>
                  </button>
                )}
              </div>

              <div className="max-h-80 overflow-y-auto divide-y divide-[#252B36]/60">
                {notifications.slice(0, 5).map((n) => (
                  <div
                    key={n.id}
                    onClick={() => markNotificationRead(n.id)}
                    className={`p-3 text-xs hover:bg-[#1B202C] transition-colors cursor-pointer ${
                      !n.isRead ? 'bg-[#8B7CFF]/5' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <p className="font-semibold text-[#F5F7FA]">{n.title}</p>
                      <span className="text-[10px] text-[#929AAA] shrink-0">
                        {formatRelativeTime(n.createdAt)}
                      </span>
                    </div>
                    <p className="text-[#929AAA] line-clamp-2 leading-relaxed">{n.message}</p>
                  </div>
                ))}
              </div>

              <div className="p-2.5 bg-[#10131A] border-t border-[#252B36] text-center">
                <Link
                  href="/notifications"
                  onClick={() => setIsNotifPopoverOpen(false)}
                  className="text-xs font-medium text-[#8B7CFF] hover:underline flex items-center justify-center gap-1"
                >
                  <span>View all notifications</span>
                  <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* Direct One-Click Sign Out Button */}
        <button
          onClick={handleSignOut}
          title="Sign Out of FLOWSTATE"
          aria-label="Sign Out"
          className="p-2 rounded-lg bg-[#151922] hover:bg-red-500/10 border border-[#252B36] hover:border-red-500/30 text-[#929AAA] hover:text-red-400 transition-colors cursor-pointer group flex items-center gap-1.5"
        >
          <LogOut className="w-4 h-4 group-hover:scale-110 transition-transform" />
          <span className="hidden xl:inline text-xs font-medium">Sign Out</span>
        </button>

        {/* User Profile Popover Trigger & Dropdown */}
        <div className="relative">
          <button
            onClick={() => {
              setIsUserMenuOpen(!isUserMenuOpen);
              setIsNotifPopoverOpen(false);
              setIsCreateDropdownOpen(false);
            }}
            className="flex items-center gap-2 p-0.5 rounded-full hover:ring-2 hover:ring-[var(--accent)]/50 transition-all cursor-pointer focus:outline-none"
            aria-label="User profile menu"
          >
            <Avatar user={user} size="sm" showStatus statusOnline />
          </button>

          {isUserMenuOpen && (
            <div className="absolute right-0 mt-2 w-72 bg-[#151922] border border-[#252B36] rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              {/* User Card Header */}
              <div className="p-4 bg-gradient-to-b from-[#1B202C] to-[#151922] border-b border-[#252B36]">
                <div className="flex items-center gap-3">
                  <Avatar user={user} size="md" />
                  <div className="min-w-0 flex-1" suppressHydrationWarning>
                    <p className="text-xs font-bold text-[#F5F7FA] truncate" suppressHydrationWarning>{user.name}</p>
                    <p className="text-[11px] text-[#929AAA] truncate" suppressHydrationWarning>{user.email}</p>
                    <div className="flex items-center gap-1.5 mt-1.5">
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase bg-[var(--accent-subtle)] text-[var(--accent)] font-bold">
                        {user.role}
                      </span>
                      <span className="text-[10px] text-[#929AAA] truncate flex items-center gap-1">
                        <Building2 className="w-3 h-3 text-[var(--accent)]" />
                        {activeOrg?.name || 'Workspace'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Navigation Links */}
              <div className="p-2 space-y-1 text-xs">
                <Link
                  href="/settings"
                  onClick={() => setIsUserMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-[#F5F7FA] hover:bg-[#1B202C] transition-colors"
                >
                  <Settings className="w-4 h-4 text-[#929AAA]" />
                  <span>Workspace Settings</span>
                </Link>

                <Link
                  href="/settings"
                  onClick={() => setIsUserMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-[#F5F7FA] hover:bg-[#1B202C] transition-colors"
                >
                  <Sparkles className="w-4 h-4 text-[var(--accent)]" />
                  <span>Appearance & Theme</span>
                </Link>

                <Link
                  href="/members"
                  onClick={() => setIsUserMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-[#F5F7FA] hover:bg-[#1B202C] transition-colors"
                >
                  <UserCircle2 className="w-4 h-4 text-[#929AAA]" />
                  <span>Team Members</span>
                </Link>
              </div>

              {/* Prominent Red Sign Out Action */}
              <div className="p-2 border-t border-[#252B36] bg-[#10131A]/60">
                <button
                  onClick={handleSignOut}
                  className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 transition-all cursor-pointer"
                >
                  <span className="flex items-center gap-2">
                    <LogOut className="w-4 h-4" />
                    <span>Sign Out of FLOWSTATE</span>
                  </span>
                  <span className="text-[10px] text-red-400/80 font-mono">Log Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

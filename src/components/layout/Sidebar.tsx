'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  CheckSquare,
  FolderKanban,
  Calendar,
  Users2,
  UserCheck,
  BarChart3,
  Bell,
  Settings,
  ChevronLeft,
  ChevronRight,
  ChevronsUpDown,
  Sparkles,
  Plus,
  Check,
  UserCircle2,
  LogOut,
  FolderPlus,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { Avatar } from '@/components/ui/Avatar';

interface NavItem {
  title: string;
  href: string;
  icon: React.ElementType;
  badge?: number;
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, allUsers, switchUser, activeOrg, organizations, switchOrganization, logout } = useAuth();
  const {
    isSidebarCollapsed,
    toggleSidebar,
    unreadNotificationsCount,
    tasks,
    projects,
    openCreateTask,
    openCreateProject,
  } = useWorkspace();

  const [isWorkspaceMenuOpen, setIsWorkspaceMenuOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);

  const handleLogout = async () => {
    setIsProfileMenuOpen(false);
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('flowstate_prevent_auto_login', 'true');
    }
    await logout();
    router.push('/login');
  };

  const displayOrganizations = organizations.length > 0 ? organizations : [
    activeOrg || { id: 'org_default', name: 'Flowstate Labs', plan: 'free' as const, slug: 'flowstate-labs', membersCount: 4 }
  ];

  // Count my active tasks
  const myActiveTasksCount = tasks.filter(
    (t) => t.assigneeId === user.id && t.status !== 'done'
  ).length;

  const workspaceGroups: { title: string; items: NavItem[] }[] = [
    {
      title: 'WORKSPACE',
      items: [
        { title: 'Overview', href: '/dashboard', icon: LayoutDashboard },
        { title: 'My Tasks', href: '/my-tasks', icon: CheckSquare, badge: myActiveTasksCount },
        { title: 'Projects', href: '/projects', icon: FolderKanban, badge: projects.length },
        { title: 'Calendar', href: '/calendar', icon: Calendar },
      ],
    },
    {
      title: 'MANAGEMENT',
      items: [
        { title: 'Teams', href: '/teams', icon: Users2 },
        { title: 'Members', href: '/members', icon: UserCheck, badge: allUsers.length },
        { title: 'Analytics', href: '/analytics', icon: BarChart3 },
      ],
    },
    {
      title: 'PERSONAL',
      items: [
        { title: 'Notifications', href: '/notifications', icon: Bell, badge: unreadNotificationsCount },
        { title: 'Settings', href: '/settings', icon: Settings },
      ],
    },
  ];

  return (
    <aside
      className={cn(
        'relative flex flex-col bg-[#10131A] border-r border-[#252B36] h-screen transition-all duration-300 z-30 select-none shrink-0',
        isSidebarCollapsed ? 'w-[68px]' : 'w-[260px]'
      )}
    >
      {/* Header / Brand */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-[#252B36]/80 shrink-0">
        {!isSidebarCollapsed ? (
          <Link href="/dashboard" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#8B7CFF] to-[#6351E6] flex items-center justify-center text-white shadow-md shadow-[#8B7CFF]/20 group-hover:scale-105 transition-transform">
              <Sparkles className="w-4 h-4 fill-white/20" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-sm tracking-tight text-[#F5F7FA] font-mono">FLOWSTATE</span>
              <span className="text-[10px] text-[#929AAA] uppercase tracking-wider font-medium">SaaS Platform</span>
            </div>
          </Link>
        ) : (
          <Link href="/dashboard" className="mx-auto">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#8B7CFF] to-[#6351E6] flex items-center justify-center text-white shadow-md shadow-[#8B7CFF]/20">
              <Sparkles className="w-4 h-4" />
            </div>
          </Link>
        )}

        <button
          onClick={toggleSidebar}
          aria-label={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#151922] p-1.5 rounded-md transition-colors hidden md:flex cursor-pointer"
        >
          {isSidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Quick Action Button */}
      {!isSidebarCollapsed ? (
        <div className="px-3 pt-3 pb-1">
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => openCreateTask()}
              className="flex items-center justify-center gap-1.5 py-1.5 px-2 bg-[#8B7CFF]/10 hover:bg-[#8B7CFF]/20 text-[#8B7CFF] border border-[#8B7CFF]/25 rounded-lg text-xs font-medium transition-all cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Task</span>
            </button>
            <button
              onClick={() => openCreateProject()}
              className="flex items-center justify-center gap-1.5 py-1.5 px-2 bg-[#151922] hover:bg-[#1A202C] text-[#F5F7FA] border border-[#252B36] rounded-lg text-xs font-medium transition-all cursor-pointer"
            >
              <FolderPlus className="w-3.5 h-3.5 text-[#929AAA]" />
              <span>Project</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="px-2 pt-3 pb-1 flex justify-center">
          <button
            onClick={() => openCreateTask()}
            title="Create Task (C)"
            className="w-10 h-10 rounded-lg bg-[#8B7CFF] hover:bg-[#7968EE] text-white flex items-center justify-center shadow-lg shadow-[#8B7CFF]/30 transition-transform active:scale-95 cursor-pointer"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Navigation List */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-6">
        {workspaceGroups.map((group) => (
          <div key={group.title} className="space-y-1">
            {!isSidebarCollapsed && (
              <p className="px-2.5 text-[10px] font-semibold text-[#929AAA]/70 tracking-wider">
                {group.title}
              </p>
            )}
            <nav className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive =
                  pathname === item.href ||
                  (item.href !== '/dashboard' && pathname.startsWith(item.href));

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={isSidebarCollapsed ? item.title : undefined}
                    className={cn(
                      'flex items-center gap-3 px-2.5 py-2 rounded-lg text-xs font-medium transition-all group relative',
                      isActive
                        ? 'bg-[#151922] text-[#F5F7FA] font-semibold shadow-sm border border-[#252B36]'
                        : 'text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#151922]/60'
                    )}
                  >
                    <Icon
                      className={cn(
                        'w-4 h-4 shrink-0 transition-colors',
                        isActive ? 'text-[#8B7CFF]' : 'text-[#929AAA] group-hover:text-[#F5F7FA]'
                      )}
                    />
                    {!isSidebarCollapsed && (
                      <span className="flex-1 truncate">{item.title}</span>
                    )}
                    {!isSidebarCollapsed && item.badge !== undefined && item.badge > 0 && (
                      <span
                        className={cn(
                          'px-1.5 py-0.5 text-[10px] rounded-full font-mono shrink-0',
                          item.title === 'Notifications'
                            ? 'bg-[#8B7CFF] text-white font-bold'
                            : 'bg-[#252B36] text-[#929AAA]'
                        )}
                      >
                        {item.badge}
                      </span>
                    )}
                    {/* Collapsed dot for unread notification */}
                    {isSidebarCollapsed && item.badge !== undefined && item.badge > 0 && (
                      <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[#8B7CFF]" />
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      {/* Sidebar Footer: Workspace selector & Profile menu */}
      <div className="p-3 border-t border-[#252B36] space-y-2 shrink-0 bg-[#10131A]">
        {/* Workspace Selector */}
        {!isSidebarCollapsed ? (
          <div className="relative">
            <button
              onClick={() => {
                setIsWorkspaceMenuOpen(!isWorkspaceMenuOpen);
                setIsProfileMenuOpen(false);
              }}
              className="w-full flex items-center justify-between p-2 rounded-lg bg-[#151922] hover:bg-[#1A202C] border border-[#252B36] text-left transition-all cursor-pointer"
            >
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-5 h-5 rounded bg-[var(--accent-subtle)] text-[var(--accent)] border border-[var(--accent)]/30 flex items-center justify-center text-[10px] font-bold uppercase">
                  {(activeOrg?.name || 'FL').substring(0, 2)}
                </div>
                <div className="min-w-0 truncate">
                  <p className="text-xs font-semibold text-[#F5F7FA] truncate">{activeOrg?.name || 'Flowstate Labs'}</p>
                  <p className="text-[10px] text-[#929AAA] capitalize">
                    {activeOrg?.plan ? `${activeOrg.plan} Plan` : 'Free Plan'}
                  </p>
                </div>
              </div>
              <ChevronsUpDown className="w-3.5 h-3.5 text-[#929AAA] shrink-0" />
            </button>

            {/* Workspace Dropdown */}
            {isWorkspaceMenuOpen && (
              <div className="absolute bottom-full left-0 right-0 mb-2 p-1.5 bg-[#151922] border border-[#252B36] rounded-xl shadow-2xl z-40 animate-in fade-in slide-in-from-bottom-2 duration-150">
                <div className="px-2 py-1 text-[10px] font-semibold text-[#929AAA] uppercase tracking-wider">
                  Switch Workspace
                </div>
                {displayOrganizations.map((org) => {
                  const isCurrent = activeOrg?.id === org.id;
                  return (
                    <button
                      key={org.id}
                      onClick={() => {
                        switchOrganization(org.id);
                        setIsWorkspaceMenuOpen(false);
                      }}
                      className={cn(
                        'w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs text-left transition-all cursor-pointer',
                        isCurrent
                          ? 'bg-[var(--accent-subtle)] text-[var(--accent)] font-medium'
                          : 'text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#1B202C]'
                      )}
                    >
                      <span className="truncate">{org.name}</span>
                      {isCurrent && <Check className="w-3.5 h-3.5 text-[var(--accent)] shrink-0" />}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        ) : null}

        {/* User Profile Trigger & Menu */}
        <div className="relative flex items-center gap-1">
          <button
            onClick={() => {
              setIsProfileMenuOpen(!isProfileMenuOpen);
              setIsWorkspaceMenuOpen(false);
            }}
            className={cn(
              'flex-1 flex items-center gap-2.5 p-1.5 rounded-lg hover:bg-[#151922] transition-all cursor-pointer text-left min-w-0',
              isSidebarCollapsed && 'justify-center'
            )}
          >
            <Avatar user={user} size="sm" showStatus statusOnline />
            {!isSidebarCollapsed && (
              <div className="min-w-0 flex-1 truncate" suppressHydrationWarning>
                <p className="text-xs font-medium text-[#F5F7FA] truncate" suppressHydrationWarning>{user.name}</p>
                <p className="text-[10px] text-[#929AAA] truncate" suppressHydrationWarning>{user.email}</p>
              </div>
            )}
          </button>

          {!isSidebarCollapsed && (
            <button
              onClick={handleLogout}
              title="Sign Out of FLOWSTATE"
              aria-label="Sign Out"
              className="p-2 rounded-lg text-[#929AAA] hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer shrink-0"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}

          {/* User Profile / Fast Switcher Dropdown */}
          {isProfileMenuOpen && (
            <div
              className={cn(
                'absolute bottom-full mb-2 p-2 bg-[#151922] border border-[#252B36] rounded-xl shadow-2xl z-40 animate-in fade-in slide-in-from-bottom-2 duration-150',
                isSidebarCollapsed ? 'left-14 w-64' : 'left-0 right-0'
              )}
            >
              <div className="px-2.5 py-2 border-b border-[#252B36] mb-2">
                <p className="text-xs font-semibold text-[#F5F7FA]">{user.name}</p>
                <p className="text-[11px] text-[#929AAA]">{user.title}</p>
                <span className="inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-[#8B7CFF]/20 text-[#8B7CFF] font-semibold">
                  {user.role}
                </span>
              </div>

              {/* Fast User Switcher (SaaS Prototype feature) */}
              <div className="px-2 py-1 text-[10px] font-semibold text-[#929AAA] uppercase tracking-wider">
                Simulate Role As:
              </div>
              <div className="max-h-36 overflow-y-auto space-y-1 mb-2">
                {allUsers.map((u) => (
                  <button
                    key={u.id}
                    onClick={() => {
                      switchUser(u.id);
                      setIsProfileMenuOpen(false);
                    }}
                    className={cn(
                      'w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-xs text-left transition-colors cursor-pointer',
                      user.id === u.id
                        ? 'bg-[#8B7CFF]/15 text-[#8B7CFF]'
                        : 'text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#1B202C]'
                    )}
                  >
                    <Avatar user={u} size="xs" />
                    <span className="truncate flex-1">{u.name}</span>
                    {user.id === u.id && <Check className="w-3.5 h-3.5 text-[#8B7CFF]" />}
                  </button>
                ))}
              </div>

              <div className="pt-2 border-t border-[#252B36] space-y-1">
                <Link
                  href="/settings"
                  onClick={() => setIsProfileMenuOpen(false)}
                  className="flex items-center gap-2 px-2 py-1.5 rounded-md text-xs text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#1B202C]"
                >
                  <UserCircle2 className="w-3.5 h-3.5" />
                  <span>Profile & Preferences</span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-xs font-medium text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 transition-all cursor-pointer"
                >
                  <span className="flex items-center gap-2">
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Sign Out of FLOWSTATE</span>
                  </span>
                  <span className="text-[10px] text-red-400/80 font-mono">Log Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

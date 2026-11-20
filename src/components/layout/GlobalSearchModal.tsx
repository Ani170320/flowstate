'use client';

import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  Search,
  CheckSquare,
  FolderKanban,
  User,
  Users2,
  Calendar,
  Settings,
  ArrowRight,
  Plus,
  X,
} from 'lucide-react';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { PriorityBadge, TaskStatusBadge } from '@/components/ui/Badge';
import { Avatar } from '@/components/ui/Avatar';

export function GlobalSearchModal() {
  const router = useRouter();
  const { allUsers } = useAuth();
  const {
    isSearchOpen,
    closeSearch,
    projects,
    tasks,
    teams,
    openCreateTask,
    openCreateProject,
    openTaskDetail,
  } = useWorkspace();

  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isSearchOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isSearchOpen]);

  const searchResults = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      // Default suggested actions
      return [
        {
          id: 'action-create-task',
          type: 'action',
          title: 'Create new task',
          subtitle: 'Shortcut: Press C anywhere',
          icon: Plus,
          action: () => {
            closeSearch();
            openCreateTask();
          },
        },
        {
          id: 'action-create-proj',
          type: 'action',
          title: 'Create new project',
          subtitle: 'Initialize roadmaps and team assignment',
          icon: FolderKanban,
          action: () => {
            closeSearch();
            openCreateProject();
          },
        },
        {
          id: 'nav-my-tasks',
          type: 'navigation',
          title: 'Go to My Tasks',
          subtitle: 'View your pending work & priorities',
          icon: CheckSquare,
          action: () => {
            closeSearch();
            router.push('/my-tasks');
          },
        },
        {
          id: 'nav-calendar',
          type: 'navigation',
          title: 'Go to Calendar',
          subtitle: 'Upcoming deadlines & release milestones',
          icon: Calendar,
          action: () => {
            closeSearch();
            router.push('/calendar');
          },
        },
        {
          id: 'nav-settings',
          type: 'navigation',
          title: 'Workspace Settings',
          subtitle: 'Profile, teams & notification rules',
          icon: Settings,
          action: () => {
            closeSearch();
            router.push('/settings');
          },
        },
      ];
    }

    const items: any[] = [];

    // Filter Tasks
    tasks
      .filter(
        (t) =>
          t.title.toLowerCase().includes(q) ||
          t.key?.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q)
      )
      .slice(0, 5)
      .forEach((t) => {
        items.push({
          id: `task-${t.id}`,
          type: 'task',
          item: t,
          title: `${t.key}: ${t.title}`,
          subtitle: `${t.projectName} • ${t.status.replace('_', ' ')}`,
          icon: CheckSquare,
          action: () => {
            closeSearch();
            openTaskDetail(t);
          },
        });
      });

    // Filter Projects
    projects
      .filter((p) => p.name.toLowerCase().includes(q) || p.key.toLowerCase().includes(q))
      .slice(0, 4)
      .forEach((p) => {
        items.push({
          id: `proj-${p.id}`,
          type: 'project',
          item: p,
          title: p.name,
          subtitle: `Key: [${p.key}] • Progress: ${p.progress}%`,
          icon: FolderKanban,
          action: () => {
            closeSearch();
            router.push(`/projects/${p.id}`);
          },
        });
      });

    // Filter Members
    allUsers
      .filter(
        (u) =>
          u.name.toLowerCase().includes(q) ||
          u.email.toLowerCase().includes(q) ||
          u.department?.toLowerCase().includes(q)
      )
      .slice(0, 3)
      .forEach((u) => {
        items.push({
          id: `user-${u.id}`,
          type: 'member',
          item: u,
          title: u.name,
          subtitle: `${u.title || u.role} • ${u.department}`,
          icon: User,
          action: () => {
            closeSearch();
            router.push('/members');
          },
        });
      });

    // Filter Teams
    teams
      .filter((t) => t.name.toLowerCase().includes(q))
      .slice(0, 2)
      .forEach((t) => {
        items.push({
          id: `team-${t.id}`,
          type: 'team',
          item: t,
          title: t.name,
          subtitle: `${t.memberIds.length} members`,
          icon: Users2,
          action: () => {
            closeSearch();
            router.push('/teams');
          },
        });
      });

    return items;
  }, [query, tasks, projects, allUsers, teams, router, closeSearch, openCreateTask, openCreateProject, openTaskDetail]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [searchResults.length]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % (searchResults.length || 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + searchResults.length) % (searchResults.length || 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (searchResults[selectedIndex]) {
        searchResults[selectedIndex].action();
      }
    }
  };

  if (!isSearchOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 p-4 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-[#0B0D12]/85 backdrop-blur-sm transition-opacity"
        onClick={closeSearch}
      />

      {/* Palette Box */}
      <div className="relative w-full max-w-2xl bg-[#151922] border border-[#252B36] rounded-2xl shadow-2xl overflow-hidden z-10 animate-in zoom-in-95 duration-150">
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-[#252B36] gap-3">
          <Search className="w-5 h-5 text-[#8B7CFF] shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type to search tasks, projects, members, actions..."
            className="flex-1 bg-transparent text-sm text-[#F5F7FA] placeholder:text-[#929AAA]/60 focus:outline-none"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="p-1 text-[#929AAA] hover:text-[#F5F7FA] rounded cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="text-[10px] bg-[#10131A] text-[#929AAA] px-2 py-1 rounded border border-[#252B36] font-mono">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-1">
          {searchResults.length === 0 ? (
            <div className="py-12 text-center text-xs text-[#929AAA]">
              No results found for &ldquo;<span className="text-[#F5F7FA]">{query}</span>&rdquo;
            </div>
          ) : (
            searchResults.map((item, index) => {
              const isSelected = index === selectedIndex;
              const Icon = item.icon;

              return (
                <div
                  key={item.id}
                  onClick={item.action}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`flex items-center justify-between p-2.5 rounded-xl text-xs cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-[#8B7CFF]/15 text-[#F5F7FA] border border-[#8B7CFF]/30'
                      : 'text-[#929AAA] hover:bg-[#1B202C] hover:text-[#F5F7FA] border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                        isSelected
                          ? 'bg-[#8B7CFF] text-white'
                          : 'bg-[#10131A] border border-[#252B36] text-[#929AAA]'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium text-[#F5F7FA] truncate">{item.title}</p>
                      <p className="text-[11px] text-[#929AAA] truncate">{item.subtitle}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {item.type === 'task' && (
                      <TaskStatusBadge status={item.item.status} className="scale-90" />
                    )}
                    {item.type === 'member' && (
                      <Avatar user={item.item} size="xs" />
                    )}
                    <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-[#10131A] border border-[#252B36] text-[#929AAA]">
                      {item.type}
                    </span>
                    <ArrowRight className={`w-3.5 h-3.5 ${isSelected ? 'text-[#8B7CFF]' : 'text-transparent'}`} />
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 bg-[#10131A] border-t border-[#252B36] flex items-center justify-between text-[11px] text-[#929AAA]">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-[#151922] border border-[#252B36] font-mono text-[10px]">
                ↑
              </kbd>{' '}
              <kbd className="px-1.5 py-0.5 rounded bg-[#151922] border border-[#252B36] font-mono text-[10px]">
                ↓
              </kbd>{' '}
              Navigate
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-[#151922] border border-[#252B36] font-mono text-[10px]">
                ↵
              </kbd>{' '}
              Select
            </span>
          </div>
          <span>FLOWSTATE Quick Switcher</span>
        </div>
      </div>
    </div>
  );
}

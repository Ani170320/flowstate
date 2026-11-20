'use client';

import React, { useState, useMemo } from 'react';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { TaskList } from '@/components/tasks/TaskList';
import { KanbanBoard } from '@/components/tasks/KanbanBoard';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { Priority, TaskStatus } from '@/types';
import {
  CheckSquare,
  Search,
  LayoutGrid,
  List,
  Plus,
  Filter,
  CheckCircle2,
  Clock,
  AlertTriangle,
} from 'lucide-react';
import { isTaskOverdue } from '@/lib/utils';
import { isToday, isThisWeek, parseISO } from 'date-fns';

export default function MyTasksPage() {
  const { user } = useAuth();
  const { tasks, openCreateTask } = useWorkspace();

  const [viewMode, setViewMode] = useState<'list' | 'board'>('list');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'completed' | TaskStatus>('all');
  const [priorityFilter, setPriorityFilter] = useState<'all' | Priority>('all');
  const [dateFilter, setDateFilter] = useState<'all' | 'today' | 'week' | 'overdue'>('all');

  // Filter tasks assigned to currently simulated user
  const myAllTasks = useMemo(() => {
    return tasks.filter((t) => t.assigneeId === user.id);
  }, [tasks, user.id]);

  const pendingCount = myAllTasks.filter((t) => t.status !== 'done').length;
  const completedCount = myAllTasks.filter((t) => t.status === 'done').length;
  const overdueCount = myAllTasks.filter((t) => isTaskOverdue(t.dueDate, t.status)).length;

  const filteredTasks = useMemo(() => {
    let result = [...myAllTasks];

    // Search
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (t) =>
          t.title.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q) ||
          t.key?.toLowerCase().includes(q) ||
          t.projectName?.toLowerCase().includes(q)
      );
    }

    // Status filter
    if (statusFilter === 'pending') {
      result = result.filter((t) => t.status !== 'done');
    } else if (statusFilter === 'completed') {
      result = result.filter((t) => t.status === 'done');
    } else if (statusFilter !== 'all') {
      result = result.filter((t) => t.status === statusFilter);
    }

    // Priority filter
    if (priorityFilter !== 'all') {
      result = result.filter((t) => t.priority === priorityFilter);
    }

    // Due date filter
    if (dateFilter === 'today') {
      result = result.filter((t) => {
        try {
          return isToday(parseISO(t.dueDate));
        } catch {
          return false;
        }
      });
    } else if (dateFilter === 'week') {
      result = result.filter((t) => {
        try {
          return isThisWeek(parseISO(t.dueDate));
        } catch {
          return false;
        }
      });
    } else if (dateFilter === 'overdue') {
      result = result.filter((t) => isTaskOverdue(t.dueDate, t.status));
    }

    return result;
  }, [myAllTasks, search, statusFilter, priorityFilter, dateFilter]);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#252B36]">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#F5F7FA]">My Tasks</h1>
          <p className="text-xs sm:text-sm text-[#929AAA] mt-1">
            Focus list assigned to <span className="text-[#8B7CFF] font-medium">{user.name}</span>.
          </p>
        </div>

        <Button
          onClick={() => openCreateTask()}
          variant="primary"
          size="sm"
          className="gap-1.5 cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>New Task</span>
        </Button>
      </div>

      {/* Mini Metric Counters */}
      <div className="grid grid-cols-3 gap-3">
        <div
          onClick={() => setStatusFilter('pending')}
          className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
            statusFilter === 'pending'
              ? 'bg-[#8B7CFF]/15 border-[#8B7CFF]'
              : 'bg-[#151922] border-[#252B36] hover:border-[#374151]'
          }`}
        >
          <div className="flex items-center justify-between text-[#929AAA] text-xs">
            <span>Pending Tasks</span>
            <Clock className="w-3.5 h-3.5 text-[#8B7CFF]" />
          </div>
          <span className="text-xl font-bold font-mono text-[#F5F7FA] mt-1 block">
            {pendingCount}
          </span>
        </div>

        <div
          onClick={() => setStatusFilter('completed')}
          className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
            statusFilter === 'completed'
              ? 'bg-emerald-500/15 border-emerald-500'
              : 'bg-[#151922] border-[#252B36] hover:border-[#374151]'
          }`}
        >
          <div className="flex items-center justify-between text-[#929AAA] text-xs">
            <span>Completed</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <span className="text-xl font-bold font-mono text-emerald-400 mt-1 block">
            {completedCount}
          </span>
        </div>

        <div
          onClick={() => setDateFilter('overdue')}
          className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
            dateFilter === 'overdue'
              ? 'bg-red-500/15 border-red-500'
              : 'bg-[#151922] border-[#252B36] hover:border-[#374151]'
          }`}
        >
          <div className="flex items-center justify-between text-[#929AAA] text-xs">
            <span>Overdue</span>
            <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
          </div>
          <span
            className={`text-xl font-bold font-mono mt-1 block ${
              overdueCount > 0 ? 'text-red-400' : 'text-emerald-400'
            }`}
          >
            {overdueCount}
          </span>
        </div>
      </div>

      {/* Filter and View Controls Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 p-3 bg-[#10131A] border border-[#252B36] rounded-2xl">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#929AAA]" />
          <input
            type="text"
            placeholder="Search my tasks..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-9 pl-9 pr-3 bg-[#151922] border border-[#252B36] rounded-xl text-xs text-[#F5F7FA] placeholder:text-[#929AAA]/60 focus:outline-none focus:border-[#8B7CFF]"
          />
        </div>

        {/* Filter Dropdowns */}
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="h-9 px-3 bg-[#151922] border border-[#252B36] rounded-xl text-xs text-[#F5F7FA] focus:outline-none focus:border-[#8B7CFF] cursor-pointer"
          >
            <option value="all">All Statuses</option>
            <option value="pending">Active Only</option>
            <option value="completed">Completed Only</option>
            <option value="in_progress">In Progress</option>
            <option value="in_review">In Review</option>
            <option value="todo">To Do</option>
            <option value="backlog">Backlog</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value as any)}
            className="h-9 px-3 bg-[#151922] border border-[#252B36] rounded-xl text-xs text-[#F5F7FA] focus:outline-none focus:border-[#8B7CFF] cursor-pointer"
          >
            <option value="all">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <select
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value as any)}
            className="h-9 px-3 bg-[#151922] border border-[#252B36] rounded-xl text-xs text-[#F5F7FA] focus:outline-none focus:border-[#8B7CFF] cursor-pointer"
          >
            <option value="all">All Due Dates</option>
            <option value="today">Due Today</option>
            <option value="week">Due This Week</option>
            <option value="overdue">Overdue</option>
          </select>

          {/* View mode toggle */}
          <div className="flex items-center bg-[#151922] border border-[#252B36] rounded-xl p-0.5">
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-lg text-xs transition-colors cursor-pointer ${
                viewMode === 'list'
                  ? 'bg-[#8B7CFF] text-white'
                  : 'text-[#929AAA] hover:text-[#F5F7FA]'
              }`}
              title="List view"
            >
              <List className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('board')}
              className={`p-1.5 rounded-lg text-xs transition-colors cursor-pointer ${
                viewMode === 'board'
                  ? 'bg-[#8B7CFF] text-white'
                  : 'text-[#929AAA] hover:text-[#F5F7FA]'
              }`}
              title="Board view"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Task Content */}
      {filteredTasks.length === 0 ? (
        <EmptyState
          icon={CheckSquare}
          title="No tasks match your filters"
          description="Everything on your radar is organized, or clear filters to see all assigned tickets."
          actionLabel="Create Task"
          onAction={() => openCreateTask()}
        />
      ) : viewMode === 'list' ? (
        <TaskList tasks={filteredTasks} />
      ) : (
        <KanbanBoard tasks={filteredTasks} />
      )}
    </div>
  );
}

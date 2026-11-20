'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  FolderKanban,
  CheckSquare,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Clock,
  ArrowRight,
  Plus,
  Calendar,
  Sparkles,
  Circle,
  ExternalLink,
} from 'lucide-react';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { Avatar } from '@/components/ui/Avatar';
import { PriorityBadge, TaskStatusBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { formatReadableDate, formatRelativeTime, isTaskOverdue } from '@/lib/utils';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from 'recharts';

export default function DashboardPage() {
  const { user } = useAuth();
  const {
    projects,
    tasks,
    activities,
    openCreateTask,
    openCreateProject,
    openTaskDetail,
    updateTaskStatus,
  } = useWorkspace();

  const [mounted, setMounted] = useState(false);
  const [todayFormatted, setTodayFormatted] = useState('Tuesday, Nov 17, 2026');

  useEffect(() => {
    setMounted(true);
    setTodayFormatted(
      new Date().toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    );
  }, []);

  // KPI Calculations
  const activeProjectsCount = projects.filter((p) => p.status !== 'completed').length;
  const totalTasksCount = tasks.length;
  const completedTasksCount = tasks.filter((t) => t.status === 'done').length;
  const overdueTasksCount = tasks.filter(
    (t) => t.status !== 'done' && isTaskOverdue(t.dueDate, t.status)
  ).length;

  const myTasks = tasks.filter((t) => t.assigneeId === user.id && t.status !== 'done');

  // Upcoming deadlines (tasks due in next 14 days sorted by date)
  const upcomingDeadlines = [...tasks]
    .filter((t) => t.status !== 'done')
    .sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime())
    .slice(0, 5);

  // Dynamic 7-day velocity / Task completion trend chart data from real tasks
  const velocityData = React.useMemo(() => {
    const days: { day: string; completed: number; created: number }[] = [];
    const now = new Date();
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(now.getDate() - i);
      const dayLabel = d.toLocaleDateString('en-US', { weekday: 'short' });
      const dStr = d.toISOString().split('T')[0];

      const createdCount = tasks.filter((t) => {
        if (!t.createdAt) return false;
        return t.createdAt.startsWith(dStr);
      }).length;

      const completedCount = tasks.filter((t) => {
        if (t.status !== 'done' || !t.updatedAt) return false;
        return t.updatedAt.startsWith(dStr);
      }).length;

      days.push({
        day: dayLabel,
        completed: completedCount,
        created: createdCount,
      });
    }
    return days;
  }, [tasks]);

  const nextMilestone = React.useMemo(() => {
    const upcoming = [...projects, ...tasks]
      .filter((item) => item.dueDate && new Date(item.dueDate).getTime() >= new Date().setHours(0, 0, 0, 0))
      .sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime());
    return upcoming[0] ? `Next: ${formatReadableDate(upcoming[0].dueDate)}` : 'No upcoming milestones';
  }, [projects, tasks]);

  const velocitySummary = React.useMemo(() => {
    if (totalTasksCount === 0) return '0% sprint completion';
    const rate = Math.round((completedTasksCount / totalTasksCount) * 100);
    return `${rate}% sprint completion`;
  }, [totalTasksCount, completedTasksCount]);

  // Project progress breakdown for chart
  const projectChartData = projects.map((p) => {
    const pTasks = tasks.filter((t) => t.projectId === p.id);
    const pDone = pTasks.filter((t) => t.status === 'done').length;
    const calcProgress = pTasks.length > 0 ? Math.round((pDone / pTasks.length) * 100) : p.progress;
    return {
      name: p.key,
      fullName: p.name,
      progress: calcProgress,
      color: p.color || '#8B7CFF',
    };
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Welcome & Executive Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#252B36]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#F5F7FA]">
              Good morning, {user.name.split(' ')[0]}
            </h1>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono bg-[#8B7CFF]/15 text-[#8B7CFF] border border-[#8B7CFF]/30 font-semibold">
              Live State
            </span>
          </div>
          <p className="text-xs sm:text-sm text-[#929AAA] mt-1 flex items-center gap-2">
            <Calendar className="w-3.5 h-3.5 text-[#8B7CFF]" />
            <span>{todayFormatted}</span>
            <span>•</span>
            <span>You have {myTasks.length} pending tasks today</span>
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            onClick={() => openCreateProject()}
            variant="secondary"
            size="sm"
            className="cursor-pointer"
          >
            <FolderKanban className="w-3.5 h-3.5 text-[#929AAA]" />
            <span>New Project</span>
          </Button>
          <Button
            onClick={() => openCreateTask()}
            variant="primary"
            size="sm"
            className="cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Task</span>
          </Button>
        </div>
      </div>

      {/* KPI Stats 4-Card Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Active Projects */}
        <div className="bg-[#151922] border border-[#252B36] hover:border-[#374151] rounded-2xl p-4.5 transition-all">
          <div className="flex items-center justify-between text-[#929AAA] mb-2">
            <span className="text-xs font-medium">Active Projects</span>
            <div className="w-7 h-7 rounded-lg bg-indigo-500/10 text-[#8B7CFF] flex items-center justify-center">
              <FolderKanban className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-[#F5F7FA]">
              {activeProjectsCount}
            </span>
            <span className="text-xs text-[#929AAA]">/ {projects.length} total</span>
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-[11px] text-[#929AAA]">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>All roadmaps on schedule</span>
          </div>
        </div>

        {/* Total Tasks */}
        <div className="bg-[#151922] border border-[#252B36] hover:border-[#374151] rounded-2xl p-4.5 transition-all">
          <div className="flex items-center justify-between text-[#929AAA] mb-2">
            <span className="text-xs font-medium">Total Tasks</span>
            <div className="w-7 h-7 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
              <CheckSquare className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-[#F5F7FA]">{totalTasksCount}</span>
            <span className="text-xs text-blue-400 font-mono">active backlog</span>
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-[11px] text-[#929AAA]">
            <TrendingUp className="w-3.5 h-3.5 text-blue-400" />
            <span>Across 5 engineering projects</span>
          </div>
        </div>

        {/* Completed Tasks */}
        <div className="bg-[#151922] border border-[#252B36] hover:border-[#374151] rounded-2xl p-4.5 transition-all">
          <div className="flex items-center justify-between text-[#929AAA] mb-2">
            <span className="text-xs font-medium">Completed Tasks</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-emerald-400">
              {completedTasksCount}
            </span>
            <span className="text-xs text-[#929AAA]">
              ({totalTasksCount > 0 ? Math.round((completedTasksCount / totalTasksCount) * 100) : 0}%)
            </span>
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-[11px] text-emerald-400">
            <Sparkles className="w-3.5 h-3.5" />
            <span>{velocitySummary}</span>
          </div>
        </div>

        {/* Overdue Tasks */}
        <div className="bg-[#151922] border border-[#252B36] hover:border-[#374151] rounded-2xl p-4.5 transition-all">
          <div className="flex items-center justify-between text-[#929AAA] mb-2">
            <span className="text-xs font-medium">Overdue Tasks</span>
            <div className="w-7 h-7 rounded-lg bg-red-500/10 text-red-400 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span
              className={`text-3xl font-bold font-mono ${
                overdueTasksCount > 0 ? 'text-red-400' : 'text-emerald-400'
              }`}
            >
              {overdueTasksCount}
            </span>
            <span className="text-xs text-[#929AAA]">
              {overdueTasksCount > 0 ? 'action required' : 'zero blockers'}
            </span>
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-[11px] text-[#929AAA]">
            <Clock className="w-3.5 h-3.5 text-amber-400" />
            <span>{nextMilestone}</span>
          </div>
        </div>
      </div>

      {/* Charts Section: Velocity Trend & Project Progress */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Task Velocity Area Chart */}
        <div className="lg:col-span-2 bg-[#151922] border border-[#252B36] rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-[#F5F7FA]">Weekly Task Throughput</h3>
              <p className="text-xs text-[#929AAA] mt-0.5">
                Completed vs created tasks over the current cycle
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-[#8B7CFF]" />
                <span className="text-[#929AAA]">Completed</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-[#3B82F6]" />
                <span className="text-[#929AAA]">Created</span>
              </div>
            </div>
          </div>

          <div className="h-64 w-full">
            {mounted ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={velocityData}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="colorCompleted" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8B7CFF" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#8B7CFF" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorCreated" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="day"
                    stroke="#929AAA"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    stroke="#929AAA"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#10131A',
                      borderColor: '#252B36',
                      borderRadius: '10px',
                      fontSize: '12px',
                      color: '#F5F7FA',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="completed"
                    stroke="#8B7CFF"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorCompleted)"
                  />
                  <Area
                    type="monotone"
                    dataKey="created"
                    stroke="#3B82F6"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorCreated)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-[#929AAA]">
                Loading velocity charts...
              </div>
            )}
          </div>
        </div>

        {/* Project Progress Bar Chart */}
        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-[#F5F7FA]">Project Completion</h3>
              <p className="text-xs text-[#929AAA] mt-0.5">Progress by roadmap key</p>
            </div>
            <Link
              href="/projects"
              className="text-xs text-[#8B7CFF] hover:underline flex items-center gap-1"
            >
              <span>All</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="space-y-3 pt-2">
            {projectChartData.map((proj) => (
              <div key={proj.name} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-[#F5F7FA] truncate max-w-[170px]">
                    [{proj.name}] {proj.fullName}
                  </span>
                  <span className="font-mono text-[#929AAA]">{proj.progress}%</span>
                </div>
                <div className="w-full h-2 bg-[#10131A] rounded-full overflow-hidden border border-[#252B36]/60">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${proj.progress}%`,
                      backgroundColor: proj.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 3-Column Layout: My Tasks, Upcoming Deadlines, Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Column 1: My Assigned Tasks */}
        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckSquare className="w-4 h-4 text-[#8B7CFF]" />
              <h3 className="text-sm font-semibold text-[#F5F7FA]">My Active Tasks</h3>
            </div>
            <Link
              href="/my-tasks"
              className="text-xs text-[#8B7CFF] hover:underline flex items-center gap-1"
            >
              <span>View ({myTasks.length})</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="space-y-2.5">
            {myTasks.length === 0 ? (
              <div className="py-8 text-center text-xs text-[#929AAA]">
                No pending tasks assigned to you!
              </div>
            ) : (
              myTasks.slice(0, 5).map((task) => (
                <div
                  key={task.id}
                  onClick={() => openTaskDetail(task)}
                  className="flex items-start gap-2.5 p-3 rounded-xl bg-[#10131A] hover:bg-[#1A202C] border border-[#252B36] transition-colors cursor-pointer group"
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      updateTaskStatus(task.id, 'done');
                    }}
                    title="Mark as done"
                    className="mt-0.5 text-[#929AAA] hover:text-emerald-400 transition-colors"
                  >
                    <Circle className="w-4 h-4" />
                  </button>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="font-mono text-[10px] text-[#8B7CFF] font-semibold">
                        {task.key}
                      </span>
                      <PriorityBadge priority={task.priority} />
                    </div>
                    <p className="text-xs font-medium text-[#F5F7FA] group-hover:text-white line-clamp-1">
                      {task.title}
                    </p>
                    <p className="text-[10px] text-[#929AAA] mt-1 font-mono">
                      Due: {formatReadableDate(task.dueDate)}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Column 2: Upcoming Deadlines */}
        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-semibold text-[#F5F7FA]">Upcoming Deadlines</h3>
            </div>
            <Link
              href="/calendar"
              className="text-xs text-[#8B7CFF] hover:underline flex items-center gap-1"
            >
              <span>Calendar</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="space-y-2.5">
            {upcomingDeadlines.map((task) => {
              const overdue = isTaskOverdue(task.dueDate, task.status);
              return (
                <div
                  key={task.id}
                  onClick={() => openTaskDetail(task)}
                  className="flex items-center justify-between p-3 rounded-xl bg-[#10131A] hover:bg-[#1A202C] border border-[#252B36] transition-colors cursor-pointer group"
                >
                  <div className="min-w-0 flex-1 pr-2">
                    <p className="text-xs font-medium text-[#F5F7FA] truncate group-hover:text-white">
                      {task.title}
                    </p>
                    <p className="text-[11px] text-[#929AAA] mt-0.5">{task.projectName}</p>
                  </div>

                  <div className="text-right shrink-0">
                    <span
                      className={`text-xs font-mono font-medium block ${
                        overdue ? 'text-red-400 font-bold' : 'text-[#929AAA]'
                      }`}
                    >
                      {formatReadableDate(task.dueDate)}
                    </span>
                    <TaskStatusBadge status={task.status} className="scale-90 origin-right" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Column 3: Recent Activity Feed */}
        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[#F5F7FA]">Recent Activity</h3>
            <span className="text-[10px] font-mono text-[#929AAA] bg-[#10131A] px-2 py-0.5 rounded border border-[#252B36]">
              Realtime
            </span>
          </div>

          <div className="space-y-3 max-h-[360px] overflow-y-auto">
            {activities.slice(0, 6).map((act) => (
              <div
                key={act.id}
                className="flex items-start gap-2.5 pb-2.5 border-b border-[#252B36]/60 last:border-0 last:pb-0"
              >
                <Avatar user={act.user} size="xs" />
                <div className="flex-1 min-w-0 text-xs">
                  <p className="text-[#F5F7FA] leading-tight">
                    <span className="font-semibold">{act.user?.name}</span>{' '}
                    <span className="text-[#929AAA]">{act.action.replace('_', ' ')}:</span>{' '}
                    <span className="font-medium text-[#8B7CFF] truncate block">
                      {act.targetTitle}
                    </span>
                  </p>
                  <span className="text-[10px] text-[#929AAA]/70 mt-0.5 block">
                    {formatRelativeTime(act.timestamp)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { Avatar } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { isTaskOverdue } from '@/lib/utils';
import {
  BarChart,
  Bar,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  BarChart3,
  TrendingUp,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Calendar,
  Users,
  Zap,
  Download,
} from 'lucide-react';

export default function AnalyticsPage() {
  const { allUsers } = useAuth();
  const { tasks, projects } = useWorkspace();

  const [mounted, setMounted] = useState(false);
  const [timeframe, setTimeframe] = useState<'7d' | '30d' | '90d'>('30d');

  useEffect(() => {
    setMounted(true);
  }, []);

  // 1. Completion Rate Metrics
  const totalTasks = tasks.length;
  const completedTasks = tasks.filter((t) => t.status === 'done').length;
  const inProgressTasks = tasks.filter((t) => t.status === 'in_progress').length;
  const overallRate = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  // 2. Tasks by Priority
  const priorityData = useMemo(() => {
    const counts = { urgent: 0, high: 0, medium: 0, low: 0 };
    tasks.forEach((t) => counts[t.priority]++);
    return [
      { name: 'Urgent', value: counts.urgent, color: '#EF4444' },
      { name: 'High', value: counts.high, color: '#F59E0B' },
      { name: 'Medium', value: counts.medium, color: '#8B7CFF' },
      { name: 'Low', value: counts.low, color: '#6B7280' },
    ];
  }, [tasks]);

  // 3. Tasks by Status
  const statusData = useMemo(() => {
    const counts = { backlog: 0, todo: 0, in_progress: 0, in_review: 0, done: 0 };
    tasks.forEach((t) => counts[t.status]++);
    return [
      { name: 'Backlog', count: counts.backlog, color: '#6B7280' },
      { name: 'To Do', count: counts.todo, color: '#3B82F6' },
      { name: 'In Progress', count: counts.in_progress, color: '#8B7CFF' },
      { name: 'In Review', count: counts.in_review, color: '#F59E0B' },
      { name: 'Done', count: counts.done, color: '#22C55E' },
    ];
  }, [tasks]);

  // 4. Tasks Completed Over Time (Historical trend)
  const throughputTrend = useMemo(() => {
    const weeks: { period: string; completed: number; created: number; velocity: number }[] = [];
    const now = new Date();
    for (let w = 3; w >= 0; w--) {
      const end = new Date(now.getTime() - w * 7 * 86400000);
      const start = new Date(end.getTime() - 7 * 86400000);
      const label = w === 0 ? 'This Week' : `${w}w ago`;

      const created = tasks.filter((t) => {
        if (!t.createdAt) return false;
        const d = new Date(t.createdAt).getTime();
        return d >= start.getTime() && d < end.getTime();
      }).length;

      const completed = tasks.filter((t) => {
        if (t.status !== 'done' || !t.updatedAt) return false;
        const d = new Date(t.updatedAt).getTime();
        return d >= start.getTime() && d < end.getTime();
      }).length;

      const velocity = created > 0 ? Math.round((completed / created) * 100) : completed > 0 ? 100 : 0;
      weeks.push({ period: label, completed, created, velocity });
    }
    return weeks;
  }, [tasks]);

  // 5. Individual Member Performance
  const memberPerformance = useMemo(() => {
    return allUsers.map((u) => {
      const assigned = tasks.filter((t) => t.assigneeId === u.id);
      const done = assigned.filter((t) => t.status === 'done');
      const active = assigned.filter((t) => t.status !== 'done').length;
      const onTime = done.filter((t) => !isTaskOverdue(t.dueDate, t.status)).length;
      const rate = assigned.length > 0 ? Math.round((done.length / assigned.length) * 100) : 100;
      const onTimeRate = done.length > 0 ? Math.round((onTime / done.length) * 100) : 100;

      return {
        user: u,
        total: assigned.length,
        done: done.length,
        active,
        onTimeRate,
        efficiency: `${rate}%`,
      };
    });
  }, [allUsers, tasks]);

  const cycleTimeDays = useMemo(() => {
    const doneTasks = tasks.filter((t) => t.status === 'done' && t.createdAt && t.updatedAt);
    if (doneTasks.length === 0) return '0.0';
    const totalDays = doneTasks.reduce((sum, t) => {
      const diffMs = new Date(t.updatedAt).getTime() - new Date(t.createdAt).getTime();
      return sum + Math.max(0.1, diffMs / (1000 * 60 * 60 * 24));
    }, 0);
    return (totalDays / doneTasks.length).toFixed(1);
  }, [tasks]);

  const sprintVelocityPts = useMemo(() => {
    const doneHours = tasks
      .filter((t) => t.status === 'done')
      .reduce((sum, t) => sum + (t.estimatedHours || 8), 0);
    return doneHours > 0 ? doneHours : completedTasks;
  }, [tasks, completedTasks]);

  const overallOnTimeRate = useMemo(() => {
    const doneTasks = tasks.filter((t) => t.status === 'done');
    if (doneTasks.length === 0) return 100;
    const onTime = doneTasks.filter((t) => !isTaskOverdue(t.dueDate, t.status)).length;
    return Math.round((onTime / doneTasks.length) * 100);
  }, [tasks]);

  const criticalBlockers = useMemo(() => {
    return tasks.filter((t) => t.priority === 'urgent' && t.status !== 'done').length;
  }, [tasks]);

  const handleExportCSV = () => {
    if (tasks.length === 0) {
      alert('No tasks to export in this workspace.');
      return;
    }
    const headers = ['Key', 'Title', 'Project', 'Status', 'Priority', 'Assignee', 'Due Date', 'Est Hours', 'Created Date'];
    const rows = tasks.map((t) => {
      const proj = projects.find((p) => p.id === t.projectId)?.name || t.projectName || '';
      const assignee = allUsers.find((u) => u.id === t.assigneeId)?.name || 'Unassigned';
      return [
        `"${t.key || ''}"`,
        `"${(t.title || '').replace(/"/g, '""')}"`,
        `"${proj.replace(/"/g, '""')}"`,
        `"${t.status}"`,
        `"${t.priority}"`,
        `"${assignee.replace(/"/g, '""')}"`,
        `"${t.dueDate || ''}"`,
        `"${t.estimatedHours || 0}"`,
        `"${t.createdAt || ''}"`,
      ].join(',');
    });

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `flowstate_analytics_report_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#252B36]">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#F5F7FA]">Engineering Analytics</h1>
          <p className="text-xs sm:text-sm text-[#929AAA] mt-1">
            Throughput velocity, sprint health metrics, and team resource allocation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCSV}
            className="cursor-pointer gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </Button>

          <div className="flex items-center bg-[#151922] border border-[#252B36] rounded-xl p-0.5">
            <button
              onClick={() => setTimeframe('7d')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                timeframe === '7d' ? 'bg-[#8B7CFF] text-white' : 'text-[#929AAA] hover:text-[#F5F7FA]'
              }`}
            >
              Last 7d
            </button>
            <button
              onClick={() => setTimeframe('30d')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                timeframe === '30d' ? 'bg-[#8B7CFF] text-white' : 'text-[#929AAA] hover:text-[#F5F7FA]'
              }`}
            >
              Last 30d
            </button>
            <button
              onClick={() => setTimeframe('90d')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                timeframe === '90d' ? 'bg-[#8B7CFF] text-white' : 'text-[#929AAA] hover:text-[#F5F7FA]'
              }`}
            >
              Quarter Q4
            </button>
          </div>
        </div>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-4.5">
          <div className="flex items-center justify-between text-[#929AAA] mb-2">
            <span className="text-xs font-medium">Completion Rate</span>
            <TrendingUp className="w-4 h-4 text-[#8B7CFF]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-[#F5F7FA]">{overallRate}%</span>
            <span className="text-xs text-emerald-400">live</span>
          </div>
          <p className="text-[11px] text-[#929AAA] mt-2">
            {completedTasks} of {totalTasks} tickets closed
          </p>
        </div>

        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-4.5">
          <div className="flex items-center justify-between text-[#929AAA] mb-2">
            <span className="text-xs font-medium">Sprint Velocity</span>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-amber-400">{sprintVelocityPts}</span>
            <span className="text-xs text-[#929AAA]">pts completed</span>
          </div>
          <p className="text-[11px] text-[#929AAA] mt-2">Active delivery momentum</p>
        </div>

        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-4.5">
          <div className="flex items-center justify-between text-[#929AAA] mb-2">
            <span className="text-xs font-medium">Cycle Time</span>
            <Clock className="w-4 h-4 text-blue-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-blue-400">{cycleTimeDays}d</span>
            <span className="text-xs text-[#929AAA]">avg to done</span>
          </div>
          <p className="text-[11px] text-[#929AAA] mt-2">From creation to merged</p>
        </div>

        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-4.5">
          <div className="flex items-center justify-between text-[#929AAA] mb-2">
            <span className="text-xs font-medium">Team Health</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-emerald-400">{overallOnTimeRate}%</span>
            <span className="text-xs text-[#929AAA]">on-time rate</span>
          </div>
          <p className="text-[11px] text-[#929AAA] mt-2">{criticalBlockers} critical blocker(s) logged</p>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Tasks Completed Over Time */}
        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-5 space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-[#F5F7FA]">Cumulative Velocity Trend</h3>
            <p className="text-xs text-[#929AAA] mt-0.5">
              Completed deliveries vs new ticket influx
            </p>
          </div>

          <div className="h-64 w-full">
            {mounted ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={throughputTrend}>
                  <defs>
                    <linearGradient id="anlCompleted" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8B7CFF" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#8B7CFF" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="period" stroke="#929AAA" fontSize={11} tickLine={false} />
                  <YAxis stroke="#929AAA" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#10131A',
                      borderColor: '#252B36',
                      borderRadius: '10px',
                      fontSize: '12px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="completed"
                    stroke="#8B7CFF"
                    strokeWidth={2}
                    fill="url(#anlCompleted)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : null}
          </div>
        </div>

        {/* Chart 2: Tasks by Status Breakdown */}
        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-5 space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-[#F5F7FA]">Tasks by Pipeline Stage</h3>
            <p className="text-xs text-[#929AAA] mt-0.5">Current distribution across Kanban stages</p>
          </div>

          <div className="h-64 w-full">
            {mounted ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusData} layout="vertical" margin={{ left: 10, right: 10 }}>
                  <XAxis type="number" stroke="#929AAA" fontSize={11} tickLine={false} />
                  <YAxis
                    dataKey="name"
                    type="category"
                    stroke="#929AAA"
                    fontSize={11}
                    tickLine={false}
                    width={80}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#10131A',
                      borderColor: '#252B36',
                      borderRadius: '10px',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                    {statusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : null}
          </div>
        </div>
      </div>

      {/* Row 2: Priority Pie Chart + Member Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Priority Breakdown */}
        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-5 space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-[#F5F7FA]">Tasks by Priority</h3>
            <p className="text-xs text-[#929AAA] mt-0.5">Severity breakdown across all backlogs</p>
          </div>

          <div className="h-56 w-full flex items-center justify-center">
            {mounted ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={priorityData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {priorityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#10131A',
                      borderColor: '#252B36',
                      borderRadius: '10px',
                      fontSize: '12px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : null}
          </div>

          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#252B36]">
            {priorityData.map((p) => (
              <div key={p.name} className="flex items-center gap-2 text-xs">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: p.color }} />
                <span className="text-[#929AAA]">{p.name}:</span>
                <span className="font-mono font-semibold text-[#F5F7FA]">{p.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Member Performance Table */}
        <div className="lg:col-span-2 bg-[#151922] border border-[#252B36] rounded-2xl p-5 space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-[#F5F7FA]">Team Productivity & Workload</h3>
            <p className="text-xs text-[#929AAA] mt-0.5">
              Individual throughput, active burden, and on-time completion rates
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#252B36] text-[#929AAA] font-medium">
                  <th className="py-2.5 px-3">Team Member</th>
                  <th className="py-2.5 px-3 text-center">Active Load</th>
                  <th className="py-2.5 px-3 text-center">Completed</th>
                  <th className="py-2.5 px-3 text-center">On-Time %</th>
                  <th className="py-2.5 px-3 text-right">Completion</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#252B36]/60">
                {memberPerformance.slice(0, 6).map((m) => (
                  <tr key={m.user.id} className="hover:bg-[#10131A]/50">
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2.5">
                        <Avatar user={m.user} size="xs" />
                        <div>
                          <p className="font-semibold text-[#F5F7FA]">{m.user.name}</p>
                          <p className="text-[10px] text-[#929AAA]">{m.user.title}</p>
                        </div>
                      </div>
                    </td>

                    <td className="py-3 px-3 text-center font-mono">
                      <span className="bg-[#10131A] px-2 py-0.5 rounded border border-[#252B36] text-[#F5F7FA]">
                        {m.active}
                      </span>
                    </td>

                    <td className="py-3 px-3 text-center font-mono text-emerald-400 font-semibold">
                      {m.done}
                    </td>

                    <td className="py-3 px-3 text-center font-mono text-[#8B7CFF]">
                      {m.onTimeRate}%
                    </td>

                    <td className="py-3 px-3 text-right font-mono font-bold text-[#F5F7FA]">
                      {m.efficiency}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

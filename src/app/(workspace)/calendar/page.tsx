'use client';

import React, { useState, useMemo } from 'react';
import { useWorkspace } from '@/context/WorkspaceContext';
import { Button } from '@/components/ui/Button';
import { PriorityBadge } from '@/components/ui/Badge';
import { formatReadableDate } from '@/lib/utils';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Plus,
  Clock,
  Flag,
  CheckCircle2,
} from 'lucide-react';
import {
  format,
  addMonths,
  subMonths,
  addWeeks,
  subWeeks,
  startOfWeek,
  endOfWeek,
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  isSameMonth,
  isSameDay,
  isToday,
  parseISO,
} from 'date-fns';

export default function CalendarPage() {
  const { tasks, projects, openCreateTask, openTaskDetail } = useWorkspace();

  const [mounted, setMounted] = useState(false);
  const [currentDate, setCurrentDate] = useState(() => new Date());
  const [todayStr, setTodayStr] = useState(() => format(new Date(), 'yyyy-MM-dd'));
  const [viewMode, setViewMode] = useState<'month' | 'week'>('month');

  // Sync to real current date on mount in client
  React.useEffect(() => {
    setMounted(true);
    const now = new Date();
    setCurrentDate(now);
    setTodayStr(format(now, 'yyyy-MM-dd'));
  }, []);

  // Month navigation
  const nextPeriod = () => {
    if (viewMode === 'month') setCurrentDate(addMonths(currentDate, 1));
    else setCurrentDate(addWeeks(currentDate, 1));
  };

  const prevPeriod = () => {
    if (viewMode === 'month') setCurrentDate(subMonths(currentDate, 1));
    else setCurrentDate(subWeeks(currentDate, 1));
  };

  const goToToday = () => setCurrentDate(new Date());

  // Generate calendar days
  const calendarDays = useMemo(() => {
    if (viewMode === 'month') {
      const monthStart = startOfMonth(currentDate);
      const monthEnd = endOfMonth(monthStart);
      const startDate = startOfWeek(monthStart);
      const endDate = endOfWeek(monthEnd);
      return eachDayOfInterval({ start: startDate, end: endDate });
    } else {
      const weekStart = startOfWeek(currentDate);
      const weekEnd = endOfWeek(weekStart);
      return eachDayOfInterval({ start: weekStart, end: weekEnd });
    }
  }, [currentDate, viewMode]);

  // Tasks mapped by date string "yyyy-MM-dd"
  const tasksByDate = useMemo(() => {
    const map: Record<string, typeof tasks> = {};
    tasks.forEach((task) => {
      if (task.dueDate) {
        if (!map[task.dueDate]) map[task.dueDate] = [];
        map[task.dueDate].push(task);
      }
    });
    return map;
  }, [tasks]);

  // Project deadlines mapped by date string
  const projectDeadlines = useMemo(() => {
    const map: Record<string, typeof projects> = {};
    projects.forEach((proj) => {
      if (proj.dueDate) {
        if (!map[proj.dueDate]) map[proj.dueDate] = [];
        map[proj.dueDate].push(proj);
      }
    });
    return map;
  }, [projects]);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#252B36]">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#F5F7FA]">Calendar</h1>
          <p className="text-xs sm:text-sm text-[#929AAA] mt-1">
            Track release cutoffs, sprint schedules, and task delivery dates.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Month / Week switch */}
          <div className="flex items-center bg-[#151922] border border-[#252B36] rounded-xl p-0.5">
            <button
              onClick={() => setViewMode('month')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                viewMode === 'month'
                  ? 'bg-[#8B7CFF] text-white'
                  : 'text-[#929AAA] hover:text-[#F5F7FA]'
              }`}
            >
              Month
            </button>
            <button
              onClick={() => setViewMode('week')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                viewMode === 'week'
                  ? 'bg-[#8B7CFF] text-white'
                  : 'text-[#929AAA] hover:text-[#F5F7FA]'
              }`}
            >
              Week
            </button>
          </div>

          <Button
            onClick={() => openCreateTask()}
            variant="primary"
            size="sm"
            className="cursor-pointer gap-1.5"
          >
            <Plus className="w-4 h-4" />
            <span>Add Event</span>
          </Button>
        </div>
      </div>

      {/* Navigation Controls Bar */}
      <div className="flex items-center justify-between p-3 bg-[#10131A] border border-[#252B36] rounded-2xl">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={goToToday} className="cursor-pointer">
            Today
          </Button>
          <button
            onClick={prevPeriod}
            className="p-1.5 rounded-lg hover:bg-[#151922] text-[#929AAA] hover:text-[#F5F7FA] transition-colors cursor-pointer"
            aria-label="Previous month"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={nextPeriod}
            className="p-1.5 rounded-lg hover:bg-[#151922] text-[#929AAA] hover:text-[#F5F7FA] transition-colors cursor-pointer"
            aria-label="Next month"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <h2 suppressHydrationWarning className="text-base font-semibold text-[#F5F7FA]">
          {format(currentDate, viewMode === 'month' ? 'MMMM yyyy' : "'Week of' MMM d, yyyy")}
        </h2>

        <div className="flex items-center gap-3 text-xs text-[#929AAA]">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#8B7CFF]" /> Task
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400" /> Milestone
          </span>
        </div>
      </div>

      {/* Calendar Grid Container */}
      <div className="bg-[#151922] border border-[#252B36] rounded-2xl overflow-hidden shadow-sm">
        {/* Days of week header */}
        <div className="grid grid-cols-7 border-b border-[#252B36] bg-[#10131A] text-center text-xs font-semibold text-[#929AAA] py-2.5">
          <span>Sun</span>
          <span>Mon</span>
          <span>Tue</span>
          <span>Wed</span>
          <span>Thu</span>
          <span>Fri</span>
          <span>Sat</span>
        </div>

        {/* Days cells */}
        <div className="grid grid-cols-7 divide-x divide-y divide-[#252B36]">
          {calendarDays.map((day) => {
            const dateStr = format(day, 'yyyy-MM-dd');
            const isCurrentMonth = isSameMonth(day, currentDate);
            const isDayToday = dateStr === todayStr;
            const dayTasks = tasksByDate[dateStr] || [];
            const dayProjects = projectDeadlines[dateStr] || [];

            return (
              <div
                key={dateStr}
                onClick={() => openCreateTask()}
                className={`min-h-[110px] p-2 transition-colors cursor-pointer flex flex-col justify-between group ${
                  !isCurrentMonth ? 'bg-[#10131A]/40 text-[#929AAA]/40' : 'hover:bg-[#1B202C]/50'
                } ${isDayToday ? 'bg-[#8B7CFF]/5 ring-1 ring-inset ring-[#8B7CFF]/40' : ''}`}
              >
                {/* Day Header */}
                <div className="flex items-center justify-between mb-1">
                  <span
                    suppressHydrationWarning
                    className={`text-xs font-mono font-medium rounded-md w-6 h-6 flex items-center justify-center ${
                      isDayToday
                        ? 'bg-[#8B7CFF] text-white font-bold shadow-sm'
                        : isCurrentMonth
                        ? 'text-[#F5F7FA]'
                        : 'text-[#929AAA]/40'
                    }`}
                  >
                    {format(day, 'd')}
                  </span>

                  {(dayTasks.length > 0 || dayProjects.length > 0) && (
                    <span className="text-[10px] font-mono text-[#929AAA]">
                      {dayTasks.length + dayProjects.length}
                    </span>
                  )}
                </div>

                {/* Day Content: Projects & Tasks badges */}
                <div className="space-y-1 overflow-hidden flex-1">
                  {/* Project milestone */}
                  {dayProjects.map((p) => (
                    <div
                      key={p.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        window.location.href = `/projects/${p.id}`;
                      }}
                      className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30 truncate flex items-center gap-1 cursor-pointer hover:bg-amber-500/25"
                      title={`Project Deadline: ${p.name}`}
                    >
                      <Flag className="w-2.5 h-2.5 shrink-0" />
                      <span className="truncate">{p.name}</span>
                    </div>
                  ))}

                  {/* Tasks on this day */}
                  {dayTasks.slice(0, 3).map((task) => (
                    <div
                      key={task.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        openTaskDetail(task);
                      }}
                      className={`px-1.5 py-0.5 rounded text-[10px] truncate flex items-center gap-1 cursor-pointer transition-colors ${
                        task.status === 'done'
                          ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-900/40 line-through opacity-70'
                          : 'bg-[#10131A] text-[#F5F7FA] border border-[#252B36] hover:border-[#8B7CFF]'
                      }`}
                      title={`${task.key}: ${task.title}`}
                    >
                      <span
                        className="w-1.5 h-1.5 rounded-full shrink-0"
                        style={{
                          backgroundColor: task.priority === 'urgent' ? '#EF4444' : '#8B7CFF',
                        }}
                      />
                      <span className="truncate">{task.title}</span>
                    </div>
                  ))}

                  {dayTasks.length > 3 && (
                    <span className="text-[9px] text-[#929AAA] block pl-1">
                      +{dayTasks.length - 3} more
                    </span>
                  )}
                </div>

                {/* Hover Add Task Hint */}
                <div className="opacity-0 group-hover:opacity-100 text-[10px] text-[#8B7CFF] flex items-center gap-0.5 pt-1 transition-opacity">
                  <Plus className="w-3 h-3" />
                  <span>Add</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

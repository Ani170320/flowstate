'use client';

import React from 'react';
import { Project, Task, Activity } from '@/types';
import { Avatar } from '@/components/ui/Avatar';
import { PriorityBadge, ProjectStatusBadge, TaskStatusBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { formatReadableDate, formatRelativeTime, isTaskOverdue } from '@/lib/utils';
import {
  Calendar,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Users2,
  DollarSign,
  TrendingUp,
  Activity as ActivityIcon,
  Plus,
} from 'lucide-react';
import { useWorkspace } from '@/context/WorkspaceContext';

interface ProjectOverviewTabProps {
  project: Project;
  tasks: Task[];
  activities: Activity[];
}

export function ProjectOverviewTab({ project, tasks, activities }: ProjectOverviewTabProps) {
  const { openCreateTask } = useWorkspace();

  const totalTasks = tasks.length;
  const doneTasks = tasks.filter((t) => t.status === 'done').length;
  const inProgressTasks = tasks.filter((t) => t.status === 'in_progress').length;
  const overdueTasks = tasks.filter(
    (t) => isTaskOverdue(t.dueDate, t.status)
  ).length;

  const progress = totalTasks > 0 ? Math.round((doneTasks / totalTasks) * 100) : project.progress;

  return (
    <div className="space-y-6">
      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-4">
          <div className="flex items-center justify-between text-[#929AAA] mb-2">
            <span className="text-xs font-medium">Completion Rate</span>
            <TrendingUp className="w-4 h-4 text-[#8B7CFF]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-[#F5F7FA]">{progress}%</span>
            <span className="text-xs text-[#929AAA]">
              {doneTasks}/{totalTasks} tasks
            </span>
          </div>
          <div className="w-full h-1.5 bg-[#10131A] rounded-full overflow-hidden mt-3">
            <div
              className="h-full bg-[#8B7CFF] rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-4">
          <div className="flex items-center justify-between text-[#929AAA] mb-2">
            <span className="text-xs font-medium">In Progress</span>
            <Clock className="w-4 h-4 text-blue-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-blue-400">{inProgressTasks}</span>
            <span className="text-xs text-[#929AAA]">active sprint items</span>
          </div>
          <span className="inline-block mt-3 text-[10px] text-blue-400 font-mono bg-blue-500/10 px-2 py-0.5 rounded">
            Engineering Velocity
          </span>
        </div>

        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-4">
          <div className="flex items-center justify-between text-[#929AAA] mb-2">
            <span className="text-xs font-medium">Overdue Tasks</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-bold font-mono ${overdueTasks > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
              {overdueTasks}
            </span>
            <span className="text-xs text-[#929AAA]">need attention</span>
          </div>
          <span className="inline-block mt-3 text-[10px] text-[#929AAA] font-mono bg-[#10131A] px-2 py-0.5 rounded border border-[#252B36]">
            Target: 0 blockers
          </span>
        </div>

        <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-4">
          <div className="flex items-center justify-between text-[#929AAA] mb-2">
            <span className="text-xs font-medium">Budget Spent</span>
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-[#F5F7FA]">
              ${((project.spent || 0) / 1000).toFixed(1)}k
            </span>
            <span className="text-xs text-[#929AAA]">
              of ${((project.budget || 50000) / 1000).toFixed(0)}k
            </span>
          </div>
          <div className="w-full h-1.5 bg-[#10131A] rounded-full overflow-hidden mt-3">
            <div
              className="h-full bg-emerald-400 rounded-full"
              style={{
                width: `${Math.min(100, Math.round(((project.spent || 0) / (project.budget || 50000)) * 100))}%`,
              }}
            />
          </div>
        </div>
      </div>

      {/* Main 2-column info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Description & Assigned Members */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description Card */}
          <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-5 space-y-3">
            <h3 className="text-sm font-semibold text-[#F5F7FA] tracking-tight">About Project</h3>
            <p className="text-xs sm:text-sm text-[#929AAA] leading-relaxed">
              {project.description}
            </p>

            <div className="pt-3 border-t border-[#252B36] flex flex-wrap items-center gap-6 text-xs text-[#929AAA]">
              <div>
                <span className="block text-[10px] uppercase font-mono text-[#929AAA]/70 mb-0.5">
                  Timeline
                </span>
                <span className="font-mono text-[#F5F7FA]">
                  {formatReadableDate(project.startDate)} &rarr; {formatReadableDate(project.dueDate)}
                </span>
              </div>
              <div>
                <span className="block text-[10px] uppercase font-mono text-[#929AAA]/70 mb-0.5">
                  Lead
                </span>
                <span className="text-[#F5F7FA] font-medium">
                  {project.manager?.name || 'Unassigned'}
                </span>
              </div>
              <div>
                <span className="block text-[10px] uppercase font-mono text-[#929AAA]/70 mb-0.5">
                  Status
                </span>
                <ProjectStatusBadge status={project.status} />
              </div>
            </div>
          </div>

          {/* Team Members Roster */}
          <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users2 className="w-4 h-4 text-[#8B7CFF]" />
                <h3 className="text-sm font-semibold text-[#F5F7FA]">
                  Assigned Team ({project.teamMembers?.length || 0})
                </h3>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {(project.teamMembers || []).map((member) => (
                <div
                  key={member.id}
                  className="flex items-center gap-3 p-3 bg-[#10131A] border border-[#252B36] rounded-xl hover:border-[#374151] transition-colors"
                >
                  <Avatar user={member} size="sm" showStatus />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-[#F5F7FA] truncate">{member.name}</p>
                    <p className="text-[10px] text-[#929AAA] truncate">{member.title || member.role}</p>
                  </div>
                  <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-[#151922] text-[#8B7CFF] border border-[#252B36] uppercase">
                    {member.department || 'Eng'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Project Audit Activity Log */}
        <div className="space-y-6">
          <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-5 space-y-4">
            <div className="flex items-center gap-2">
              <ActivityIcon className="w-4 h-4 text-[#8B7CFF]" />
              <h3 className="text-sm font-semibold text-[#F5F7FA]">Project Activity</h3>
            </div>

            <div className="space-y-3 max-h-[380px] overflow-y-auto">
              {activities.length === 0 ? (
                <p className="text-xs text-[#929AAA]">No recent activities logged.</p>
              ) : (
                activities.map((act) => (
                  <div
                    key={act.id}
                    className="flex items-start gap-3 text-xs pb-3 border-b border-[#252B36]/60 last:border-0 last:pb-0"
                  >
                    <Avatar user={act.user} size="xs" />
                    <div className="flex-1 min-w-0">
                      <p className="text-[#F5F7FA] font-medium leading-tight">
                        {act.user?.name}{' '}
                        <span className="text-[#929AAA] font-normal">
                          {act.action.replace('_', ' ')}:
                        </span>{' '}
                        {act.targetTitle}
                      </p>
                      {act.details && (
                        <p className="text-[11px] text-[#929AAA] mt-0.5">{act.details}</p>
                      )}
                      <span className="text-[10px] text-[#929AAA]/70 mt-1 block">
                        {formatRelativeTime(act.timestamp)}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

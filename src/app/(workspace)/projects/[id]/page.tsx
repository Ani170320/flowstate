'use client';

import React, { useState, use, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useWorkspace } from '@/context/WorkspaceContext';
import { ProjectOverviewTab } from '@/components/projects/ProjectOverviewTab';
import { ProjectFilesTab } from '@/components/projects/ProjectFilesTab';
import { KanbanBoard } from '@/components/tasks/KanbanBoard';
import { TaskList } from '@/components/tasks/TaskList';
import { ProjectStatusBadge, PriorityBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Tabs, TabItem } from '@/components/ui/Tabs';
import { formatReadableDate } from '@/lib/utils';
import {
  FolderKanban,
  Kanban,
  List,
  Activity,
  Files,
  Plus,
  ArrowLeft,
  Calendar,
  Settings,
  Edit2,
  Trash2,
} from 'lucide-react';

function ProjectDetailContent({ projectId }: { projectId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const { projects, tasks, activities, isLoading, openCreateTask, openCreateProject, deleteProject } =
    useWorkspace();

  const project = projects.find((p) => p.id === projectId);
  const projectTasks = tasks.filter((t) => t.projectId === projectId);
  const projectActivities = activities.filter((a) => a.projectId === projectId);

  const initialTab = searchParams.get('tab') || 'overview';
  const [activeTab, setActiveTab] = useState(initialTab);

  if (isLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <div className="w-8 h-8 rounded-full border-2 border-[var(--accent)] border-t-transparent animate-spin" />
        <p className="text-xs text-[#929AAA]">Loading project details...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="py-20 text-center space-y-4">
        <h2 className="text-xl font-bold text-[#F5F7FA]">Project not found</h2>
        <p className="text-sm text-[#929AAA]">
          The project with ID &quot;{projectId}&quot; does not exist or may have been deleted.
        </p>
        <Link href="/projects">
          <Button variant="secondary" size="sm">
            &larr; Back to Projects
          </Button>
        </Link>
      </div>
    );
  }

  const tabs: TabItem[] = [
    { id: 'overview', label: 'Overview', icon: <FolderKanban className="w-4 h-4" /> },
    {
      id: 'board',
      label: 'Board',
      count: projectTasks.length,
      icon: <Kanban className="w-4 h-4" />,
    },
    {
      id: 'list',
      label: 'List',
      count: projectTasks.length,
      icon: <List className="w-4 h-4" />,
    },
    {
      id: 'activity',
      label: 'Activity',
      count: projectActivities.length,
      icon: <Activity className="w-4 h-4" />,
    },
    { id: 'files', label: 'Files', icon: <Files className="w-4 h-4" /> },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Back button & Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          href="/projects"
          className="inline-flex items-center gap-1.5 text-xs text-[#929AAA] hover:text-[#F5F7FA] transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Projects</span>
        </Link>

        <div className="flex items-center gap-2">
          <Button
            size="xs"
            variant="outline"
            onClick={() => openCreateProject(project)}
            className="gap-1.5 cursor-pointer"
          >
            <Edit2 className="w-3.5 h-3.5" />
            <span>Edit Project</span>
          </Button>
          <Button
            size="xs"
            variant="primary"
            onClick={() => openCreateTask(project.id)}
            className="gap-1.5 cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Task</span>
          </Button>
        </div>
      </div>

      {/* Project Banner / Header */}
      <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2.5">
              <span
                className="w-3.5 h-3.5 rounded-full ring-2 ring-offset-2 ring-offset-[#151922]"
                style={{ backgroundColor: project.color || '#8B7CFF' }}
              />
              <span className="font-mono text-xs font-bold text-[#8B7CFF] bg-[#8B7CFF]/15 px-2 py-0.5 rounded border border-[#8B7CFF]/25">
                {project.key}
              </span>
              <ProjectStatusBadge status={project.status} />
              <PriorityBadge priority={project.priority} />
            </div>

            <h1 className="text-2xl sm:text-3xl font-bold text-[#F5F7FA] tracking-tight">
              {project.name}
            </h1>

            <p className="text-xs sm:text-sm text-[#929AAA] max-w-2xl leading-relaxed">
              {project.description}
            </p>
          </div>

          {/* Quick Metrics */}
          <div className="flex sm:flex-col items-end justify-between sm:justify-center border-t sm:border-t-0 sm:border-l border-[#252B36] pt-3 sm:pt-0 sm:pl-6 gap-2 shrink-0">
            <div className="text-right">
              <span className="text-[10px] text-[#929AAA] uppercase font-mono block">
                Target Deadline
              </span>
              <span className="text-xs font-mono font-medium text-[#F5F7FA] flex items-center gap-1 mt-0.5">
                <Calendar className="w-3.5 h-3.5 text-[#8B7CFF]" />
                {formatReadableDate(project.dueDate)}
              </span>
            </div>
            <div className="text-right">
              <span className="text-[10px] text-[#929AAA] uppercase font-mono block">
                Progress
              </span>
              <span className="text-base font-bold font-mono text-emerald-400">
                {project.progress}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* Tab Panels */}
      <div>
        {activeTab === 'overview' && (
          <ProjectOverviewTab
            project={project}
            tasks={projectTasks}
            activities={projectActivities}
          />
        )}

        {activeTab === 'board' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-xs text-[#929AAA]">
                Drag and drop task cards across status stages. Click any card to edit details.
              </p>
              <Button size="xs" variant="primary" onClick={() => openCreateTask(project.id)}>
                <Plus className="w-3.5 h-3.5 mr-1" />
                New Task
              </Button>
            </div>
            <KanbanBoard projectId={project.id} />
          </div>
        )}

        {activeTab === 'list' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-xs text-[#929AAA]">
                Tabular sprint view. Click headers to inspect or edit inline.
              </p>
              <Button size="xs" variant="primary" onClick={() => openCreateTask(project.id)}>
                <Plus className="w-3.5 h-3.5 mr-1" />
                New Task
              </Button>
            </div>
            <TaskList tasks={projectTasks} />
          </div>
        )}

        {activeTab === 'activity' && (
          <div className="bg-[#151922] border border-[#252B36] rounded-2xl p-6 space-y-4">
            <h3 className="text-sm font-semibold text-[#F5F7FA]">Project Activity History</h3>
            <div className="space-y-4">
              {projectActivities.length === 0 ? (
                <p className="text-xs text-[#929AAA]">No activity recorded for this project yet.</p>
              ) : (
                projectActivities.map((act) => (
                  <div key={act.id} className="flex items-start gap-3 text-xs pb-3 border-b border-[#252B36]/60 last:border-0">
                    <span className="w-2 h-2 rounded-full bg-[#8B7CFF] mt-1.5 shrink-0" />
                    <div>
                      <p className="text-[#F5F7FA] font-medium">
                        {act.user?.name || 'Member'}{' '}
                        <span className="text-[#929AAA]">{act.action.replace('_', ' ')}:</span>{' '}
                        {act.targetTitle}
                      </p>
                      {act.details && <p className="text-[#929AAA] mt-0.5">{act.details}</p>}
                      <span className="text-[10px] text-[#929AAA]/70 mt-1 block">
                        {new Date(act.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {activeTab === 'files' && <ProjectFilesTab projectId={project.id} />}
      </div>
    </div>
  );
}

export default function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  return (
    <Suspense fallback={<div className="py-20 text-center text-xs text-[#929AAA]">Loading workspace...</div>}>
      <ProjectDetailContent projectId={resolvedParams.id} />
    </Suspense>
  );
}

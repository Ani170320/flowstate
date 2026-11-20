'use client';

import React from 'react';
import Link from 'next/link';
import { Project } from '@/types';
import { ProjectStatusBadge, PriorityBadge } from '@/components/ui/Badge';
import { Avatar, AvatarGroup } from '@/components/ui/Avatar';
import { useWorkspace } from '@/context/WorkspaceContext';
import { formatReadableDate } from '@/lib/utils';
import { Calendar, MoreVertical, Edit2, Trash2, ArrowUpRight } from 'lucide-react';

interface ProjectCardProps {
  project: Project;
}

export function ProjectCard({ project }: ProjectCardProps) {
  const { openCreateProject, deleteProject, tasks } = useWorkspace();
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);

  const projectTasks = tasks.filter((t) => t.projectId === project.id);
  const completedTasks = projectTasks.filter((t) => t.status === 'done').length;
  const totalTasks = projectTasks.length;
  const calculatedProgress =
    totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : project.progress;

  const handleDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsMenuOpen(false);
    if (confirm(`Are you sure you want to delete project "${project.name}"?`)) {
      deleteProject(project.id);
    }
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsMenuOpen(false);
    openCreateProject(project);
  };

  return (
    <div className="group relative bg-[#151922] border border-[#252B36] hover:border-[#374151] rounded-2xl p-5 transition-all duration-200 flex flex-col justify-between shadow-sm hover:shadow-lg">
      <div>
        {/* Top bar: Key + Color, Status, Menu */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <span
              className="w-3 h-3 rounded-full shrink-0"
              style={{ backgroundColor: project.color || '#8B7CFF' }}
            />
            <span className="font-mono text-xs font-bold text-[#8B7CFF] bg-[#8B7CFF]/10 px-2 py-0.5 rounded border border-[#8B7CFF]/25">
              {project.key}
            </span>
          </div>

          <div className="flex items-center gap-1.5 relative">
            <ProjectStatusBadge status={project.status} />

            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setIsMenuOpen(!isMenuOpen);
              }}
              className="text-[#929AAA] hover:text-[#F5F7FA] p-1 rounded-md hover:bg-[#1B202C] transition-colors cursor-pointer"
            >
              <MoreVertical className="w-4 h-4" />
            </button>

            {isMenuOpen && (
              <div className="absolute right-0 top-full mt-1 w-32 bg-[#10131A] border border-[#252B36] rounded-xl shadow-2xl py-1 z-30 animate-in fade-in zoom-in-95 duration-100">
                <button
                  onClick={handleEdit}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-[#F5F7FA] hover:bg-[#1B202C] transition-colors text-left cursor-pointer"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                  <span>Edit</span>
                </button>
                <button
                  onClick={handleDelete}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/10 transition-colors text-left cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Delete</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Project Name & Description */}
        <Link href={`/projects/${project.id}`} className="block group-hover:text-white">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-base font-semibold text-[#F5F7FA] tracking-tight group-hover:text-white transition-colors line-clamp-1">
              {project.name}
            </h3>
            <ArrowUpRight className="w-4 h-4 text-[#929AAA] opacity-0 group-hover:opacity-100 group-hover:text-[#8B7CFF] transition-all shrink-0" />
          </div>
          <p className="text-xs text-[#929AAA] mt-1.5 line-clamp-2 leading-relaxed">
            {project.description}
          </p>
        </Link>

        {/* Tags */}
        {(project.tags || []).length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap mt-3">
            {project.tags?.map((t, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded text-[10px] font-medium bg-[#10131A] text-[#929AAA] border border-[#252B36]"
              >
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Progress & Team members Footer */}
      <div className="mt-5 pt-4 border-t border-[#252B36]/80 space-y-3">
        {/* Progress bar */}
        <div>
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="text-[#929AAA]">
              Tasks: {completedTasks}/{totalTasks}
            </span>
            <span className="font-mono font-medium text-[#F5F7FA]">{calculatedProgress}%</span>
          </div>
          <div className="w-full h-1.5 bg-[#10131A] rounded-full overflow-hidden border border-[#252B36]">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${calculatedProgress}%`,
                backgroundColor: project.color || '#8B7CFF',
              }}
            />
          </div>
        </div>

        {/* Team Avatars & Due Date */}
        <div className="flex items-center justify-between text-xs pt-1">
          <AvatarGroup users={project.teamMembers || []} max={3} size="xs" />

          <div className="flex items-center gap-1.5 font-mono text-[11px] text-[#929AAA]">
            <Calendar className="w-3.5 h-3.5" />
            <span>{formatReadableDate(project.dueDate)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

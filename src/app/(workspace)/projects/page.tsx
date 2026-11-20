'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { Project, ProjectStatus } from '@/types';
import { useWorkspace } from '@/context/WorkspaceContext';
import { ProjectCard } from '@/components/projects/ProjectCard';
import { ProjectStatusBadge, PriorityBadge } from '@/components/ui/Badge';
import { Avatar, AvatarGroup } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { formatReadableDate } from '@/lib/utils';
import {
  FolderKanban,
  Search,
  LayoutGrid,
  List,
  Plus,
  SlidersHorizontal,
  ArrowUpDown,
  MoreVertical,
  Edit2,
  Trash2,
  ArrowRight,
  Download,
} from 'lucide-react';

export default function ProjectsPage() {
  const { projects, openCreateProject, deleteProject } = useWorkspace();

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'deadline' | 'created' | 'progress'>('deadline');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const filteredProjects = useMemo(() => {
    let result = [...projects];

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q) ||
          p.key.toLowerCase().includes(q)
      );
    }

    if (statusFilter !== 'all') {
      result = result.filter((p) => p.status === statusFilter);
    }

    result.sort((a, b) => {
      if (sortBy === 'deadline') {
        const diff = new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime();
        return sortOrder === 'asc' ? diff : -diff;
      }
      if (sortBy === 'created') {
        const diff = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        return sortOrder === 'asc' ? diff : -diff;
      }
      if (sortBy === 'progress') {
        const diff = a.progress - b.progress;
        return sortOrder === 'asc' ? diff : -diff;
      }
      return 0;
    });

    return result;
  }, [projects, search, statusFilter, sortBy, sortOrder]);

  const handleExportCSV = () => {
    if (projects.length === 0) {
      alert('No projects to export in this workspace.');
      return;
    }
    const headers = ['Key', 'Name', 'Description', 'Status', 'Priority', 'Progress (%)', 'Start Date', 'Due Date', 'Budget', 'Spent'];
    const rows = filteredProjects.map((p) => [
      `"${p.key}"`,
      `"${p.name.replace(/"/g, '""')}"`,
      `"${(p.description || '').replace(/"/g, '""')}"`,
      `"${p.status}"`,
      `"${p.priority}"`,
      `"${p.progress}"`,
      `"${p.startDate || ''}"`,
      `"${p.dueDate || ''}"`,
      `"${p.budget || 0}"`,
      `"${p.spent || 0}"`,
    ].join(','));

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `flowstate_projects_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#252B36]">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#F5F7FA]">Projects</h1>
          <p className="text-xs sm:text-sm text-[#929AAA] mt-1">
            Manage engineering initiatives, design sprint roadmaps, and delivery milestones.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={handleExportCSV}
            variant="outline"
            size="sm"
            className="cursor-pointer gap-1.5"
          >
            <Download className="w-4 h-4" />
            <span>Export CSV</span>
          </Button>

          <Button
            onClick={() => openCreateProject()}
            variant="primary"
            size="sm"
            className="cursor-pointer gap-1.5"
          >
            <Plus className="w-4 h-4" />
            <span>New Project</span>
          </Button>
        </div>
      </div>

      {/* Filter and View Controls Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 p-3 bg-[#10131A] border border-[#252B36] rounded-2xl">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#929AAA]" />
          <input
            type="text"
            placeholder="Search projects by name, key or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-9 pl-9 pr-3 bg-[#151922] border border-[#252B36] rounded-xl text-xs text-[#F5F7FA] placeholder:text-[#929AAA]/60 focus:outline-none focus:border-[#8B7CFF]"
          />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 px-3 bg-[#151922] border border-[#252B36] rounded-xl text-xs text-[#F5F7FA] focus:outline-none focus:border-[#8B7CFF] cursor-pointer"
          >
            <option value="all">All Statuses</option>
            <option value="planning">Planning</option>
            <option value="in_progress">In Progress</option>
            <option value="in_review">In Review</option>
            <option value="completed">Completed</option>
            <option value="on_hold">On Hold</option>
          </select>

          <select
            value={`${sortBy}-${sortOrder}`}
            onChange={(e) => {
              const [sb, so] = e.target.value.split('-') as [any, any];
              setSortBy(sb);
              setSortOrder(so);
            }}
            className="h-9 px-3 bg-[#151922] border border-[#252B36] rounded-xl text-xs text-[#F5F7FA] focus:outline-none focus:border-[#8B7CFF] cursor-pointer"
          >
            <option value="deadline-asc">Deadline: Soonest</option>
            <option value="deadline-desc">Deadline: Furthest</option>
            <option value="created-desc">Newest Created</option>
            <option value="progress-desc">Highest Progress</option>
          </select>

          {/* View Mode Toggle */}
          <div className="flex items-center bg-[#151922] border border-[#252B36] rounded-xl p-0.5">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-lg text-xs transition-colors cursor-pointer ${
                viewMode === 'grid'
                  ? 'bg-[#8B7CFF] text-white'
                  : 'text-[#929AAA] hover:text-[#F5F7FA]'
              }`}
              title="Grid view"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
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
          </div>
        </div>
      </div>

      {/* Projects Display */}
      {filteredProjects.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title="No projects found"
          description="Try adjusting your search query or status filters, or start a new initiative."
          actionLabel="Create Project"
          onAction={() => openCreateProject()}
        />
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredProjects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      ) : (
        /* List / Table View */
        <div className="bg-[#151922] border border-[#252B36] rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[#252B36] bg-[#10131A] text-[#929AAA] font-medium">
                  <th className="py-3 px-4 w-24">Key</th>
                  <th className="py-3 px-4">Project Name</th>
                  <th className="py-3 px-4 w-32">Status</th>
                  <th className="py-3 px-4 w-28">Priority</th>
                  <th className="py-3 px-4 w-36">Progress</th>
                  <th className="py-3 px-4 w-32">Due Date</th>
                  <th className="py-3 px-4 w-36">Team</th>
                  <th className="py-3 px-4 w-12 text-right"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#252B36]/60">
                {filteredProjects.map((p) => (
                  <tr
                    key={p.id}
                    className="hover:bg-[#10131A]/60 transition-colors group cursor-pointer"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-[#8B7CFF]">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: p.color || '#8B7CFF' }}
                        />
                        <span>{p.key}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-semibold text-[#F5F7FA]">
                      <Link
                        href={`/projects/${p.id}`}
                        className="hover:text-[#8B7CFF] transition-colors"
                      >
                        {p.name}
                      </Link>
                    </td>

                    <td className="py-3.5 px-4">
                      <ProjectStatusBadge status={p.status} />
                    </td>

                    <td className="py-3.5 px-4">
                      <PriorityBadge priority={p.priority} />
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="space-y-1">
                        <div className="flex justify-between text-[11px] font-mono">
                          <span>{p.progress}%</span>
                        </div>
                        <div className="w-24 h-1.5 bg-[#10131A] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[#8B7CFF] rounded-full"
                            style={{ width: `${p.progress}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-[#929AAA] font-mono">
                      {formatReadableDate(p.dueDate)}
                    </td>

                    <td className="py-3.5 px-4">
                      <AvatarGroup users={p.teamMembers || []} max={3} size="xs" />
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <Link
                        href={`/projects/${p.id}`}
                        className="text-[#929AAA] hover:text-[#8B7CFF] p-1 inline-block"
                      >
                        <ArrowRight className="w-4 h-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

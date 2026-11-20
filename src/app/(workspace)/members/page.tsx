'use client';

import React, { useState, useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useToast } from '@/context/ToastContext';
import { User, Role } from '@/types';
import { memberService } from '@/services/memberService';
import { Avatar } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { PriorityBadge, TaskStatusBadge } from '@/components/ui/Badge';
import {
  UserCheck,
  Search,
  UserPlus,
  Mail,
  Phone,
  Calendar,
  CheckSquare,
  FolderKanban,
  Shield,
  Briefcase,
  MapPin,
} from 'lucide-react';
import { formatReadableDate } from '@/lib/utils';

export default function MembersPage() {
  const { allUsers, refreshMembers } = useAuth();
  const { tasks, projects, refreshData } = useWorkspace();
  const { success } = useToast();

  const [search, setSearch] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('all');
  const [selectedMember, setSelectedMember] = useState<User | null>(null);
  const [isInviteOpen, setIsInviteOpen] = useState(false);

  // Invite Form state
  const [inviteName, setInviteName] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<Role>('developer');
  const [inviteDept, setInviteDept] = useState('Engineering');
  const [inviteTitle, setInviteTitle] = useState('Software Engineer');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const departments = useMemo(() => {
    const set = new Set<string>();
    allUsers.forEach((u) => {
      if (u.department) set.add(u.department);
    });
    return Array.from(set);
  }, [allUsers]);

  const filteredMembers = useMemo(() => {
    let result = [...allUsers];

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (u) =>
          u.name.toLowerCase().includes(q) ||
          u.email.toLowerCase().includes(q) ||
          u.title?.toLowerCase().includes(q) ||
          u.department?.toLowerCase().includes(q)
      );
    }

    if (departmentFilter !== 'all') {
      result = result.filter((u) => u.department === departmentFilter);
    }

    return result;
  }, [allUsers, search, departmentFilter]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteName.trim() || !inviteEmail.trim()) return;

    setIsSubmitting(true);
    try {
      await memberService.inviteMember({
        name: inviteName.trim(),
        email: inviteEmail.trim(),
        role: inviteRole,
        department: inviteDept,
        title: inviteTitle,
      });

      await refreshMembers();
      await refreshData();
      setIsInviteOpen(false);
      setInviteName('');
      setInviteEmail('');
      success('Invitation Sent', `Invited ${inviteName} to FLOWSTATE workspace.`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#252B36]">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#F5F7FA]">Members Directory</h1>
          <p className="text-xs sm:text-sm text-[#929AAA] mt-1">
            Manage organization teammates, permissions, workload, and assigned deliverables.
          </p>
        </div>

        <Button
          onClick={() => setIsInviteOpen(true)}
          variant="primary"
          size="sm"
          className="gap-1.5 cursor-pointer"
        >
          <UserPlus className="w-4 h-4" />
          <span>Invite Member</span>
        </Button>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 bg-[#10131A] border border-[#252B36] rounded-2xl">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#929AAA]" />
          <input
            type="text"
            placeholder="Search by name, email, department..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-9 pl-9 pr-3 bg-[#151922] border border-[#252B36] rounded-xl text-xs text-[#F5F7FA] placeholder:text-[#929AAA]/60 focus:outline-none focus:border-[#8B7CFF]"
          />
        </div>

        <select
          value={departmentFilter}
          onChange={(e) => setDepartmentFilter(e.target.value)}
          className="h-9 px-3 bg-[#151922] border border-[#252B36] rounded-xl text-xs text-[#F5F7FA] focus:outline-none focus:border-[#8B7CFF] cursor-pointer"
        >
          <option value="all">All Departments</option>
          {departments.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </div>

      {/* Members Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {filteredMembers.map((member) => {
          const assignedTasks = tasks.filter((t) => t.assigneeId === member.id);
          const activeTasksCount = assignedTasks.filter((t) => t.status !== 'done').length;
          const memberProjects = projects.filter((p) => p.teamMemberIds?.includes(member.id));

          return (
            <div
              key={member.id}
              onClick={() => setSelectedMember(member)}
              className="bg-[#151922] border border-[#252B36] hover:border-[#374151] rounded-2xl p-5 transition-all flex flex-col justify-between cursor-pointer group shadow-sm hover:shadow-lg"
            >
              <div className="flex flex-col items-center text-center">
                <Avatar user={member} size="lg" showStatus className="mb-3" />

                <h3 className="text-sm font-semibold text-[#F5F7FA] group-hover:text-white transition-colors">
                  {member.name}
                </h3>
                <p className="text-xs text-[#929AAA] mt-0.5 line-clamp-1">{member.title}</p>

                <div className="flex items-center gap-1.5 mt-2.5">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-[#10131A] text-[#8B7CFF] border border-[#252B36]">
                    {member.department || 'Eng'}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-[#8B7CFF]/15 text-[#8B7CFF] font-semibold">
                    {member.role}
                  </span>
                </div>
              </div>

              {/* Stats Footer */}
              <div className="mt-5 pt-4 border-t border-[#252B36]/80 grid grid-cols-2 gap-2 text-center text-xs">
                <div className="bg-[#10131A] p-2 rounded-xl border border-[#252B36]/60">
                  <span className="text-[10px] text-[#929AAA] block">Active Tasks</span>
                  <span className="font-bold font-mono text-[#F5F7FA]">{activeTasksCount}</span>
                </div>
                <div className="bg-[#10131A] p-2 rounded-xl border border-[#252B36]/60">
                  <span className="text-[10px] text-[#929AAA] block">Projects</span>
                  <span className="font-bold font-mono text-[#F5F7FA]">
                    {memberProjects.length}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Member Profile Drawer / Modal */}
      {selectedMember && (
        <Modal
          isOpen={Boolean(selectedMember)}
          onClose={() => setSelectedMember(null)}
          title="Team Member Profile"
          maxWidth="2xl"
        >
          <div className="space-y-6">
            {/* Top Info */}
            <div className="flex items-center gap-4 p-4 bg-[#10131A] rounded-2xl border border-[#252B36]">
              <Avatar user={selectedMember} size="xl" showStatus />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold text-[#F5F7FA]">{selectedMember.name}</h3>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-[#8B7CFF]/20 text-[#8B7CFF] font-bold">
                    {selectedMember.role}
                  </span>
                </div>
                <p className="text-xs text-[#929AAA] mt-0.5">{selectedMember.title}</p>
                <div className="flex items-center gap-4 mt-2 text-xs text-[#929AAA]">
                  <span className="flex items-center gap-1">
                    <Mail className="w-3.5 h-3.5 text-[#8B7CFF]" />
                    {selectedMember.email}
                  </span>
                  {selectedMember.phone && (
                    <span className="flex items-center gap-1">
                      <Phone className="w-3.5 h-3.5 text-[#8B7CFF]" />
                      {selectedMember.phone}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Bio */}
            {selectedMember.bio && (
              <div className="text-xs text-[#929AAA] bg-[#10131A]/60 p-3.5 rounded-xl border border-[#252B36]/60">
                <span className="text-[10px] uppercase font-mono text-[#929AAA]/70 block mb-1">
                  Bio / Focus
                </span>
                {selectedMember.bio}
              </div>
            )}

            {/* Currently Assigned Tasks */}
            <div>
              <h4 className="text-xs font-semibold text-[#929AAA] uppercase tracking-wider mb-2.5">
                Assigned Tasks (
                {tasks.filter((t) => t.assigneeId === selectedMember.id).length})
              </h4>
              <div className="space-y-2 max-h-52 overflow-y-auto">
                {tasks
                  .filter((t) => t.assigneeId === selectedMember.id)
                  .map((task) => (
                    <div
                      key={task.id}
                      className="flex items-center justify-between p-2.5 bg-[#10131A] rounded-xl border border-[#252B36] text-xs"
                    >
                      <div className="min-w-0 flex-1 pr-3">
                        <span className="font-mono text-[10px] text-[#8B7CFF] mr-2">
                          {task.key}
                        </span>
                        <span className="text-[#F5F7FA] font-medium">{task.title}</span>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <PriorityBadge priority={task.priority} />
                        <TaskStatusBadge status={task.status} />
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* Invite Member Modal */}
      <Modal
        isOpen={isInviteOpen}
        onClose={() => setIsInviteOpen(false)}
        title="Invite New Member"
        description="Add a teammate to FLOWSTATE. They will receive access to your projects."
        maxWidth="md"
      >
        <form onSubmit={handleInvite} className="space-y-4">
          <Input
            label="Full Name *"
            placeholder="e.g. Jordan Blake"
            value={inviteName}
            onChange={(e) => setInviteName(e.target.value)}
            autoFocus
          />

          <Input
            label="Work Email *"
            type="email"
            placeholder="jordan@flowstate.dev"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
          />

          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Role"
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as Role)}
            >
              <option value="developer">Developer</option>
              <option value="designer">Designer</option>
              <option value="manager">Manager</option>
              <option value="admin">Admin</option>
              <option value="viewer">Viewer</option>
            </Select>

            <Input
              label="Department"
              value={inviteDept}
              onChange={(e) => setInviteDept(e.target.value)}
            />
          </div>

          <Input
            label="Job Title"
            value={inviteTitle}
            onChange={(e) => setInviteTitle(e.target.value)}
          />

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#252B36]">
            <Button type="button" variant="outline" onClick={() => setIsInviteOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" isLoading={isSubmitting}>
              Send Invitation
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

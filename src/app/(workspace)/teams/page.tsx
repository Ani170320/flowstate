'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useAuth } from '@/context/AuthContext';
import { Team, User } from '@/types';
import { Avatar, AvatarGroup } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Input, Textarea } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { formatReadableDate } from '@/lib/utils';
import {
  Users2,
  Plus,
  FolderKanban,
  Shield,
  ArrowRight,
  UserPlus,
  Activity,
  Check,
} from 'lucide-react';

export default function TeamsPage() {
  const { allUsers } = useAuth();
  const { teams, projects, createTeam } = useWorkspace();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [teamName, setTeamName] = useState('');
  const [description, setDescription] = useState('');
  const [leadId, setLeadId] = useState(allUsers[0]?.id || 'user_1');
  const [selectedMemberIds, setSelectedMemberIds] = useState<string[]>([allUsers[0]?.id || 'user_1']);
  const [selectedTeamForDetail, setSelectedTeamForDetail] = useState<Team | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const toggleMemberSelection = (id: string) => {
    setSelectedMemberIds((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  };

  const handleCreateTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!teamName.trim()) return;

    setIsSubmitting(true);
    try {
      await createTeam({
        name: teamName.trim(),
        description: description.trim(),
        leadId,
        memberIds: selectedMemberIds,
      });

      setIsCreateModalOpen(false);
      setTeamName('');
      setDescription('');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#252B36]">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#F5F7FA]">Teams & Squads</h1>
          <p className="text-xs sm:text-sm text-[#929AAA] mt-1">
            Organize departments, squads, team leads, and cross-functional ownership.
          </p>
        </div>

        <Button
          onClick={() => setIsCreateModalOpen(true)}
          variant="primary"
          size="sm"
          className="gap-1.5 cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Create Team</span>
        </Button>
      </div>

      {/* Teams Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {teams.map((team) => {
          const lead = allUsers.find((u) => u.id === team.leadId);
          const members = (team.memberIds || [])
            .map((id) => allUsers.find((u) => u.id === id)!)
            .filter(Boolean);
          const assignedProjects = projects.filter(
            (p) => team.projectIds?.includes(p.id) || p.teamId === team.id
          );

          return (
            <div
              key={team.id}
              onClick={() => setSelectedTeamForDetail(team)}
              className="bg-[#151922] border border-[#252B36] hover:border-[#374151] rounded-2xl p-5 transition-all duration-200 flex flex-col justify-between cursor-pointer group shadow-sm hover:shadow-lg"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="w-9 h-9 rounded-xl bg-indigo-500/10 text-[#8B7CFF] border border-indigo-500/20 flex items-center justify-center">
                    <Users2 className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-mono text-[#929AAA] bg-[#10131A] px-2 py-0.5 rounded border border-[#252B36]">
                    {members.length} members
                  </span>
                </div>

                <h3 className="text-base font-semibold text-[#F5F7FA] group-hover:text-white transition-colors">
                  {team.name}
                </h3>
                <p className="text-xs text-[#929AAA] mt-1.5 line-clamp-2 leading-relaxed">
                  {team.description}
                </p>

                {/* Team Lead */}
                <div className="mt-4 p-2.5 bg-[#10131A] border border-[#252B36] rounded-xl flex items-center gap-2.5">
                  <Avatar user={lead} size="xs" />
                  <div className="min-w-0 flex-1">
                    <span className="text-[10px] text-[#929AAA] uppercase font-mono block">
                      Team Lead
                    </span>
                    <p className="text-xs font-semibold text-[#F5F7FA] truncate">
                      {lead?.name || 'Unassigned'}
                    </p>
                  </div>
                  <Shield className="w-3.5 h-3.5 text-[#8B7CFF]" />
                </div>
              </div>

              {/* Footer: Member avatars & projects count */}
              <div className="mt-5 pt-4 border-t border-[#252B36]/80 flex items-center justify-between">
                <AvatarGroup users={members} max={4} size="xs" />

                <div className="flex items-center gap-1.5 text-xs text-[#929AAA]">
                  <FolderKanban className="w-3.5 h-3.5 text-[#8B7CFF]" />
                  <span>{assignedProjects.length} projects</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Create Team Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create New Team"
        description="Assemble an engineering squad or cross-functional department."
        maxWidth="lg"
      >
        <form onSubmit={handleCreateTeam} className="space-y-4">
          <Input
            label="Team Name *"
            placeholder="e.g. Infrastructure & Platform"
            value={teamName}
            onChange={(e) => setTeamName(e.target.value)}
            autoFocus
          />

          <Textarea
            label="Description"
            placeholder="What domains or systems does this team manage?"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />

          <Select
            label="Designated Team Lead"
            value={leadId}
            onChange={(e) => setLeadId(e.target.value)}
          >
            {allUsers.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name} ({u.role})
              </option>
            ))}
          </Select>

          {/* Member Selection */}
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-[#929AAA]">
              Select Members ({selectedMemberIds.length} selected)
            </label>
            <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto p-2 bg-[#10131A] border border-[#252B36] rounded-xl">
              {allUsers.map((u) => {
                const isSelected = selectedMemberIds.includes(u.id);
                return (
                  <button
                    type="button"
                    key={u.id}
                    onClick={() => toggleMemberSelection(u.id)}
                    className={`flex items-center gap-2 p-1.5 rounded-lg text-xs transition-colors text-left cursor-pointer ${
                      isSelected
                        ? 'bg-[#8B7CFF]/15 text-[#8B7CFF] border border-[#8B7CFF]/30'
                        : 'text-[#929AAA] hover:bg-[#151922] hover:text-[#F5F7FA]'
                    }`}
                  >
                    <Avatar user={u} size="xs" />
                    <span className="truncate flex-1">{u.name}</span>
                    {isSelected && <Check className="w-3.5 h-3.5 shrink-0" />}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#252B36]">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsCreateModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" isLoading={isSubmitting}>
              Create Team
            </Button>
          </div>
        </form>
      </Modal>

      {/* Team Details Modal */}
      {selectedTeamForDetail && (
        <Modal
          isOpen={Boolean(selectedTeamForDetail)}
          onClose={() => setSelectedTeamForDetail(null)}
          title={selectedTeamForDetail.name}
          description={selectedTeamForDetail.description}
          maxWidth="2xl"
        >
          <div className="space-y-6">
            {/* Team Roster */}
            <div>
              <h4 className="text-xs font-semibold text-[#929AAA] uppercase tracking-wider mb-3">
                Team Members ({selectedTeamForDetail.memberIds?.length || 0})
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {(selectedTeamForDetail.memberIds || []).map((id) => {
                  const m = allUsers.find((u) => u.id === id);
                  if (!m) return null;
                  const isLead = id === selectedTeamForDetail.leadId;

                  return (
                    <div
                      key={id}
                      className="flex items-center gap-3 p-3 bg-[#10131A] border border-[#252B36] rounded-xl"
                    >
                      <Avatar user={m} size="sm" showStatus />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <p className="text-xs font-semibold text-[#F5F7FA] truncate">{m.name}</p>
                          {isLead && (
                            <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-[#8B7CFF]/20 text-[#8B7CFF] font-bold">
                              LEAD
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-[#929AAA] truncate">{m.title || m.role}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Assigned Projects */}
            <div>
              <h4 className="text-xs font-semibold text-[#929AAA] uppercase tracking-wider mb-3">
                Assigned Projects
              </h4>
              <div className="space-y-2">
                {projects
                  .filter((p) => p.teamId === selectedTeamForDetail.id || selectedTeamForDetail.projectIds?.includes(p.id))
                  .map((p) => (
                    <Link
                      key={p.id}
                      href={`/projects/${p.id}`}
                      className="flex items-center justify-between p-3 rounded-xl bg-[#10131A] hover:bg-[#1B202C] border border-[#252B36] transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-[#8B7CFF] font-bold">
                          [{p.key}]
                        </span>
                        <span className="text-xs font-medium text-[#F5F7FA]">{p.name}</span>
                      </div>
                      <span className="text-xs font-mono text-[#929AAA]">{p.progress}%</span>
                    </Link>
                  ))}
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

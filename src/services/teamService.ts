import { Team, User } from '@/types';
import { apiClient } from '@/lib/api-client';
import { getItem, setItem, STORAGE_KEYS, initializeLocalStorage } from '@/lib/storage/local-storage';

initializeLocalStorage();

function mapBackendUser(u: any): User {
  return {
    id: u.id,
    name: u.name,
    email: u.email,
    avatar: u.avatar_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(u.name || u.email)}`,
    role: u.role || 'developer',
    department: u.department || 'Engineering',
    title: u.title || 'Team Member',
    timezone: u.timezone || 'UTC',
    createdAt: u.created_at || new Date().toISOString(),
  };
}

function mapBackendTeam(t: any): Team {
  const memberList = t.members || [];
  return {
    id: t.id,
    name: t.name,
    description: t.description || '',
    leadId: t.lead_id || (t.lead?.id ?? ''),
    lead: t.lead ? mapBackendUser(t.lead) : undefined,
    memberIds: memberList.map((m: any) => m.user_id),
    members: memberList.map((m: any) => (m.user ? mapBackendUser(m.user) : null)).filter(Boolean),
    projectIds: [],
    createdAt: t.created_at || new Date().toISOString(),
  };
}

export const teamService = {
  async getTeams(): Promise<Team[]> {
    try {
      const teams = await apiClient.get<any[]>('/teams');
      if (Array.isArray(teams)) {
        const mapped = teams.map(mapBackendTeam);
        setItem(STORAGE_KEYS.TEAMS, mapped);
        return mapped;
      }
    } catch (err) {
      console.warn('Backend /teams unavailable, falling back to local storage:', err);
    }

    const teams = getItem<Team[]>(STORAGE_KEYS.TEAMS, []);
    const users = getItem<User[]>(STORAGE_KEYS.USERS, []);
    return teams.map((team) => ({
      ...team,
      lead: users.find((u) => u.id === team.leadId),
      members: (team.memberIds || []).map((id) => users.find((u) => u.id === id)!).filter(Boolean),
    }));
  },

  async getTeamById(id: string): Promise<Team | null> {
    try {
      const res = await apiClient.get<any>(`/teams/${id}`);
      if (res && res.id) {
        return mapBackendTeam(res);
      }
    } catch {
      // Fallback
    }
    const teams = await this.getTeams();
    return teams.find((t) => t.id === id) || null;
  },

  async createTeam(data: { name: string; description: string; leadId: string; memberIds?: string[] }): Promise<Team> {
    try {
      const res = await apiClient.post<any>('/teams', {
        name: data.name,
        description: data.description,
        lead_id: data.leadId || undefined,
        member_ids: data.memberIds || [],
      });
      if (res && res.id) {
        const mapped = mapBackendTeam(res);
        const teams = getItem<Team[]>(STORAGE_KEYS.TEAMS, []);
        setItem(STORAGE_KEYS.TEAMS, [...teams, mapped]);
        return mapped;
      }
    } catch (err) {
      console.warn('Backend team creation failed, creating locally:', err);
    }

    const teams = getItem<Team[]>(STORAGE_KEYS.TEAMS, []);
    const newTeam: Team = {
      id: `team_${Date.now()}`,
      name: data.name,
      description: data.description,
      leadId: data.leadId,
      memberIds: data.memberIds || [data.leadId],
      projectIds: [],
      createdAt: new Date().toISOString(),
    };

    const updated = [...teams, newTeam];
    setItem(STORAGE_KEYS.TEAMS, updated);
    return newTeam;
  },

  async updateTeam(id: string, updates: Partial<Team>): Promise<Team> {
    try {
      const res = await apiClient.patch<any>(`/teams/${id}`, {
        name: updates.name,
        description: updates.description,
        lead_id: updates.leadId,
      });
      if (res && res.id) {
        return mapBackendTeam(res);
      }
    } catch {
      // Fallback
    }
    const teams = getItem<Team[]>(STORAGE_KEYS.TEAMS, []);
    const idx = teams.findIndex((t) => t.id === id);
    if (idx !== -1) {
      teams[idx] = { ...teams[idx], ...updates };
      setItem(STORAGE_KEYS.TEAMS, teams);
      return teams[idx];
    }
    throw new Error(`Team ${id} not found`);
  },

  async deleteTeam(id: string): Promise<boolean> {
    try {
      await apiClient.delete(`/teams/${id}`);
    } catch {
      // Fallback
    }
    const teams = getItem<Team[]>(STORAGE_KEYS.TEAMS, []);
    setItem(STORAGE_KEYS.TEAMS, teams.filter((t) => t.id !== id));
    return true;
  },

  async addMemberToTeam(teamId: string, memberId: string): Promise<boolean> {
    try {
      await apiClient.post(`/teams/${teamId}/members`, { user_id: memberId });
    } catch {
      // Fallback
    }

    const teams = getItem<Team[]>(STORAGE_KEYS.TEAMS, []);
    const team = teams.find((t) => t.id === teamId);
    if (!team) return false;

    if (!team.memberIds.includes(memberId)) {
      team.memberIds.push(memberId);
      setItem(STORAGE_KEYS.TEAMS, teams);
    }
    return true;
  },

  async removeMemberFromTeam(teamId: string, memberId: string): Promise<boolean> {
    try {
      await apiClient.delete(`/teams/${teamId}/members/${memberId}`);
    } catch {
      // Fallback
    }
    const teams = getItem<Team[]>(STORAGE_KEYS.TEAMS, []);
    const team = teams.find((t) => t.id === teamId);
    if (!team) return false;
    team.memberIds = team.memberIds.filter((id) => id !== memberId);
    setItem(STORAGE_KEYS.TEAMS, teams);
    return true;
  },
};

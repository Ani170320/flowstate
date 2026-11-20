import { User, Role } from '@/types';
import { apiClient } from '@/lib/api-client';
import { getItem, setItem, STORAGE_KEYS, initializeLocalStorage } from '@/lib/storage/local-storage';
import { isValidUuid, DEFAULT_ORG_ID } from '@/lib/utils';

initializeLocalStorage();

function mapBackendMember(m: any): User {
  const u = m.user || m;
  return {
    id: u.id,
    name: u.name,
    email: u.email,
    avatar: u.avatar_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(u.name || u.email)}`,
    role: m.role || u.role || 'developer',
    department: u.department || 'Engineering',
    title: u.title || 'Team Member',
    phone: u.phone || '',
    bio: u.bio || '',
    timezone: u.timezone || 'UTC',
    createdAt: u.created_at || new Date().toISOString(),
  };
}

export const memberService = {
  async getMembers(): Promise<User[]> {
    try {
      const rawOrgId = apiClient.getActiveOrgId();
      const orgId = isValidUuid(rawOrgId) ? rawOrgId : DEFAULT_ORG_ID;
      if (orgId) {
        const members = await apiClient.get<any[]>(`/organizations/${orgId}/members`);
        if (Array.isArray(members)) {
          const mapped = members.map(mapBackendMember);
          setItem(STORAGE_KEYS.USERS, mapped);
          return mapped;
        }
      }
    } catch (err) {
      console.warn('Backend /organizations/{id}/members failed, falling back to local storage:', err);
    }

    return getItem<User[]>(STORAGE_KEYS.USERS, []);
  },

  async getMemberById(id: string): Promise<User | null> {
    const members = await this.getMembers();
    return members.find((u) => u.id === id) || null;
  },

  async updateMember(id: string, updates: Partial<User>): Promise<User> {
    try {
      const rawOrgId = apiClient.getActiveOrgId();
      const orgId = isValidUuid(rawOrgId) ? rawOrgId : DEFAULT_ORG_ID;
      if (orgId && updates.role) {
        await apiClient.patch(`/organizations/${orgId}/members/${id}`, {
          role: updates.role,
        });
      }
    } catch (err) {
      console.warn(`Backend update member role failed for ${id}:`, err);
    }

    const members = getItem<User[]>(STORAGE_KEYS.USERS, []);
    const index = members.findIndex((u) => u.id === id);

    let updated: User;
    if (index === -1) {
      updated = {
        id,
        name: updates.name || 'User',
        email: updates.email || '',
        avatar: updates.avatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${id}`,
        role: updates.role || 'owner',
        department: updates.department || 'Engineering',
        title: updates.title || 'Team Member',
        phone: updates.phone || '',
        bio: updates.bio || '',
        timezone: updates.timezone || 'UTC',
        createdAt: new Date().toISOString(),
        ...updates,
      };
      members.push(updated);
    } else {
      updated = {
        ...members[index],
        ...updates,
      };
      members[index] = updated;
    }
    setItem(STORAGE_KEYS.USERS, members);
    return updated;
  },

  async inviteMember(data: { name: string; email: string; role: Role; department: string; title: string }): Promise<User> {
    try {
      const rawOrgId = apiClient.getActiveOrgId();
      const orgId = isValidUuid(rawOrgId) ? rawOrgId : DEFAULT_ORG_ID;
      if (orgId) {
        const res = await apiClient.post<any>(`/organizations/${orgId}/members`, {
          email: data.email,
          role: data.role,
        });
        if (res && res.user) {
          const newUser = mapBackendMember(res);
          const members = getItem<User[]>(STORAGE_KEYS.USERS, []);
          setItem(STORAGE_KEYS.USERS, [...members, newUser]);
          return newUser;
        }
      }
    } catch (err) {
      console.warn('Backend invite member failed, creating locally:', err);
    }

    const members = getItem<User[]>(STORAGE_KEYS.USERS, []);
    const newUser: User = {
      id: `user_${Date.now()}`,
      name: data.name,
      email: data.email,
      avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(data.name)}`,
      role: data.role,
      department: data.department,
      title: data.title,
      createdAt: new Date().toISOString(),
    };

    const updated = [...members, newUser];
    setItem(STORAGE_KEYS.USERS, updated);
    return newUser;
  },

  async removeMember(userId: string): Promise<boolean> {
    try {
      const orgId = apiClient.getActiveOrgId();
      if (orgId) {
        await apiClient.delete(`/organizations/${orgId}/members/${userId}`);
      }
    } catch {
      // Fallback
    }

    const members = getItem<User[]>(STORAGE_KEYS.USERS, []);
    setItem(STORAGE_KEYS.USERS, members.filter((m) => m.id !== userId));
    return true;
  },
};

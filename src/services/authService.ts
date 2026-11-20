import { User, Organization } from '@/types';
import { apiClient } from '@/lib/api-client';

interface BackendUserProfile {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  department?: string;
  title?: string;
  phone?: string;
  bio?: string;
  timezone: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface BackendOrgMembership {
  id: string;
  name: string;
  slug: string;
  logo_url?: string;
  plan: 'free' | 'pro' | 'enterprise';
  role: 'owner' | 'admin' | 'manager' | 'developer' | 'designer' | 'viewer';
  joined_at: string;
}

interface BackendAuthMeResponse {
  user: BackendUserProfile;
  active_organization: BackendOrgMembership | null;
  organizations: BackendOrgMembership[];
}

interface BackendAuthSessionResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: BackendUserProfile;
  active_organization: BackendOrgMembership | null;
  organizations: BackendOrgMembership[];
}

function mapUserProfile(u: BackendUserProfile, role: string = 'developer'): User {
  return {
    id: u.id,
    name: u.name,
    email: u.email,
    avatar: u.avatar_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(u.name || u.email)}`,
    role: (role as any) || 'developer',
    department: u.department || 'Engineering',
    title: u.title || 'Team Member',
    phone: u.phone || '',
    bio: u.bio || '',
    timezone: u.timezone || 'UTC',
    createdAt: u.created_at,
  };
}

export const authService = {
  async bootstrapDemoSession(email?: string): Promise<BackendAuthSessionResponse | null> {
    try {
      let targetEmail = email;
      if (!targetEmail && typeof window !== 'undefined') {
        const saved = localStorage.getItem('flowstate_saved_user');
        if (saved) {
          try {
            const p = JSON.parse(saved);
            if (p.email) targetEmail = p.email;
          } catch {}
        }
      }
      if (!targetEmail) {
        targetEmail = 'alex@flowstate.dev';
      }
      const demoRes = await apiClient.post<BackendAuthSessionResponse>('/auth/demo-session', {
        email: targetEmail,
      });
      if (demoRes?.access_token) {
        apiClient.setAuthToken(demoRes.access_token);
        if (demoRes.active_organization) {
          apiClient.setActiveOrgId(demoRes.active_organization.id);
        }
      }
      return demoRes;
    } catch (bootErr) {
      console.warn('Demo session auto-bootstrap fallback:', bootErr);
      return null;
    }
  },

  async getSession(): Promise<{ user: User; activeOrg: Organization | null; organizations: Organization[] }> {
    let token = apiClient.getAuthToken();
    if (!token && typeof window !== 'undefined') {
      const savedUserStr = localStorage.getItem('flowstate_saved_user');
      if (savedUserStr) {
        try {
          const parsed = JSON.parse(savedUserStr);
          if (parsed.email) {
            await this.bootstrapDemoSession(parsed.email);
            token = apiClient.getAuthToken();
          }
        } catch {}
      }
    }

    if (!token) {
      await this.bootstrapDemoSession();
    }

    let data: BackendAuthMeResponse;
    try {
      data = await apiClient.get<BackendAuthMeResponse>('/auth/me');
    } catch (err: any) {
      // If token expired or unauthorized, clear token and retry with user's saved session
      if (err?.status === 401 || err?.code === 'TOKEN_EXPIRED') {
        apiClient.setAuthToken(null);
        if (typeof window !== 'undefined') {
          const savedUserStr = localStorage.getItem('flowstate_saved_user');
          if (savedUserStr) {
            try {
              const parsed = JSON.parse(savedUserStr);
              if (parsed.email) {
                await this.bootstrapDemoSession(parsed.email);
              }
            } catch {}
          }
        }
        data = await apiClient.get<BackendAuthMeResponse>('/auth/me');
      } else {
        throw err;
      }
    }

    const activeRole = data.active_organization?.role || 'owner';
    const user = mapUserProfile(data.user, activeRole);

    if (data.active_organization) {
      apiClient.setActiveOrgId(data.active_organization.id);
    }

    const organizations: Organization[] = (data.organizations || []).map((org) => ({
      id: org.id,
      name: org.name,
      slug: org.slug,
      logo: org.logo_url,
      plan: org.plan,
      membersCount: 1,
    }));

    const activeOrg: Organization | null = data.active_organization
      ? {
          id: data.active_organization.id,
          name: data.active_organization.name,
          slug: data.active_organization.slug,
          logo: data.active_organization.logo_url,
          plan: data.active_organization.plan,
          membersCount: organizations.length,
        }
      : null;

    return { user, activeOrg, organizations };
  },

  async getCurrentUser(): Promise<User> {
    const session = await this.getSession().catch(() => null);
    if (session) return session.user;
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem('flowstate_current_user');
        if (stored) return JSON.parse(stored);
        const saved = localStorage.getItem('flowstate_saved_user');
        if (saved) {
          const p = JSON.parse(saved);
          return {
            id: p.id || 'usr_me',
            name: p.name || 'User',
            email: p.email || '',
            avatar: p.avatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(p.email || 'user')}`,
            role: p.role || 'owner',
            createdAt: new Date().toISOString(),
          };
        }
      } catch {}
    }
    return {
      id: '',
      name: '',
      email: '',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=user',
      role: 'owner',
      createdAt: new Date().toISOString(),
    };
  },

  async switchUser(userId: string): Promise<User> {
    const isEmail = userId.includes('@');
    const res = await apiClient.post<BackendAuthSessionResponse>('/auth/demo-session', {
      user_id: isEmail ? undefined : userId,
      email: isEmail ? userId : undefined,
    });
    apiClient.setAuthToken(res.access_token);
    if (res.active_organization) {
      apiClient.setActiveOrgId(res.active_organization.id);
    }
    return mapUserProfile(res.user, res.active_organization?.role || 'owner');
  },

  async login(email: string, password?: string): Promise<{ user: User; token: string }> {
    const res = await apiClient.post<BackendAuthSessionResponse>('/auth/login', {
      email,
      password,
    });
    apiClient.setAuthToken(res.access_token);
    if (res.active_organization) {
      apiClient.setActiveOrgId(res.active_organization.id);
    }
    const user = mapUserProfile(res.user, res.active_organization?.role || 'developer');
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('flowstate_saved_user', JSON.stringify({ email: user.email, id: user.id, name: user.name }));
        localStorage.setItem('flowstate_current_user', JSON.stringify(user));
      } catch {}
    }
    return { user, token: res.access_token };
  },

  async register(data: {
    name: string;
    email: string;
    password?: string;
    phone?: string;
    workspaceName?: string;
    workspaceSlug?: string;
    plan?: string;
  }): Promise<{ user: User; token: string }> {
    const res = await apiClient.post<BackendAuthSessionResponse>('/auth/signup', {
      name: data.name,
      email: data.email,
      password: data.password || 'FlowstatePass123!',
      phone: data.phone,
      workspace_name: data.workspaceName,
      workspace_slug: data.workspaceSlug,
      plan: data.plan || 'enterprise',
    });
    apiClient.setAuthToken(res.access_token);
    if (res.active_organization) {
      apiClient.setActiveOrgId(res.active_organization.id);
    }
    const user = mapUserProfile(res.user, res.active_organization?.role || 'owner');
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('flowstate_saved_user', JSON.stringify({ email: user.email, id: user.id, name: user.name }));
        localStorage.setItem('flowstate_current_user', JSON.stringify(user));
      } catch {}
    }
    return { user, token: res.access_token };
  },

  async updateProfile(updates: Partial<User>): Promise<User> {
    const res = await apiClient.patch<BackendUserProfile>('/auth/me', {
      name: updates.name,
      email: updates.email,
      title: updates.title,
      department: updates.department,
      phone: updates.phone,
      bio: updates.bio,
      timezone: updates.timezone,
      avatar_url: updates.avatar,
    });
    const user = mapUserProfile(res, updates.role || 'owner');
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('flowstate_saved_user', JSON.stringify({ email: user.email, id: user.id, name: user.name }));
        localStorage.setItem('flowstate_current_user', JSON.stringify(user));
      } catch {}
    }
    return user;
  },

  async switchOrganization(orgId: string): Promise<Organization> {
    const res = await apiClient.post<{ message: string; active_organization: BackendOrgMembership }>(
      '/auth/switch-organization',
      { organization_id: orgId }
    );
    apiClient.setActiveOrgId(res.active_organization.id);
    return {
      id: res.active_organization.id,
      name: res.active_organization.name,
      slug: res.active_organization.slug,
      logo: res.active_organization.logo_url,
      plan: res.active_organization.plan,
      membersCount: 1,
    };
  },

  async requestPasswordReset(email: string): Promise<boolean> {
    return true;
  },

  async logout(): Promise<void> {
    apiClient.setAuthToken(null);
    apiClient.setActiveOrgId(null);
    if (typeof window !== 'undefined') {
      try {
        localStorage.removeItem('flowstate_saved_user');
        localStorage.removeItem('flowstate_current_user');
        localStorage.removeItem('flowstate_auth_token');
        localStorage.removeItem('flowstate_active_org_id');
      } catch {}
    }
  },
};

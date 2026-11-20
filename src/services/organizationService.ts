import { Organization, WorkspaceSettings } from '@/types';
import { apiClient } from '@/lib/api-client';
import { isValidUuid, DEFAULT_ORG_ID } from '@/lib/utils';

export interface BackendWorkspaceSettings {
  id: string;
  organization_id: string;
  currency: string;
  timezone: string;
  working_days: number[];
  notifications_email: boolean;
  notifications_desktop: boolean;
  theme: string;
  accent_color: string;
  updated_at: string;
}

export interface BackendOrgDetail {
  id: string;
  name: string;
  slug: string;
  logo_url?: string;
  plan: 'free' | 'pro' | 'enterprise';
  current_user_role?: 'owner' | 'admin' | 'manager' | 'developer' | 'designer' | 'viewer';
  members_count: number;
  settings?: BackendWorkspaceSettings;
  created_at: string;
  updated_at: string;
}

export const organizationService = {
  async getOrganizations(): Promise<Organization[]> {
    try {
      const orgs = await apiClient.get<BackendOrgDetail[]>('/organizations');
      return orgs.map((o) => ({
        id: o.id,
        name: o.name,
        slug: o.slug,
        logo: o.logo_url,
        plan: o.plan,
        membersCount: o.members_count || 1,
      }));
    } catch (err) {
      console.warn('Failed to fetch organizations from backend, using active org if set:', err);
      const activeId = apiClient.getActiveOrgId();
      return [
        {
          id: activeId || DEFAULT_ORG_ID,
          name: 'Flowstate Labs',
          slug: 'flowstate-labs',
          plan: 'free',
          membersCount: 4,
        },
      ];
    }
  },

  async getOrganization(orgId: string): Promise<BackendOrgDetail | null> {
    const validId = isValidUuid(orgId) ? orgId : DEFAULT_ORG_ID;
    try {
      return await apiClient.get<BackendOrgDetail>(`/organizations/${validId}`);
    } catch {
      return null;
    }
  },

  async createOrganization(data: { name: string; slug?: string; logo_url?: string }): Promise<Organization> {
    const res = await apiClient.post<BackendOrgDetail>('/organizations', data);
    return {
      id: res.id,
      name: res.name,
      slug: res.slug,
      logo: res.logo_url,
      plan: res.plan,
      membersCount: 1,
    };
  },

  async updateOrganization(orgId: string, data: { name?: string; slug?: string; logo_url?: string }): Promise<void> {
    const validId = isValidUuid(orgId) ? orgId : DEFAULT_ORG_ID;
    await apiClient.patch(`/organizations/${validId}`, data);
  },

  async getWorkspaceSettings(orgId: string): Promise<WorkspaceSettings> {
    const validId = isValidUuid(orgId) ? orgId : DEFAULT_ORG_ID;
    try {
      const s = await apiClient.get<BackendWorkspaceSettings>(`/organizations/${validId}/settings`);
      return {
        name: 'Workspace',
        slug: 'workspace',
        currency: s.currency,
        timezone: s.timezone,
        workingDays: s.working_days,
        notificationsEmail: s.notifications_email,
        notificationsDesktop: s.notifications_desktop,
        theme: (s.theme as any) || 'dark',
      };
    } catch {
      return {
        name: 'Flowstate Labs',
        slug: 'flowstate-labs',
        currency: 'USD',
        timezone: 'UTC',
        workingDays: [1, 2, 3, 4, 5],
        notificationsEmail: true,
        notificationsDesktop: true,
        theme: 'dark',
      };
    }
  },

  async updateWorkspaceSettings(
    orgId: string,
    settings: Partial<BackendWorkspaceSettings>
  ): Promise<WorkspaceSettings> {
    const validId = isValidUuid(orgId) ? orgId : DEFAULT_ORG_ID;
    const s = await apiClient.patch<BackendWorkspaceSettings>(`/organizations/${validId}/settings`, settings);
    return {
      name: 'Workspace',
      slug: 'workspace',
      currency: s.currency,
      timezone: s.timezone,
      workingDays: s.working_days,
      notificationsEmail: s.notifications_email,
      notificationsDesktop: s.notifications_desktop,
      theme: (s.theme as any) || 'dark',
    };
  },
};

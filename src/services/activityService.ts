import { Activity, User } from '@/types';
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

function mapBackendActivity(a: any): Activity {
  return {
    id: a.id,
    userId: a.user_id,
    user: a.user ? mapBackendUser(a.user) : undefined,
    action: a.action || 'created_task',
    targetType: a.target_type || 'task',
    targetId: a.target_id,
    targetTitle: a.target_title || 'Work Item',
    projectId: a.project_id,
    details: typeof a.details === 'object' ? JSON.stringify(a.details) : a.details,
    timestamp: a.created_at || new Date().toISOString(),
  };
}

export const activityService = {
  async getActivities(limit = 20): Promise<Activity[]> {
    try {
      const orgId = apiClient.getActiveOrgId();
      if (orgId) {
        const res = await apiClient.get<any>(`/organizations/${orgId}/activities`, {
          params: { limit },
        });
        const items = Array.isArray(res) ? res : res.items || [];
        if (Array.isArray(items)) {
          const mapped = items.map(mapBackendActivity);
          setItem(STORAGE_KEYS.ACTIVITIES, mapped);
          return mapped;
        }
      }
    } catch (err) {
      console.warn('Backend /activities failed, falling back to local storage:', err);
    }

    const activities = getItem<Activity[]>(STORAGE_KEYS.ACTIVITIES, []);
    const users = getItem<User[]>(STORAGE_KEYS.USERS, []);

    return activities
      .slice(0, limit)
      .map((act) => ({
        ...act,
        user: users.find((u) => u.id === act.userId),
      }))
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  },

  async getActivitiesByProject(projectId: string): Promise<Activity[]> {
    try {
      const res = await apiClient.get<any>(`/projects/${projectId}/activities`, {
        params: { limit: 50 },
      });
      const items = Array.isArray(res) ? res : res.items || [];
      if (items.length > 0) {
        return items.map(mapBackendActivity);
      }
    } catch {
      // Fallback
    }

    const all = await this.getActivities(50);
    return all.filter((a) => a.projectId === projectId);
  },

  async logActivity(data: {
    userId: string;
    action: Activity['action'];
    targetType: Activity['targetType'];
    targetId: string;
    targetTitle: string;
    projectId?: string;
    projectName?: string;
    details?: string;
  }): Promise<Activity> {
    const activities = getItem<Activity[]>(STORAGE_KEYS.ACTIVITIES, []);
    const users = getItem<User[]>(STORAGE_KEYS.USERS, []);

    const newActivity: Activity = {
      id: `act_${Date.now()}`,
      userId: data.userId,
      action: data.action,
      targetType: data.targetType,
      targetId: data.targetId,
      targetTitle: data.targetTitle,
      projectId: data.projectId,
      projectName: data.projectName,
      details: data.details,
      timestamp: new Date().toISOString(),
    };

    const updated = [newActivity, ...activities];
    setItem(STORAGE_KEYS.ACTIVITIES, updated);

    return {
      ...newActivity,
      user: users.find((u) => u.id === data.userId),
    };
  },
};

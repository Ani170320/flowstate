import { apiClient } from '@/lib/api-client';

export interface DashboardOverview {
  total_projects: number;
  active_projects: number;
  completed_projects: number;
  total_tasks: number;
  completed_tasks: number;
  in_progress_tasks: number;
  overdue_tasks: number;
  upcoming_deadlines: number;
  total_team_members: number;
  my_tasks_summary: Record<string, number>;
}

export interface TaskStats {
  total_tasks: number;
  completed_tasks: number;
  in_progress_tasks: number;
  overdue_tasks: number;
  completion_rate: number;
  tasks_by_status: Record<string, number>;
  tasks_by_priority: Record<string, number>;
  total_estimated_hours: number;
  total_actual_hours: number;
}

export interface ProjectStatItem {
  id: string;
  key: string;
  name: string;
  status: string;
  priority: string;
  color: string;
  progress: number;
  calculated_progress: number;
  total_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;
  start_date?: string;
  due_date?: string;
  is_overdue: boolean;
  spent: number;
  budget?: number;
}

export interface ProjectStats {
  total_projects: number;
  projects: ProjectStatItem[];
}

export interface MemberWorkloadStatItem {
  user_id: string;
  name: string;
  email: string;
  avatar_url?: string;
  role?: string;
  assigned_tasks_count: number;
  completed_tasks_count: number;
  pending_tasks_count: number;
  overdue_tasks_count: number;
  workload_percentage: number;
}

export interface TeamStats {
  total_members: number;
  active_tasks_count: number;
  members: MemberWorkloadStatItem[];
}

export interface ProjectAnalytics {
  project_id: string;
  project_name: string;
  project_key: string;
  status: string;
  priority: string;
  completion_percentage: number;
  tasks_by_status: Record<string, number>;
  tasks_by_priority: Record<string, number>;
  total_tasks: number;
  completed_tasks: number;
  pending_tasks: number;
  overdue_tasks_count: number;
  start_date?: string;
  due_date?: string;
  days_remaining?: number;
  is_overdue: boolean;
  estimated_hours_total: number;
  actual_hours_total: number;
}

export interface TeamAnalytics {
  team_id: string;
  team_name: string;
  member_count: number;
  members: MemberWorkloadStatItem[];
}

export const dashboardService = {
  async getOverview(): Promise<DashboardOverview> {
    try {
      return await apiClient.get<DashboardOverview>('/dashboard/overview');
    } catch (err) {
      console.warn('Dashboard overview API fallback:', err);
      return {
        total_projects: 0,
        active_projects: 0,
        completed_projects: 0,
        total_tasks: 0,
        completed_tasks: 0,
        in_progress_tasks: 0,
        overdue_tasks: 0,
        upcoming_deadlines: 0,
        total_team_members: 0,
        my_tasks_summary: { todo: 0, in_progress: 0, done: 0 },
      };
    }
  },

  async getTaskStats(): Promise<TaskStats> {
    return apiClient.get<TaskStats>('/dashboard/task-stats');
  },

  async getProjectStats(): Promise<ProjectStats> {
    return apiClient.get<ProjectStats>('/dashboard/project-stats');
  },

  async getTeamStats(): Promise<TeamStats> {
    return apiClient.get<TeamStats>('/dashboard/team-stats');
  },

  async getRecentActivity(limit = 10) {
    return apiClient.get('/dashboard/recent-activity', { params: { limit } });
  },

  async getProjectAnalytics(projectId: string): Promise<ProjectAnalytics> {
    return apiClient.get<ProjectAnalytics>(`/projects/${projectId}/analytics`);
  },

  async getTeamAnalytics(teamId: string): Promise<TeamAnalytics> {
    return apiClient.get<TeamAnalytics>(`/teams/${teamId}/analytics`);
  },
};

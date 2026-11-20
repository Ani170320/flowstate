export type Priority = 'low' | 'medium' | 'high' | 'urgent';

export type TaskStatus = 'backlog' | 'todo' | 'in_progress' | 'in_review' | 'done';

export type ProjectStatus = 'planning' | 'in_progress' | 'in_review' | 'completed' | 'on_hold';

export type Role = 'owner' | 'admin' | 'manager' | 'developer' | 'designer' | 'viewer';

export interface User {
  id: string;
  name: string;
  email: string;
  avatar: string;
  role: Role;
  department?: string;
  title?: string;
  phone?: string;
  bio?: string;
  timezone?: string;
  createdAt: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  logo?: string;
  plan: 'free' | 'pro' | 'enterprise';
  membersCount: number;
}

export interface Team {
  id: string;
  name: string;
  description: string;
  leadId: string;
  lead?: User;
  memberIds: string[];
  members?: User[];
  projectIds: string[];
  createdAt: string;
}

export interface Subtask {
  id: string;
  title: string;
  completed: boolean;
}

export interface Comment {
  id: string;
  taskId: string;
  authorId: string;
  author?: User;
  content: string;
  createdAt: string;
  attachments?: string[];
}

export interface Task {
  id: string;
  projectId: string;
  projectName?: string;
  projectKey?: string;
  taskNumber?: number;
  key?: string; // e.g. "FLW-104"
  title: string;
  description: string;
  status: TaskStatus;
  priority: Priority;
  assigneeId?: string;
  assignee?: User;
  creatorId: string;
  creator?: User;
  dueDate: string;
  startDate?: string;
  estimatedHours?: number;
  actualHours?: number;
  labels: string[];
  subtasks: Subtask[];
  commentsCount?: number;
  createdAt: string;
  updatedAt: string;
  order: number;
}

export interface ProjectFile {
  id: string;
  name: string;
  size: number;
  type: string;
  uploadedBy: string;
  uploader?: User;
  uploadedAt: string;
  url: string;
}

export interface Project {
  id: string;
  key: string; // e.g. "FLW"
  name: string;
  description: string;
  status: ProjectStatus;
  priority: Priority;
  color?: string;
  startDate: string;
  dueDate: string;
  managerId: string;
  manager?: User;
  teamMemberIds: string[];
  teamMembers?: User[];
  teamId?: string;
  progress: number; // 0 - 100
  budget?: number;
  spent?: number;
  tags?: string[];
  createdAt: string;
  updatedAt: string;
}

export interface Activity {
  id: string;
  userId: string;
  user?: User;
  action: 'created_task' | 'updated_task' | 'completed_task' | 'created_project' | 'updated_project' | 'commented' | 'assigned_task' | 'status_change';
  targetType: 'task' | 'project' | 'team' | 'comment';
  targetId: string;
  targetTitle: string;
  projectId?: string;
  projectName?: string;
  details?: string;
  timestamp: string;
}

export interface Notification {
  id: string;
  userId: string;
  title: string;
  message: string;
  type: 'assignment' | 'deadline' | 'mention' | 'project_update' | 'system';
  isRead: boolean;
  link?: string;
  createdAt: string;
  senderId?: string;
  sender?: User;
}

export interface WorkspaceSettings {
  name: string;
  slug: string;
  currency: string;
  timezone: string;
  workingDays: number[];
  notificationsEmail: boolean;
  notificationsDesktop: boolean;
  theme: 'dark' | 'midnight' | 'system';
}

export interface FilterOptions {
  search?: string;
  status?: string;
  priority?: string;
  assigneeId?: string;
  projectId?: string;
  sortBy?: string;
  sortDirection?: 'asc' | 'desc';
}

// ==========================================
// AI Intelligence Types
// ==========================================
export interface AISubtaskItem {
  title: string;
  description?: string;
}

export interface AISubtaskGenerationResponse {
  suggested_title: string;
  description: string;
  estimated_hours: number;
  priority: Priority;
  subtasks: AISubtaskItem[];
  labels: string[];
}

export interface AIAssigneeSuggestionResponse {
  recommended_user_id?: string;
  recommended_user_name?: string;
  confidence: number;
  reasoning: string;
  suggested_hours: number;
}

export interface AIChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface AIChatResponse {
  reply: string;
  references?: Array<Record<string, any>>;
}

export interface AISprintRetroResponse {
  markdown_report: string;
  summary: string;
  highlights: string[];
  bottlenecks: string[];
  recommendations: string[];
}


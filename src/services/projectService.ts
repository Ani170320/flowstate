import { Project, ProjectStatus, Priority, ProjectFile, User } from '@/types';
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

function mapBackendProject(p: any): Project {
  return {
    id: p.id,
    key: p.key,
    name: p.name,
    description: p.description || '',
    status: p.status || 'planning',
    priority: p.priority || 'medium',
    color: p.color || '#8B7CFF',
    startDate: p.start_date || p.created_at?.split('T')[0] || new Date().toISOString().split('T')[0],
    dueDate: p.due_date || '',
    managerId: p.manager_id || (p.manager?.id ?? ''),
    manager: p.manager ? mapBackendUser(p.manager) : undefined,
    teamMemberIds: p.members ? p.members.map((m: any) => m.user_id) : [],
    teamMembers: p.members ? p.members.map((m: any) => (m.user ? mapBackendUser(m.user) : null)).filter(Boolean) : [],
    teamId: p.team_id,
    progress: p.progress ?? 0,
    budget: p.budget !== undefined && p.budget !== null ? Number(p.budget) : 30000,
    spent: p.spent !== undefined && p.spent !== null ? Number(p.spent) : 0,
    tags: p.tags || ['Feature'],
    createdAt: p.created_at || new Date().toISOString(),
    updatedAt: p.updated_at || new Date().toISOString(),
  };
}

export const projectService = {
  async getProjects(): Promise<Project[]> {
    try {
      const projects = await apiClient.get<any[]>('/projects');
      if (Array.isArray(projects)) {
        const mapped = projects.map(mapBackendProject);
        setItem(STORAGE_KEYS.PROJECTS, mapped);
        return mapped;
      }
    } catch (err) {
      console.warn('Backend /projects unavailable, falling back to local storage:', err);
    }

    const projects = getItem<Project[]>(STORAGE_KEYS.PROJECTS, []);
    const users = getItem<User[]>(STORAGE_KEYS.USERS, []);
    return projects.map((proj) => ({
      ...proj,
      manager: users.find((u) => u.id === proj.managerId),
      teamMembers: (proj.teamMemberIds || []).map((id) => users.find((u) => u.id === id)!).filter(Boolean),
    }));
  },

  async getProjectById(id: string): Promise<Project | null> {
    try {
      const proj = await apiClient.get<any>(`/projects/${id}`);
      if (proj && proj.id) {
        return mapBackendProject(proj);
      }
    } catch {
      // Fallback
    }
    const projects = await this.getProjects();
    return projects.find((p) => p.id === id) || null;
  },

  async createProject(data: {
    name: string;
    key?: string;
    description: string;
    status?: ProjectStatus;
    priority?: Priority;
    startDate: string;
    dueDate: string;
    managerId: string;
    teamMemberIds: string[];
    color?: string;
    budget?: number;
    tags?: string[];
    teamId?: string;
  }): Promise<Project> {
    try {
      const res = await apiClient.post<any>('/projects', {
        name: data.name,
        key: data.key,
        description: data.description,
        status: data.status || 'planning',
        priority: data.priority || 'medium',
        start_date: data.startDate || undefined,
        due_date: data.dueDate || undefined,
        manager_id: data.managerId || undefined,
        color: data.color || '#8B7CFF',
        budget: data.budget || 0,
        member_ids: data.teamMemberIds || [],
        team_id: data.teamId || undefined,
      });

      if (res && res.id) {
        const mapped = mapBackendProject(res);
        const projects = getItem<Project[]>(STORAGE_KEYS.PROJECTS, []);
        setItem(STORAGE_KEYS.PROJECTS, [mapped, ...projects]);
        return mapped;
      }
    } catch (err) {
      console.warn('Backend project creation failed, creating locally:', err);
    }

    // Local fallback
    const projects = getItem<Project[]>(STORAGE_KEYS.PROJECTS, []);
    const key = data.key || data.name.substring(0, 3).toUpperCase();
    const newProject: Project = {
      id: `proj_${Date.now()}`,
      key,
      name: data.name,
      description: data.description,
      status: data.status || 'planning',
      priority: data.priority || 'medium',
      color: data.color || '#8B7CFF',
      startDate: data.startDate,
      dueDate: data.dueDate,
      managerId: data.managerId,
      teamMemberIds: data.teamMemberIds || [data.managerId],
      progress: 0,
      budget: data.budget || 30000,
      spent: 0,
      tags: data.tags || ['Feature'],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setItem(STORAGE_KEYS.PROJECTS, [newProject, ...projects]);
    return newProject;
  },

  async updateProject(id: string, updates: Partial<Project>): Promise<Project> {
    try {
      const payload: any = {};
      if (updates.name !== undefined) payload.name = updates.name;
      if (updates.key !== undefined) payload.key = updates.key;
      if (updates.description !== undefined) payload.description = updates.description;
      if (updates.status !== undefined) payload.status = updates.status;
      if (updates.priority !== undefined) payload.priority = updates.priority;
      if (updates.color !== undefined) payload.color = updates.color;
      if (updates.startDate !== undefined) payload.start_date = updates.startDate;
      if (updates.dueDate !== undefined) payload.due_date = updates.dueDate;
      if (updates.progress !== undefined) payload.progress = updates.progress;
      if (updates.budget !== undefined) payload.budget = updates.budget;
      if (updates.spent !== undefined) payload.spent = updates.spent;

      const res = await apiClient.patch<any>(`/projects/${id}`, payload);
      if (res && res.id) {
        const mapped = mapBackendProject(res);
        const projects = getItem<Project[]>(STORAGE_KEYS.PROJECTS, []);
        const idx = projects.findIndex((p) => p.id === id);
        if (idx !== -1) {
          projects[idx] = mapped;
          setItem(STORAGE_KEYS.PROJECTS, projects);
        }
        return mapped;
      }
    } catch (err) {
      console.warn(`Backend update failed for project ${id}, updating locally:`, err);
    }

    const projects = getItem<Project[]>(STORAGE_KEYS.PROJECTS, []);
    const index = projects.findIndex((p) => p.id === id);
    if (index === -1) throw new Error(`Project ${id} not found`);

    const updatedProject: Project = {
      ...projects[index],
      ...updates,
      updatedAt: new Date().toISOString(),
    };

    projects[index] = updatedProject;
    setItem(STORAGE_KEYS.PROJECTS, projects);
    return updatedProject;
  },

  async deleteProject(id: string): Promise<boolean> {
    try {
      await apiClient.delete(`/projects/${id}`);
    } catch (err) {
      console.warn(`Backend deletion failed for project ${id}:`, err);
    }

    const projects = getItem<Project[]>(STORAGE_KEYS.PROJECTS, []);
    const filtered = projects.filter((p) => p.id !== id);
    setItem(STORAGE_KEYS.PROJECTS, filtered);
    return true;
  },

  async getProjectFiles(projectId: string): Promise<ProjectFile[]> {
    const files = getItem<ProjectFile[]>(STORAGE_KEYS.PROJECT_FILES, []);
    const users = getItem<User[]>(STORAGE_KEYS.USERS, []);
    return files.map((f) => ({
      ...f,
      uploader: users.find((u) => u.id === f.uploadedBy),
    }));
  },

  async uploadProjectFile(
    projectId: string,
    fileData: { name: string; size: number; type: string; userId: string; file?: File }
  ): Promise<ProjectFile> {
    const files = getItem<ProjectFile[]>(STORAGE_KEYS.PROJECT_FILES, []);
    const users = getItem<User[]>(STORAGE_KEYS.USERS, []);
    const newFile: ProjectFile = {
      id: `file_${Date.now()}`,
      name: fileData.name,
      size: fileData.size,
      type: fileData.type,
      uploadedBy: fileData.userId,
      uploadedAt: new Date().toISOString(),
      url: '#',
    };
    const updated = [newFile, ...files];
    setItem(STORAGE_KEYS.PROJECT_FILES, updated);
    return {
      ...newFile,
      uploader: users.find((u) => u.id === fileData.userId),
    };
  },
};

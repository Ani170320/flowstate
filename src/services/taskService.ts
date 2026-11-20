import { Task, TaskStatus, Priority, Comment, Subtask, FilterOptions, User, Project } from '@/types';
import { apiClient } from '@/lib/api-client';
import { projectService } from '@/services/projectService';
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

function mapBackendTask(t: any, projects: { id: string; name: string; key: string }[] = []): Task {
  const proj = projects.find((p) => p.id === t.project_id);
  return {
    id: t.id,
    projectId: t.project_id,
    projectName: proj ? proj.name : 'Flowstate Project',
    projectKey: proj ? proj.key : (t.key ? t.key.split('-')[0] : 'FLW'),
    taskNumber: t.task_number || 100,
    key: t.key || `FLW-${t.task_number || 100}`,
    title: t.title,
    description: t.description || '',
    status: t.status || 'todo',
    priority: t.priority || 'medium',
    assigneeId: t.assignee_id,
    assignee: t.assignee ? mapBackendUser(t.assignee) : undefined,
    creatorId: t.creator_id || '',
    creator: t.creator ? mapBackendUser(t.creator) : undefined,
    dueDate: t.due_date || '',
    startDate: t.start_date || (t.created_at ? t.created_at.split('T')[0] : undefined),
    estimatedHours: t.estimated_hours ? Number(t.estimated_hours) : undefined,
    actualHours: t.actual_hours ? Number(t.actual_hours) : undefined,
    order: typeof t.order === 'number' ? t.order : 1000,
    labels: (t.labels || []).map((l: any) => (typeof l === 'string' ? l : l.name)),
    subtasks: (t.subtasks || []).map((st: any) => ({
      id: st.id,
      title: st.title,
      completed: Boolean(st.completed),
    })),
    commentsCount: t.comments_count || 0,
    createdAt: t.created_at || new Date().toISOString(),
    updatedAt: t.updated_at || new Date().toISOString(),
  };
}

export const taskService = {
  async getTasks(filters?: FilterOptions): Promise<Task[]> {
    try {
      const projects = await projectService.getProjects();
      let targetProjectIds: string[] = [];

      if (filters?.projectId && filters.projectId !== 'all') {
        targetProjectIds = [filters.projectId];
      } else {
        targetProjectIds = projects.map((p) => p.id);
      }

      if (targetProjectIds.length > 0) {
        const results = await Promise.all(
          targetProjectIds.map(async (pid) => {
            try {
              const queryParams: any = {};
              if (filters?.status && filters.status !== 'all') queryParams.status = filters.status;
              if (filters?.priority && filters.priority !== 'all') queryParams.priority = filters.priority;
              if (filters?.assigneeId && filters.assigneeId !== 'all') queryParams.assignee_id = filters.assigneeId;

              const projectTasks = await apiClient.get<any[]>(`/projects/${pid}/tasks`, {
                params: queryParams,
              });
              return projectTasks.map((t) => mapBackendTask(t, projects));
            } catch {
              return [];
            }
          })
        );

        const flattened = results.flat();
        let filtered = flattened;
        if (filters?.search) {
          const q = filters.search.toLowerCase();
          filtered = filtered.filter(
            (t) =>
              t.title.toLowerCase().includes(q) ||
              t.description.toLowerCase().includes(q) ||
              t.key?.toLowerCase().includes(q)
          );
        }
        return filtered.sort((a, b) => a.order - b.order);
      }
      return [];
    } catch (err) {
      console.warn('Backend task list failed, falling back to local storage:', err);
    }

    // Local fallback
    const tasks = getItem<Task[]>(STORAGE_KEYS.TASKS, []);
    const users = getItem<User[]>(STORAGE_KEYS.USERS, []);
    const projects = getItem<Project[]>(STORAGE_KEYS.PROJECTS, []);

    let populated = tasks.map((t) => {
      const proj = projects.find((p) => p.id === t.projectId);
      return {
        ...t,
        projectName: proj ? proj.name : t.projectName,
        projectKey: proj ? proj.key : t.projectKey,
        key: t.key || (proj ? `${proj.key}-${t.taskNumber || 100}` : `FLW-${t.id.slice(-3)}`),
        assignee: users.find((u) => u.id === t.assigneeId),
        creator: users.find((u) => u.id === t.creatorId),
      };
    });

    if (filters) {
      if (filters.search) {
        const q = filters.search.toLowerCase();
        populated = populated.filter(
          (t) =>
            t.title.toLowerCase().includes(q) ||
            t.description.toLowerCase().includes(q) ||
            t.key?.toLowerCase().includes(q)
        );
      }
      if (filters.status && filters.status !== 'all') {
        populated = populated.filter((t) => t.status === filters.status);
      }
      if (filters.priority && filters.priority !== 'all') {
        populated = populated.filter((t) => t.priority === filters.priority);
      }
      if (filters.assigneeId && filters.assigneeId !== 'all') {
        populated = populated.filter((t) => t.assigneeId === filters.assigneeId);
      }
      if (filters.projectId && filters.projectId !== 'all') {
        populated = populated.filter((t) => t.projectId === filters.projectId);
      }
    }

    return populated.sort((a, b) => a.order - b.order);
  },

  async getTaskById(id: string): Promise<Task | null> {
    try {
      const t = await apiClient.get<any>(`/tasks/${id}`);
      if (t && t.id) {
        const projects = await projectService.getProjects();
        return mapBackendTask(t, projects);
      }
    } catch {
      // Fallback
    }
    const tasks = await this.getTasks();
    return tasks.find((t) => t.id === id) || null;
  },

  async getTasksByProject(projectId: string): Promise<Task[]> {
    return this.getTasks({ projectId });
  },

  async getTasksByAssignee(assigneeId: string): Promise<Task[]> {
    return this.getTasks({ assigneeId });
  },

  async createTask(data: {
    projectId: string;
    title: string;
    description: string;
    status?: TaskStatus;
    priority?: Priority;
    assigneeId?: string;
    creatorId: string;
    dueDate: string;
    labels?: string[];
    subtasks?: Subtask[];
    estimatedHours?: number;
    order?: number;
  }): Promise<Task> {
    try {
      const res = await apiClient.post<any>(`/projects/${data.projectId}/tasks`, {
        title: data.title,
        description: data.description,
        status: data.status || 'todo',
        priority: data.priority || 'medium',
        assignee_id: data.assigneeId || undefined,
        due_date: data.dueDate || undefined,
        estimated_hours: data.estimatedHours || undefined,
        order: data.order !== undefined ? data.order : undefined,
      });

      if (res && res.id) {
        const projects = await projectService.getProjects();
        const mapped = mapBackendTask(res, projects);
        const tasks = getItem<Task[]>(STORAGE_KEYS.TASKS, []);
        setItem(STORAGE_KEYS.TASKS, [mapped, ...tasks]);
        return mapped;
      }
    } catch (err) {
      console.warn('Backend task creation failed, creating locally:', err);
    }

    // Local fallback
    const tasks = getItem<Task[]>(STORAGE_KEYS.TASKS, []);
    const projects = getItem<Project[]>(STORAGE_KEYS.PROJECTS, []);
    const proj = projects.find((p) => p.id === data.projectId);
    const projTasks = tasks.filter((t) => t.projectId === data.projectId);
    const nextNumber = 100 + projTasks.length + 1;
    const key = proj ? `${proj.key}-${nextNumber}` : `FLW-${nextNumber}`;

    const newTask: Task = {
      id: `task_${Date.now()}`,
      projectId: data.projectId,
      projectName: proj?.name || 'Flowstate Project',
      projectKey: proj?.key || 'FLW',
      taskNumber: nextNumber,
      key,
      title: data.title,
      description: data.description,
      status: data.status || 'todo',
      priority: data.priority || 'medium',
      assigneeId: data.assigneeId,
      creatorId: data.creatorId,
      dueDate: data.dueDate,
      startDate: new Date().toISOString().split('T')[0],
      estimatedHours: data.estimatedHours || 8,
      labels: data.labels || ['Task'],
      subtasks: data.subtasks || [],
      commentsCount: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      order: projTasks.length,
    };

    const updated = [newTask, ...tasks];
    setItem(STORAGE_KEYS.TASKS, updated);
    return newTask;
  },

  async updateTask(id: string, updates: Partial<Task>): Promise<Task> {
    try {
      const payload: any = {};
      if (updates.title !== undefined) payload.title = updates.title;
      if (updates.description !== undefined) payload.description = updates.description;
      if (updates.status !== undefined) payload.status = updates.status;
      if (updates.priority !== undefined) payload.priority = updates.priority;
      if (updates.assigneeId !== undefined) {
        payload.assignee_id = updates.assigneeId || undefined;
        payload.unassign = !updates.assigneeId;
      }
      if (updates.dueDate !== undefined) payload.due_date = updates.dueDate;
      if (updates.startDate !== undefined) payload.start_date = updates.startDate;
      if (updates.estimatedHours !== undefined) payload.estimated_hours = updates.estimatedHours;
      if (updates.actualHours !== undefined) payload.actual_hours = updates.actualHours;
      if (updates.order !== undefined) payload.order = updates.order;

      const res = await apiClient.patch<any>(`/tasks/${id}`, payload);
      if (res && res.id) {
        const projects = await projectService.getProjects();
        const mapped = mapBackendTask(res, projects);
        const tasks = getItem<Task[]>(STORAGE_KEYS.TASKS, []);
        const idx = tasks.findIndex((t) => t.id === id);
        if (idx !== -1) {
          tasks[idx] = mapped;
          setItem(STORAGE_KEYS.TASKS, tasks);
        }
        return mapped;
      }
    } catch (err) {
      console.warn(`Backend update failed for task ${id}:`, err);
    }

    const tasks = getItem<Task[]>(STORAGE_KEYS.TASKS, []);
    const index = tasks.findIndex((t) => t.id === id);
    if (index === -1) throw new Error(`Task ${id} not found`);

    const updatedTask: Task = {
      ...tasks[index],
      ...updates,
      updatedAt: new Date().toISOString(),
    };

    tasks[index] = updatedTask;
    setItem(STORAGE_KEYS.TASKS, tasks);
    return updatedTask;
  },

  async updateTaskStatus(id: string, status: TaskStatus, newOrder?: number): Promise<Task> {
    try {
      const res = await apiClient.patch<any>(`/tasks/${id}/status`, { status });
      if (res && res.id) {
        const projects = await projectService.getProjects();
        return mapBackendTask(res, projects);
      }
    } catch (err) {
      console.warn(`Backend status update failed for task ${id}:`, err);
    }

    const tasks = getItem<Task[]>(STORAGE_KEYS.TASKS, []);
    const index = tasks.findIndex((t) => t.id === id);
    if (index === -1) throw new Error(`Task ${id} not found`);

    tasks[index].status = status;
    if (newOrder !== undefined) {
      tasks[index].order = newOrder;
    }
    tasks[index].updatedAt = new Date().toISOString();

    setItem(STORAGE_KEYS.TASKS, tasks);
    return tasks[index];
  },

  async deleteTask(id: string): Promise<boolean> {
    try {
      await apiClient.delete(`/tasks/${id}`);
    } catch (err) {
      console.warn(`Backend deletion failed for task ${id}:`, err);
    }

    const tasks = getItem<Task[]>(STORAGE_KEYS.TASKS, []);
    const filtered = tasks.filter((t) => t.id !== id);
    setItem(STORAGE_KEYS.TASKS, filtered);
    return true;
  },

  async addSubtask(taskId: string, title: string): Promise<Subtask> {
    try {
      const res = await apiClient.post<any>(`/tasks/${taskId}/subtasks`, { title });
      if (res && res.id) {
        return {
          id: res.id,
          title: res.title,
          completed: Boolean(res.completed),
        };
      }
    } catch (err) {
      console.warn(`Backend subtask add failed for task ${taskId}:`, err);
    }

    const tasks = getItem<Task[]>(STORAGE_KEYS.TASKS, []);
    const task = tasks.find((t) => t.id === taskId);
    if (!task) throw new Error(`Task ${taskId} not found`);

    const newSubtask: Subtask = {
      id: `st_${Date.now()}`,
      title,
      completed: false,
    };

    task.subtasks = [...(task.subtasks || []), newSubtask];
    task.updatedAt = new Date().toISOString();
    setItem(STORAGE_KEYS.TASKS, tasks);
    return newSubtask;
  },

  async toggleSubtask(taskId: string, subtaskId: string): Promise<boolean> {
    const tasks = getItem<Task[]>(STORAGE_KEYS.TASKS, []);
    const task = tasks.find((t) => t.id === taskId);
    const targetSubtask = task?.subtasks?.find((s) => s.id === subtaskId);
    const newCompleted = targetSubtask ? !targetSubtask.completed : true;

    try {
      await apiClient.patch(`/tasks/${taskId}/subtasks/${subtaskId}`, {
        completed: newCompleted,
      });
    } catch {
      // Ignore or fallback
    }

    if (!task) return false;
    task.subtasks = (task.subtasks || []).map((st) =>
      st.id === subtaskId ? { ...st, completed: !st.completed } : st
    );
    task.updatedAt = new Date().toISOString();
    setItem(STORAGE_KEYS.TASKS, tasks);
    return true;
  },

  async getComments(taskId: string): Promise<Comment[]> {
    try {
      const res = await apiClient.get<any>(`/tasks/${taskId}/comments`);
      const items = Array.isArray(res) ? res : res.items || [];
      if (items.length > 0) {
        return items.map((c: any) => ({
          id: c.id,
          taskId: c.task_id,
          authorId: c.author_id,
          author: c.author ? mapBackendUser(c.author) : undefined,
          content: c.content,
          createdAt: c.created_at,
        }));
      }
    } catch (err) {
      console.warn(`Backend get comments failed for task ${taskId}:`, err);
    }

    const comments = getItem<Comment[]>(STORAGE_KEYS.COMMENTS, []);
    const users = getItem<User[]>(STORAGE_KEYS.USERS, []);

    return comments
      .filter((c) => c.taskId === taskId)
      .map((c) => ({
        ...c,
        author: users.find((u) => u.id === c.authorId),
      }))
      .sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());
  },

  async addComment(taskId: string, authorId: string, content: string): Promise<Comment> {
    try {
      const res = await apiClient.post<any>(`/tasks/${taskId}/comments`, { content });
      if (res && res.id) {
        return {
          id: res.id,
          taskId: res.task_id,
          authorId: res.author_id,
          author: res.author ? mapBackendUser(res.author) : undefined,
          content: res.content,
          createdAt: res.created_at,
        };
      }
    } catch (err) {
      console.warn(`Backend comment post failed for task ${taskId}:`, err);
    }

    const comments = getItem<Comment[]>(STORAGE_KEYS.COMMENTS, []);
    const users = getItem<User[]>(STORAGE_KEYS.USERS, []);
    const tasks = getItem<Task[]>(STORAGE_KEYS.TASKS, []);

    const newComment: Comment = {
      id: `com_${Date.now()}`,
      taskId,
      authorId,
      content,
      createdAt: new Date().toISOString(),
    };

    const updatedComments = [...comments, newComment];
    setItem(STORAGE_KEYS.COMMENTS, updatedComments);

    const task = tasks.find((t) => t.id === taskId);
    if (task) {
      task.commentsCount = (task.commentsCount || 0) + 1;
      setItem(STORAGE_KEYS.TASKS, tasks);
    }

    return {
      ...newComment,
      author: users.find((u) => u.id === authorId),
    };
  },

  async getAttachments(taskId: string): Promise<any[]> {
    try {
      const res = await apiClient.get<any>(`/tasks/${taskId}/attachments`);
      return res.items || [];
    } catch {
      return [];
    }
  },

  async uploadAttachment(taskId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post(`/tasks/${taskId}/attachments`, formData);
  },

  async deleteAttachment(attachmentId: string): Promise<boolean> {
    try {
      await apiClient.delete(`/attachments/${attachmentId}`);
      return true;
    } catch {
      return false;
    }
  },
};

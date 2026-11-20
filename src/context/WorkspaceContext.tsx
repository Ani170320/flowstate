'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { Project, Task, Team, Activity, Notification, TaskStatus, Priority, Subtask, Comment } from '@/types';
import { projectService } from '@/services/projectService';
import { taskService } from '@/services/taskService';
import { teamService } from '@/services/teamService';
import { activityService } from '@/services/activityService';
import { notificationService } from '@/services/notificationService';
import { SYNC_EVENT } from '@/lib/storage/local-storage';
import { useAuth } from './AuthContext';
import { useToast } from './ToastContext';

interface WorkspaceContextType {
  projects: Project[];
  tasks: Task[];
  teams: Team[];
  activities: Activity[];
  notifications: Notification[];
  unreadNotificationsCount: number;
  isLoading: boolean;
  refreshData: () => Promise<void>;

  // Project operations
  createProject: (data: Parameters<typeof projectService.createProject>[0]) => Promise<Project>;
  updateProject: (id: string, updates: Partial<Project>) => Promise<Project>;
  deleteProject: (id: string) => Promise<boolean>;

  // Task operations
  createTask: (data: Parameters<typeof taskService.createTask>[0]) => Promise<Task>;
  updateTask: (id: string, updates: Partial<Task>) => Promise<Task>;
  updateTaskStatus: (id: string, status: TaskStatus, newOrder?: number) => Promise<Task>;
  deleteTask: (id: string) => Promise<boolean>;
  addSubtask: (taskId: string, title: string) => Promise<Subtask>;
  toggleSubtask: (taskId: string, subtaskId: string) => Promise<boolean>;
  addComment: (taskId: string, content: string) => Promise<Comment>;

  // Team operations
  createTeam: (data: Parameters<typeof teamService.createTeam>[0]) => Promise<Team>;

  // Notification operations
  markNotificationRead: (id: string) => Promise<void>;
  markAllNotificationsRead: () => Promise<void>;

  // UI state & Modals
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
  isCreateTaskOpen: boolean;
  defaultProjectId?: string;
  openCreateTask: (projectId?: string) => void;
  closeCreateTask: () => void;

  isCreateProjectOpen: boolean;
  projectToEdit: Project | null;
  openCreateProject: (project?: Project) => void;
  closeCreateProject: () => void;

  isSearchOpen: boolean;
  openSearch: () => void;
  closeSearch: () => void;

  selectedTask: Task | null;
  openTaskDetail: (task: Task) => void;
  closeTaskDetail: () => void;

  // AI Copilot Modal
  isCopilotOpen: boolean;
  openCopilot: () => void;
  closeCopilot: () => void;
  toggleCopilot: () => void;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const { success, error } = useToast();

  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // UI State
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isCreateTaskOpen, setIsCreateTaskOpen] = useState(false);
  const [defaultProjectId, setDefaultProjectId] = useState<string | undefined>(undefined);
  const [isCreateProjectOpen, setIsCreateProjectOpen] = useState(false);
  const [projectToEdit, setProjectToEdit] = useState<Project | null>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);

  const refreshData = useCallback(async () => {
    try {
      const [p, t, tm, a, n] = await Promise.all([
        projectService.getProjects(),
        taskService.getTasks(),
        teamService.getTeams(),
        activityService.getActivities(30),
        notificationService.getNotifications(user.id),
      ]);
      setProjects(p);
      setTasks(t);
      setTeams(tm);
      setActivities(a);
      setNotifications(n);

      // Keep selectedTask in sync if open
      if (selectedTask) {
        const found = t.find((task) => task.id === selectedTask.id);
        if (found) setSelectedTask(found);
      }
    } catch (err) {
      console.error('Failed to load workspace data:', err);
    } finally {
      setIsLoading(false);
    }
  }, [user.id, selectedTask]);

  const broadcastSync = useCallback(() => {
    try {
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event(SYNC_EVENT));
        if ('BroadcastChannel' in window) {
          const bc = new BroadcastChannel('flowstate_workspace_channel');
          bc.postMessage({ type: 'SYNC', timestamp: Date.now() });
          bc.close();
        }
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    refreshData();

    const handleSync = () => {
      refreshData();
    };

    window.addEventListener(SYNC_EVENT, handleSync);

    let bc: BroadcastChannel | null = null;
    if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
      bc = new BroadcastChannel('flowstate_workspace_channel');
      bc.onmessage = () => {
        refreshData();
      };
    }

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        refreshData();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleVisibilityChange);

    return () => {
      window.removeEventListener(SYNC_EVENT, handleSync);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleVisibilityChange);
      if (bc) bc.close();
    };
  }, [refreshData]);

  // Global Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+K or Ctrl+K for search
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
      // 'c' hotkey to create task when not in an input
      if (
        e.key.toLowerCase() === 'c' &&
        !['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement)?.tagName) &&
        !e.metaKey &&
        !e.ctrlKey &&
        !e.altKey
      ) {
        e.preventDefault();
        setIsCreateTaskOpen(true);
      }
      // Esc to close modals
      if (e.key === 'Escape') {
        if (isSearchOpen) setIsSearchOpen(false);
        if (isCreateTaskOpen) setIsCreateTaskOpen(false);
        if (isCreateProjectOpen) setIsCreateProjectOpen(false);
        if (selectedTask) setSelectedTask(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isSearchOpen, isCreateTaskOpen, isCreateProjectOpen, selectedTask]);

  // Project Actions
  const createProject = async (data: Parameters<typeof projectService.createProject>[0]) => {
    try {
      const newProj = await projectService.createProject(data);
      await activityService.logActivity({
        userId: user.id,
        action: 'created_project',
        targetType: 'project',
        targetId: newProj.id,
        targetTitle: newProj.name,
        projectId: newProj.id,
        projectName: newProj.name,
        details: `Created project ${newProj.name}`,
      });
      await refreshData();
      broadcastSync();
      success('Project Created', `Project "${newProj.name}" is now active.`);
      return newProj;
    } catch (err: any) {
      error('Failed to create project', err.message);
      throw err;
    }
  };

  const updateProject = async (id: string, updates: Partial<Project>) => {
    try {
      const updated = await projectService.updateProject(id, updates);
      await activityService.logActivity({
        userId: user.id,
        action: 'updated_project',
        targetType: 'project',
        targetId: id,
        targetTitle: updated.name,
        projectId: id,
        projectName: updated.name,
        details: `Updated project settings`,
      });
      await refreshData();
      broadcastSync();
      success('Project Updated', `Saved changes to "${updated.name}".`);
      return updated;
    } catch (err: any) {
      error('Failed to update project', err.message);
      throw err;
    }
  };

  const deleteProject = async (id: string) => {
    try {
      const p = projects.find((proj) => proj.id === id);
      await projectService.deleteProject(id);
      await refreshData();
      broadcastSync();
      success('Project Deleted', p ? `"${p.name}" has been removed.` : 'Project deleted.');
      return true;
    } catch (err: any) {
      error('Failed to delete project', err.message);
      throw err;
    }
  };

  // Task Actions
  const createTask = async (data: Parameters<typeof taskService.createTask>[0]) => {
    try {
      const newTask = await taskService.createTask(data);
      await activityService.logActivity({
        userId: user.id,
        action: 'created_task',
        targetType: 'task',
        targetId: newTask.id,
        targetTitle: newTask.title,
        projectId: newTask.projectId,
        projectName: newTask.projectName,
        details: `Created task ${newTask.key}: "${newTask.title}"`,
      });
      await refreshData();
      broadcastSync();
      success('Task Created', `Added ${newTask.key}: ${newTask.title}`);
      return newTask;
    } catch (err: any) {
      error('Failed to create task', err.message);
      throw err;
    }
  };

  const updateTask = async (id: string, updates: Partial<Task>) => {
    try {
      const updated = await taskService.updateTask(id, updates);
      await activityService.logActivity({
        userId: user.id,
        action: updates.status ? 'status_change' : 'updated_task',
        targetType: 'task',
        targetId: id,
        targetTitle: updated.title,
        projectId: updated.projectId,
        projectName: updated.projectName,
        details: updates.status ? `Changed status to ${updates.status}` : `Updated task details`,
      });
      await refreshData();
      broadcastSync();
      return updated;
    } catch (err: any) {
      error('Failed to update task', err.message);
      throw err;
    }
  };

  const updateTaskStatus = async (id: string, status: TaskStatus, newOrder?: number) => {
    // Optimistic UI update
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status, order: newOrder !== undefined ? newOrder : t.order } : t))
    );
    try {
      const updated = await taskService.updateTaskStatus(id, status, newOrder);
      await activityService.logActivity({
        userId: user.id,
        action: 'status_change',
        targetType: 'task',
        targetId: id,
        targetTitle: updated.title,
        projectId: updated.projectId,
        projectName: updated.projectName,
        details: `Moved to ${status.replace('_', ' ').toUpperCase()}`,
      });
      await refreshData();
      broadcastSync();
      return updated;
    } catch (err: any) {
      refreshData();
      error('Failed to move task', err.message);
      throw err;
    }
  };

  const deleteTask = async (id: string) => {
    try {
      await taskService.deleteTask(id);
      if (selectedTask?.id === id) setSelectedTask(null);
      await refreshData();
      broadcastSync();
      success('Task Deleted', 'Task was permanently removed.');
      return true;
    } catch (err: any) {
      error('Failed to delete task', err.message);
      throw err;
    }
  };

  const addSubtask = async (taskId: string, title: string) => {
    const st = await taskService.addSubtask(taskId, title);
    await refreshData();
    broadcastSync();
    return st;
  };

  const toggleSubtask = async (taskId: string, subtaskId: string) => {
    const res = await taskService.toggleSubtask(taskId, subtaskId);
    await refreshData();
    broadcastSync();
    return res;
  };

  const addComment = async (taskId: string, content: string) => {
    const com = await taskService.addComment(taskId, user.id, content);
    await activityService.logActivity({
      userId: user.id,
      action: 'commented',
      targetType: 'task',
      targetId: taskId,
      targetTitle: selectedTask?.title || 'Task',
      details: content.substring(0, 50),
    });
    await refreshData();
    broadcastSync();
    return com;
  };

  const createTeam = async (data: Parameters<typeof teamService.createTeam>[0]) => {
    const newTeam = await teamService.createTeam(data);
    await refreshData();
    broadcastSync();
    success('Team Created', `Team "${newTeam.name}" has been formed.`);
    return newTeam;
  };

  const markNotificationRead = async (id: string) => {
    await notificationService.markAsRead(id);
    await refreshData();
  };

  const markAllNotificationsRead = async () => {
    await notificationService.markAllAsRead(user.id);
    await refreshData();
    success('Notifications Marked as Read', 'All notifications are now cleared.');
  };

  const unreadNotificationsCount = notifications.filter((n) => !n.isRead).length;

  return (
    <WorkspaceContext.Provider
      value={{
        projects,
        tasks,
        teams,
        activities,
        notifications,
        unreadNotificationsCount,
        isLoading,
        refreshData,
        createProject,
        updateProject,
        deleteProject,
        createTask,
        updateTask,
        updateTaskStatus,
        deleteTask,
        addSubtask,
        toggleSubtask,
        addComment,
        createTeam,
        markNotificationRead,
        markAllNotificationsRead,
        isSidebarCollapsed,
        toggleSidebar: () => setIsSidebarCollapsed((prev) => !prev),
        isCreateTaskOpen,
        defaultProjectId,
        openCreateTask: (projId) => {
          setDefaultProjectId(projId);
          setIsCreateTaskOpen(true);
        },
        closeCreateTask: () => {
          setIsCreateTaskOpen(false);
          setDefaultProjectId(undefined);
        },
        isCreateProjectOpen,
        projectToEdit,
        openCreateProject: (proj) => {
          setProjectToEdit(proj || null);
          setIsCreateProjectOpen(true);
        },
        closeCreateProject: () => {
          setIsCreateProjectOpen(false);
          setProjectToEdit(null);
        },
        isSearchOpen,
        openSearch: () => setIsSearchOpen(true),
        closeSearch: () => setIsSearchOpen(false),
        selectedTask,
        openTaskDetail: (t) => setSelectedTask(t),
        closeTaskDetail: () => setSelectedTask(null),
        isCopilotOpen,
        openCopilot: () => setIsCopilotOpen(true),
        closeCopilot: () => setIsCopilotOpen(false),
        toggleCopilot: () => setIsCopilotOpen((prev) => !prev),
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
}

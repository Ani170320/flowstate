import {
  SEED_USERS,
  SEED_PROJECTS,
  SEED_TASKS,
  SEED_TEAMS,
  SEED_ACTIVITIES,
  SEED_NOTIFICATIONS,
  SEED_COMMENTS,
  SEED_PROJECT_FILES,
} from '@/lib/mock-data/seed';

export const STORAGE_KEYS = {
  USERS: 'flowstate_users',
  CURRENT_USER: 'flowstate_current_user',
  PROJECTS: 'flowstate_projects',
  TASKS: 'flowstate_tasks',
  TEAMS: 'flowstate_teams',
  ACTIVITIES: 'flowstate_activities',
  NOTIFICATIONS: 'flowstate_notifications',
  COMMENTS: 'flowstate_comments',
  PROJECT_FILES: 'flowstate_project_files',
  WORKSPACE_SETTINGS: 'flowstate_workspace_settings',
  THEME: 'flowstate_theme',
} as const;

export const SYNC_EVENT = 'flowstate_storage_sync';

export function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

export function initializeLocalStorage(): void {
  if (!isBrowser()) return;

  try {
    const saved = localStorage.getItem('flowstate_saved_user');
    if (saved && !localStorage.getItem(STORAGE_KEYS.CURRENT_USER)) {
      try {
        const parsed = JSON.parse(saved);
        localStorage.setItem(STORAGE_KEYS.CURRENT_USER, JSON.stringify({
          id: parsed.id || 'usr_me',
          name: parsed.name || parsed.email?.split('@')[0] || 'User',
          email: parsed.email,
          avatar: parsed.avatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(parsed.email || 'user')}`,
          role: parsed.role || 'owner',
          createdAt: new Date().toISOString(),
        }));
      } catch {}
    }
  } catch (error) {
    console.error('Error initializing Flowstate localStorage:', error);
  }
}

export function getItem<T>(key: string, defaultValue: T): T {
  if (!isBrowser()) return defaultValue;
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return defaultValue;
    return JSON.parse(raw) as T;
  } catch (error) {
    console.error(`Error reading ${key} from localStorage:`, error);
    return defaultValue;
  }
}

export function setItem<T>(key: string, value: T): void {
  if (!isBrowser()) return;
  try {
    localStorage.setItem(key, JSON.stringify(value));
    window.dispatchEvent(new CustomEvent(SYNC_EVENT, { detail: { key } }));
  } catch (error) {
    console.error(`Error saving ${key} to localStorage:`, error);
  }
}

export function resetToSeedData(): void {
  if (!isBrowser()) return;
  try {
    localStorage.setItem(STORAGE_KEYS.USERS, JSON.stringify(SEED_USERS));
    localStorage.setItem(STORAGE_KEYS.CURRENT_USER, JSON.stringify(SEED_USERS[0]));
    localStorage.setItem(STORAGE_KEYS.PROJECTS, JSON.stringify(SEED_PROJECTS));
    localStorage.setItem(STORAGE_KEYS.TASKS, JSON.stringify(SEED_TASKS));
    localStorage.setItem(STORAGE_KEYS.TEAMS, JSON.stringify(SEED_TEAMS));
    localStorage.setItem(STORAGE_KEYS.ACTIVITIES, JSON.stringify(SEED_ACTIVITIES));
    localStorage.setItem(STORAGE_KEYS.NOTIFICATIONS, JSON.stringify(SEED_NOTIFICATIONS));
    localStorage.setItem(STORAGE_KEYS.COMMENTS, JSON.stringify(SEED_COMMENTS));
    localStorage.setItem(STORAGE_KEYS.PROJECT_FILES, JSON.stringify(SEED_PROJECT_FILES));
    window.dispatchEvent(new CustomEvent(SYNC_EVENT, { detail: { key: 'ALL' } }));
  } catch (error) {
    console.error('Error resetting to seed data:', error);
  }
}

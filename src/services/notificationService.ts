import { Notification, User } from '@/types';
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

function mapBackendNotification(n: any): Notification {
  return {
    id: n.id,
    userId: n.user_id,
    title: n.title,
    message: n.message,
    type: n.type || 'system',
    isRead: Boolean(n.is_read),
    link: n.link,
    createdAt: n.created_at || new Date().toISOString(),
    senderId: n.sender_id,
    sender: n.sender ? mapBackendUser(n.sender) : undefined,
  };
}

export const notificationService = {
  async getNotifications(userId?: string): Promise<Notification[]> {
    try {
      const res = await apiClient.get<any>('/notifications');
      const items = Array.isArray(res) ? res : res.items || [];
      if (items.length > 0) {
        const mapped = items.map(mapBackendNotification);
        setItem(STORAGE_KEYS.NOTIFICATIONS, mapped);
        return mapped;
      }
    } catch (err) {
      console.warn('Backend /notifications failed, falling back to local storage:', err);
    }

    const notifications = getItem<Notification[]>(STORAGE_KEYS.NOTIFICATIONS, []);
    const users = getItem<User[]>(STORAGE_KEYS.USERS, []);

    let filtered = notifications;
    if (userId) {
      filtered = notifications.filter((n) => n.userId === userId);
    }

    return filtered
      .map((notif) => ({
        ...notif,
        sender: notif.senderId ? users.find((u) => u.id === notif.senderId) : undefined,
      }))
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  },

  async markAsRead(id: string): Promise<boolean> {
    try {
      await apiClient.patch(`/notifications/${id}/read`);
    } catch (err) {
      console.warn(`Backend mark notification read failed for ${id}:`, err);
    }

    const notifications = getItem<Notification[]>(STORAGE_KEYS.NOTIFICATIONS, []);
    const notif = notifications.find((n) => n.id === id);
    if (!notif) return false;

    notif.isRead = true;
    setItem(STORAGE_KEYS.NOTIFICATIONS, notifications);
    return true;
  },

  async markAllAsRead(userId?: string): Promise<boolean> {
    try {
      await apiClient.patch('/notifications/read-all');
    } catch (err) {
      console.warn('Backend mark all notifications read failed:', err);
    }

    const notifications = getItem<Notification[]>(STORAGE_KEYS.NOTIFICATIONS, []);
    notifications.forEach((n) => {
      if (!userId || n.userId === userId) {
        n.isRead = true;
      }
    });
    setItem(STORAGE_KEYS.NOTIFICATIONS, notifications);
    return true;
  },

  async createNotification(data: {
    userId: string;
    title: string;
    message: string;
    type: Notification['type'];
    link?: string;
    senderId?: string;
  }): Promise<Notification> {
    const notifications = getItem<Notification[]>(STORAGE_KEYS.NOTIFICATIONS, []);
    const newNotification: Notification = {
      id: `notif_${Date.now()}`,
      userId: data.userId,
      title: data.title,
      message: data.message,
      type: data.type,
      link: data.link,
      isRead: false,
      senderId: data.senderId,
      createdAt: new Date().toISOString(),
    };

    const updated = [newNotification, ...notifications];
    setItem(STORAGE_KEYS.NOTIFICATIONS, updated);
    return newNotification;
  },
};

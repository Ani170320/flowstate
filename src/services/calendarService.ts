import { apiClient } from '@/lib/api-client';
import { Priority, TaskStatus, User } from '@/types';

export interface CalendarEvent {
  id: string;
  entityType: 'task' | 'project';
  entityId: string;
  title: string;
  key?: string;
  startDate?: string;
  dueDate?: string;
  date: string;
  status: string;
  priority?: Priority;
  color?: string;
  projectId?: string;
  projectName?: string;
  assignee?: User;
  isOverdue: boolean;
}

export interface CalendarUpcomingItem {
  id: string;
  entityType: 'task' | 'project';
  key?: string;
  title: string;
  projectName?: string;
  dueDate: string;
  daysRemaining: number;
  isOverdue: boolean;
  priority: Priority;
  status: string;
  assignee?: User;
}

export interface CalendarDay {
  date: string;
  eventsCount: number;
  events: CalendarEvent[];
}

export interface CalendarView {
  view: 'month' | 'week' | 'day';
  startDate: string;
  endDate: string;
  referenceDate: string;
  totalEvents: number;
  days: CalendarDay[];
}

export const calendarService = {
  async getCalendarView(view: 'month' | 'week' | 'day' = 'month', dateStr?: string): Promise<CalendarView | null> {
    try {
      const res = await apiClient.get<any>('/calendar', {
        params: {
          view,
          date: dateStr,
        },
      });

      return {
        view: res.view,
        startDate: res.start_date,
        endDate: res.end_date,
        referenceDate: res.reference_date,
        totalEvents: res.total_events,
        days: (res.days || []).map((d: any) => ({
          date: d.date,
          eventsCount: d.events_count,
          events: (d.events || []).map((e: any) => ({
            id: e.id,
            entityType: e.entity_type,
            entityId: e.entity_id,
            title: e.title,
            key: e.key,
            startDate: e.start_date,
            dueDate: e.due_date,
            date: e.date,
            status: e.status,
            priority: e.priority,
            color: e.color,
            projectId: e.project_id,
            projectName: e.project_name,
            assignee: e.assignee
              ? {
                  id: e.assignee.id,
                  name: e.assignee.name,
                  email: e.assignee.email,
                  avatar: e.assignee.avatar_url || '',
                  role: 'developer',
                  createdAt: e.assignee.created_at,
                }
              : undefined,
            isOverdue: e.is_overdue || false,
          })),
        })),
      };
    } catch (err) {
      console.warn('Calendar view API fallback:', err);
      return null;
    }
  },

  async getEvents(startDate: string, endDate: string): Promise<CalendarEvent[]> {
    try {
      const res = await apiClient.get<any[]>('/calendar/events', {
        params: {
          start_date: startDate,
          end_date: endDate,
        },
      });

      return res.map((e) => ({
        id: e.id,
        entityType: e.entity_type,
        entityId: e.entity_id,
        title: e.title,
        key: e.key,
        startDate: e.start_date,
        dueDate: e.due_date,
        date: e.date,
        status: e.status,
        priority: e.priority,
        color: e.color,
        projectId: e.project_id,
        projectName: e.project_name,
        assignee: e.assignee
          ? {
              id: e.assignee.id,
              name: e.assignee.name,
              email: e.assignee.email,
              avatar: e.assignee.avatar_url || '',
              role: 'developer',
              createdAt: e.assignee.created_at,
            }
          : undefined,
        isOverdue: e.is_overdue || false,
      }));
    } catch {
      return [];
    }
  },

  async getUpcoming(days = 14): Promise<CalendarUpcomingItem[]> {
    try {
      const res = await apiClient.get<any[]>('/calendar/upcoming', {
        params: { days },
      });

      return res.map((item) => ({
        id: item.id,
        entityType: item.entity_type,
        key: item.key,
        title: item.title,
        projectName: item.project_name,
        dueDate: item.due_date,
        daysRemaining: item.days_remaining,
        isOverdue: item.is_overdue,
        priority: item.priority,
        status: item.status,
        assignee: item.assignee
          ? {
              id: item.assignee.id,
              name: item.assignee.name,
              email: item.assignee.email,
              avatar: item.assignee.avatar_url || '',
              role: 'developer',
              createdAt: item.assignee.created_at,
            }
          : undefined,
      }));
    } catch {
      return [];
    }
  },
};

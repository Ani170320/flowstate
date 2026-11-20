'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, Organization } from '@/types';
import { authService } from '@/services/authService';
import { memberService } from '@/services/memberService';
import { apiClient } from '@/lib/api-client';
import { SEED_USERS } from '@/lib/mock-data/seed';
import { SYNC_EVENT } from '@/lib/storage/local-storage';
import { DEFAULT_ORG_ID } from '@/lib/utils';

interface AuthContextType {
  user: User;
  allUsers: User[];
  activeOrg: Organization | null;
  organizations: Organization[];
  isLoading: boolean;
  switchUser: (userId: string) => Promise<void>;
  switchOrganization: (orgId: string) => Promise<void>;
  updateProfile: (updates: Partial<User>) => Promise<void>;
  refreshMembers: () => Promise<void>;
  login: (email: string, password?: string) => Promise<void>;
  register: (data: {
    name: string;
    email: string;
    password?: string;
    phone?: string;
    workspaceName?: string;
    workspaceSlug?: string;
    plan?: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
}

const DEFAULT_INITIAL_USER: User = {
  id: '',
  name: '',
  email: '',
  avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=user',
  role: 'owner',
  createdAt: '2026-01-01T00:00:00Z',
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User>(DEFAULT_INITIAL_USER);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [activeOrg, setActiveOrg] = useState<Organization | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadUserData = useCallback(async () => {
    try {
      // 1. On client mount, load cached user snapshot if present
      if (typeof window !== 'undefined') {
        const stored = localStorage.getItem('flowstate_current_user');
        if (stored) {
          try {
            setUser(JSON.parse(stored));
          } catch {}
        }
      }

      // 2. Try real backend session
      const session = await authService.getSession().catch(() => null);

      if (session) {
        setUser(session.user);
        if (session.activeOrg) setActiveOrg(session.activeOrg);
        if (session.organizations) setOrganizations(session.organizations);
      } else {
        const current = await authService.getCurrentUser();
        setUser(current);
      }

      // 3. Load members of active organization
      const members = await memberService.getMembers().catch(() => []);
      setAllUsers(members);
    } catch (err) {
      console.error('Failed to load auth user:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshMembers = useCallback(async () => {
    try {
      const members = await memberService.getMembers().catch(() => []);
      setAllUsers(members);
    } catch (err) {
      console.warn('Failed to refresh members:', err);
    }
  }, []);

  useEffect(() => {
    loadUserData();

    const handleSync = () => {
      loadUserData();
    };

    const handleAuthExpired = () => {
      console.warn('Flowstate authentication session expired.');
    };

    window.addEventListener(SYNC_EVENT, handleSync);
    window.addEventListener('flowstate:auth_expired', handleAuthExpired);

    return () => {
      window.removeEventListener(SYNC_EVENT, handleSync);
      window.removeEventListener('flowstate:auth_expired', handleAuthExpired);
    };
  }, [loadUserData]);

  const switchUser = async (userId: string) => {
    try {
      const switched = await authService.switchUser(userId);
      setUser(switched);
      const members = await memberService.getMembers();
      setAllUsers(members);
    } catch (err) {
      console.warn('Backend switchUser fallback:', err);
      const fallback = allUsers.find((u) => u.id === userId);
      if (fallback) setUser(fallback);
    }
  };

  const switchOrganization = async (orgId: string) => {
    try {
      const switched = await authService.switchOrganization(orgId);
      setActiveOrg(switched);
      await loadUserData();
    } catch (err) {
      console.error('Failed to switch organization:', err);
    }
  };

  const updateProfile = async (updates: Partial<User>) => {
    let finalUser: User;
    try {
      const updated = await authService.updateProfile(updates);
      finalUser = {
        ...user,
        ...updated,
        role: user.role,
      };
    } catch (err) {
      console.warn('Backend update profile failed, falling back:', err);
      const updated = await memberService.updateMember(user.id, updates);
      finalUser = {
        ...user,
        ...updated,
      };
    }

    setUser(finalUser);

    // Update in allUsers list immediately
    setAllUsers((prev) =>
      prev.map((u) => (u.id === finalUser.id || u.email === finalUser.email ? finalUser : u))
    );

    // Persist in localStorage so refreshes and re-renders keep the updated user
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('flowstate_saved_user');
        if (saved) {
          const parsed = JSON.parse(saved);
          parsed.name = finalUser.name;
          parsed.email = finalUser.email;
          localStorage.setItem('flowstate_saved_user', JSON.stringify(parsed));
        }
        localStorage.setItem('flowstate_current_user', JSON.stringify(finalUser));
      } catch {}
    }
  };

  const login = async (email: string, password?: string) => {
    const res = await authService.login(email, password);
    setUser(res.user);
    await loadUserData();
  };

  const register = async (data: {
    name: string;
    email: string;
    password?: string;
    phone?: string;
    workspaceName?: string;
    workspaceSlug?: string;
    plan?: string;
  }) => {
    const res = await authService.register(data);
    setUser(res.user);
    await loadUserData();
  };

  const logout = async () => {
    await authService.logout();
    if (typeof window !== 'undefined') {
      localStorage.removeItem('flowstate_current_user');
      localStorage.removeItem('flowstate_saved_user');
      sessionStorage.removeItem('flowstate_prevent_auto_login');
    }
    setUser({
      id: '',
      name: '',
      email: '',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=guest',
      role: 'owner',
      createdAt: new Date().toISOString(),
    });
    setAllUsers([]);
    setActiveOrg(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        allUsers,
        activeOrg,
        organizations,
        isLoading,
        switchUser,
        switchOrganization,
        updateProfile,
        refreshMembers,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

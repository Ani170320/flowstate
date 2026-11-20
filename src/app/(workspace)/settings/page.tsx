'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { useTheme, ACCENT_OPTIONS } from '@/context/ThemeContext';
import { organizationService } from '@/services/organizationService';
import { resetToSeedData } from '@/lib/storage/local-storage';
import { Avatar } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { Input, Textarea } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import {
  User,
  Building2,
  Bell,
  Palette,
  ShieldCheck,
  RotateCcw,
  Check,
  Smartphone,
  KeyRound,
  Laptop,
  LogOut,
} from 'lucide-react';

export default function SettingsPage() {
  const router = useRouter();
  const { user, updateProfile, activeOrg, logout } = useAuth();
  const { success, info, error } = useToast();
  const {
    theme,
    accentColor,
    setTheme,
    setAccentColor,
    saveAppearance,
    isSaving: isSavingAppearance,
  } = useTheme();

  const [activeSection, setActiveSection] = useState<
    'profile' | 'workspace' | 'notifications' | 'appearance' | 'security'
  >('appearance');

  // Profile Form State
  const [name, setName] = useState(user.name);
  const [email, setEmail] = useState(user.email);
  const [title, setTitle] = useState(user.title || '');
  const [department, setDepartment] = useState(user.department || '');
  const [phone, setPhone] = useState(user.phone || '');
  const [bio, setBio] = useState(user.bio || '');
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  // Workspace Settings State
  const [workspaceName, setWorkspaceName] = useState(activeOrg?.name || 'Workspace');
  const [workspaceSlug, setWorkspaceSlug] = useState(activeOrg?.slug || 'workspace');
  const [timezone, setTimezone] = useState('America/San_Francisco');
  const [currency, setCurrency] = useState('USD ($)');
  const [isSavingWorkspace, setIsSavingWorkspace] = useState(false);

  // Notification Preferences State
  const [notifyAssignment, setNotifyAssignment] = useState(true);
  const [notifyDeadline, setNotifyDeadline] = useState(true);
  const [notifyMentions, setNotifyMentions] = useState(true);
  const [notifyDigest, setNotifyDigest] = useState(false);
  const [isSavingNotifications, setIsSavingNotifications] = useState(false);

  // Security State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(true);

  // Update local states when activeOrg or user changes
  useEffect(() => {
    if (activeOrg) {
      setWorkspaceName(activeOrg.name);
      setWorkspaceSlug(activeOrg.slug);

      organizationService
        .getWorkspaceSettings(activeOrg.id)
        .then((s) => {
          if (s.timezone) setTimezone(s.timezone);
          if (s.currency) setCurrency(`${s.currency} (${s.currency === 'USD' ? '$' : s.currency === 'EUR' ? '€' : '£'})`);
          if (s.notificationsEmail !== undefined) setNotifyAssignment(s.notificationsEmail);
          if (s.notificationsDesktop !== undefined) setNotifyMentions(s.notificationsDesktop);
        })
        .catch(() => {});
    }
  }, [activeOrg]);

  useEffect(() => {
    setName(user.name);
    setEmail(user.email);
    setTitle(user.title || '');
    setDepartment(user.department || '');
    setPhone(user.phone || '');
    setBio(user.bio || '');
  }, [user]);

  const handleSignOut = async (clearSavedUser: boolean = false) => {
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('flowstate_prevent_auto_login', 'true');
      if (clearSavedUser) {
        localStorage.removeItem('flowstate_saved_user');
      }
    }
    await logout();
    success('Signed Out', 'You have been safely signed out of FLOWSTATE.');
    router.push('/login');
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    try {
      await updateProfile({
        name,
        email,
        title,
        department,
        phone,
        bio,
      });
      success('Profile Updated', 'Your profile details have been saved.');
    } catch (err: any) {
      error('Update Failed', err?.message || 'Could not save profile details.');
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleSaveWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingWorkspace(true);
    try {
      if (activeOrg?.id) {
        await organizationService.updateOrganization(activeOrg.id, {
          name: workspaceName.trim(),
          slug: workspaceSlug.trim(),
        });
        const currCode = currency.includes('EUR') ? 'EUR' : currency.includes('GBP') ? 'GBP' : 'USD';
        await organizationService.updateWorkspaceSettings(activeOrg.id, {
          timezone,
          currency: currCode,
        });
      }
      success('Workspace Settings Saved', 'Workspace configuration updated.');
    } catch (err) {
      console.warn('Workspace save warning:', err);
      success('Workspace Settings Saved', 'Workspace configuration updated.');
    } finally {
      setIsSavingWorkspace(false);
    }
  };

  const handleSaveNotifications = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingNotifications(true);
    try {
      if (activeOrg?.id) {
        await organizationService.updateWorkspaceSettings(activeOrg.id, {
          notifications_email: notifyAssignment,
          notifications_desktop: notifyMentions,
        });
      }
      try {
        localStorage.setItem(
          'flowstate_notifications_pref',
          JSON.stringify({ notifyAssignment, notifyDeadline, notifyMentions, notifyDigest })
        );
      } catch {}
      success('Preferences Saved', 'Notification rules updated.');
    } finally {
      setIsSavingNotifications(false);
    }
  };

  const handleResetData = () => {
    if (
      confirm(
        'Reset all projects, tasks, comments and activities to initial seed data? Any newly created items will be restored.'
      )
    ) {
      resetToSeedData();
      info('Seed Data Restored', 'The workspace has been reset to initial seed state.');
    }
  };

  const navItems = [
    { id: 'profile', label: 'My Profile', icon: User },
    { id: 'workspace', label: 'Workspace', icon: Building2 },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'security', label: 'Security & Auth', icon: ShieldCheck },
  ] as const;

  return (
    <div className="space-y-6 max-w-5xl mx-auto animate-in fade-in duration-300">
      {/* Header */}
      <div className="pb-2 border-b border-[#252B36]">
        <h1 className="text-2xl font-bold tracking-tight text-[#F5F7FA]">Settings</h1>
        <p className="text-xs sm:text-sm text-[#929AAA] mt-1">
          Manage your account profile, workspace team configurations, and security preferences.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-start">
        {/* Settings Navigation Sidebar */}
        <div className="space-y-1 bg-[#10131A] p-2 rounded-2xl border border-[#252B36]">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-medium transition-all text-left cursor-pointer ${
                  isActive
                    ? 'bg-[#151922] text-[#F5F7FA] font-semibold border border-[#252B36] shadow-sm'
                    : 'text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#151922]/50'
                }`}
              >
                <Icon
                  className={`w-4 h-4 ${isActive ? 'text-[var(--accent)]' : 'text-[#929AAA]'}`}
                />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* Section Content Area */}
        <div className="md:col-span-3 bg-[#151922] border border-[#252B36] rounded-2xl p-6 shadow-sm">
          {/* PROFILE SECTION */}
          {activeSection === 'profile' && (
            <form onSubmit={handleSaveProfile} className="space-y-5">
              <div className="flex items-center gap-4 pb-4 border-b border-[#252B36]">
                <Avatar user={user} size="lg" />
                <div>
                  <h3 className="text-sm font-semibold text-[#F5F7FA]">{user.name}</h3>
                  <p className="text-xs text-[#929AAA]">{user.email}</p>
                  <p className="text-[10px] text-[var(--accent)] font-mono mt-0.5">Role: {user.role}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Full Name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
                <Input
                  label="Email Address"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Job Title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
                <Input
                  label="Department"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                />
              </div>

              <Input
                label="Phone Number"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />

              <Textarea
                label="Bio & Responsibilities"
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                rows={3}
              />

              <div className="flex items-center justify-between pt-3 border-t border-[#252B36]">
                <button
                  type="button"
                  onClick={() => handleSignOut(false)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Sign Out</span>
                </button>
                <Button type="submit" variant="primary" isLoading={isSavingProfile}>
                  Save Profile Changes
                </Button>
              </div>
            </form>
          )}

          {/* WORKSPACE SECTION */}
          {activeSection === 'workspace' && (
            <form onSubmit={handleSaveWorkspace} className="space-y-5">
              <div className="pb-3 border-b border-[#252B36]">
                <h3 className="text-sm font-semibold text-[#F5F7FA]">Workspace Organization</h3>
                <p className="text-xs text-[#929AAA] mt-0.5">
                  Manage organization metadata and data persistence controls.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Workspace Name"
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                />
                <Input
                  label="Workspace URL Slug"
                  value={workspaceSlug}
                  onChange={(e) => setWorkspaceSlug(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Select
                  label="Default Timezone"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                >
                  <option value="America/San_Francisco">America/San_Francisco (PST)</option>
                  <option value="America/New_York">America/New_York (EST)</option>
                  <option value="Europe/London">Europe/London (GMT)</option>
                  <option value="Europe/Berlin">Europe/Berlin (CET)</option>
                  <option value="Asia/Tokyo">Asia/Tokyo (JST)</option>
                </Select>

                <Select
                  label="Currency"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                >
                  <option value="USD ($)">USD ($)</option>
                  <option value="EUR (€)">EUR (€)</option>
                  <option value="GBP (£)">GBP (£)</option>
                </Select>
              </div>

              <div className="flex justify-end pt-3 border-t border-[#252B36]">
                <Button type="submit" variant="primary" isLoading={isSavingWorkspace}>
                  Save Workspace
                </Button>
              </div>

              {/* Danger Zone: Seed Data Reset */}
              <div className="mt-8 pt-6 border-t border-red-500/20 space-y-3">
                <h4 className="text-xs font-semibold text-red-400 uppercase tracking-wider">
                  Data Reset & Sandbox
                </h4>
                <p className="text-xs text-[#929AAA]">
                  Restore FLOWSTATE to the 5 seed projects, 20 tasks, 8 members, and 10 activity
                  logs in localStorage.
                </p>
                <Button
                  type="button"
                  variant="danger"
                  size="sm"
                  onClick={handleResetData}
                  className="gap-1.5 cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Restore Seed Data</span>
                </Button>
              </div>
            </form>
          )}

          {/* NOTIFICATION PREFERENCES SECTION */}
          {activeSection === 'notifications' && (
            <form onSubmit={handleSaveNotifications} className="space-y-5">
              <div className="pb-3 border-b border-[#252B36]">
                <h3 className="text-sm font-semibold text-[#F5F7FA]">Notification Rules</h3>
                <p className="text-xs text-[#929AAA] mt-0.5">
                  Configure when you want alerts and in-app updates.
                </p>
              </div>

              <div className="space-y-4">
                <label className="flex items-start justify-between p-3.5 bg-[#10131A] rounded-xl border border-[#252B36] cursor-pointer">
                  <div>
                    <p className="text-xs font-semibold text-[#F5F7FA]">Task Assignments</p>
                    <p className="text-[11px] text-[#929AAA] mt-0.5">
                      Receive an alert when someone assigns a task to you.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={notifyAssignment}
                    onChange={(e) => setNotifyAssignment(e.target.checked)}
                    className="w-4 h-4 rounded text-[var(--accent)] accent-[var(--accent)] cursor-pointer"
                  />
                </label>

                <label className="flex items-start justify-between p-3.5 bg-[#10131A] rounded-xl border border-[#252B36] cursor-pointer">
                  <div>
                    <p className="text-xs font-semibold text-[#F5F7FA]">Deadline Reminders</p>
                    <p className="text-[11px] text-[#929AAA] mt-0.5">
                      Notify 48 hours and 24 hours prior to ticket due dates.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={notifyDeadline}
                    onChange={(e) => setNotifyDeadline(e.target.checked)}
                    className="w-4 h-4 rounded text-[var(--accent)] accent-[var(--accent)] cursor-pointer"
                  />
                </label>

                <label className="flex items-start justify-between p-3.5 bg-[#10131A] rounded-xl border border-[#252B36] cursor-pointer">
                  <div>
                    <p className="text-xs font-semibold text-[#F5F7FA]">Comments & Mentions</p>
                    <p className="text-[11px] text-[#929AAA] mt-0.5">
                      Notify when a colleague mentions your username in a comment thread.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={notifyMentions}
                    onChange={(e) => setNotifyMentions(e.target.checked)}
                    className="w-4 h-4 rounded text-[var(--accent)] accent-[var(--accent)] cursor-pointer"
                  />
                </label>

                <label className="flex items-start justify-between p-3.5 bg-[#10131A] rounded-xl border border-[#252B36] cursor-pointer">
                  <div>
                    <p className="text-xs font-semibold text-[#F5F7FA]">Daily Morning Digest</p>
                    <p className="text-[11px] text-[#929AAA] mt-0.5">
                      Receive an AI-synthesized morning brief of standups and PR merges.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={notifyDigest}
                    onChange={(e) => setNotifyDigest(e.target.checked)}
                    className="w-4 h-4 rounded text-[var(--accent)] accent-[var(--accent)] cursor-pointer"
                  />
                </label>
              </div>

              <div className="flex justify-end pt-3 border-t border-[#252B36]">
                <Button type="submit" variant="primary" isLoading={isSavingNotifications}>
                  Save Preferences
                </Button>
              </div>
            </form>
          )}

          {/* APPEARANCE SECTION */}
          {activeSection === 'appearance' && (
            <div className="space-y-5">
              <div className="pb-3 border-b border-[#252B36]">
                <h3 className="text-sm font-semibold text-[#F5F7FA]">Theme & Interface</h3>
                <p className="text-xs text-[#929AAA] mt-0.5">
                  High-contrast dark mode design system inspired by Linear and Vercel.
                </p>
              </div>

              {/* Theme Selector */}
              <div>
                <label className="block text-xs font-medium text-[#929AAA] mb-2">Base Theme</label>
                <div className="grid grid-cols-2 gap-3">
                  <div
                    onClick={() => setTheme('dark')}
                    className={`p-4 rounded-xl border transition-all cursor-pointer ${
                      theme === 'dark'
                        ? 'bg-[#10131A] shadow-sm'
                        : 'bg-[#10131A]/60 border-[#252B36]'
                    }`}
                    style={{ borderColor: theme === 'dark' ? accentColor : undefined }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-[#F5F7FA]">Linear Dark</span>
                      {theme === 'dark' && (
                        <Check className="w-3.5 h-3.5" style={{ color: accentColor }} />
                      )}
                    </div>
                    <p className="text-[11px] text-[#929AAA]">
                      #0B0D12 primary background with #151922 card elevation.
                    </p>
                  </div>

                  <div
                    onClick={() => setTheme('midnight')}
                    className={`p-4 rounded-xl border transition-all cursor-pointer ${
                      theme === 'midnight'
                        ? 'bg-[#10131A] shadow-sm'
                        : 'bg-[#10131A]/60 border-[#252B36]'
                    }`}
                    style={{ borderColor: theme === 'midnight' ? accentColor : undefined }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-[#F5F7FA]">Deep Midnight</span>
                      {theme === 'midnight' && (
                        <Check className="w-3.5 h-3.5" style={{ color: accentColor }} />
                      )}
                    </div>
                    <p className="text-[11px] text-[#929AAA]">
                      Pure black #000000 with sharp subtle borders.
                    </p>
                  </div>
                </div>
              </div>

              {/* Accent Color */}
              <div>
                <label className="block text-xs font-medium text-[#929AAA] mb-2">
                  Accent Color
                </label>
                <div className="flex items-center gap-3">
                  {ACCENT_OPTIONS.map((opt) => (
                    <button
                      key={opt.hex}
                      title={opt.label}
                      onClick={() => setAccentColor(opt.hex)}
                      className={`w-8 h-8 rounded-full transition-transform cursor-pointer ${
                        accentColor === opt.hex
                          ? 'scale-110 ring-2 ring-white ring-offset-2 ring-offset-[#151922]'
                          : 'opacity-70 hover:opacity-100'
                      }`}
                      style={{ backgroundColor: opt.hex }}
                    />
                  ))}
                </div>
              </div>

              <div className="flex justify-end pt-3 border-t border-[#252B36]">
                <Button
                  onClick={saveAppearance}
                  variant="primary"
                  isLoading={isSavingAppearance}
                >
                  Save Appearance
                </Button>
              </div>
            </div>
          )}

          {/* SECURITY & AUTH SECTION */}
          {activeSection === 'security' && (
            <div className="space-y-6">
              <div className="pb-3 border-b border-[#252B36]">
                <h3 className="text-sm font-semibold text-[#F5F7FA]">Security & Authentication</h3>
                <p className="text-xs text-[#929AAA] mt-0.5">
                  FastAPI JWT auth readiness layer, session tokens and two-factor credentials.
                </p>
              </div>

              {/* Password update simulation */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-[#F5F7FA]">Change Password</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Current Password"
                    type="password"
                    placeholder="••••••••••••"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                  />
                  <Input
                    label="New Password"
                    type="password"
                    placeholder="••••••••••••"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                  />
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    success('Password Updated', 'Mock password hash refreshed.');
                    setCurrentPassword('');
                    setNewPassword('');
                  }}
                >
                  Update Password
                </Button>
              </div>

              {/* Two Factor Toggle */}
              <div className="pt-4 border-t border-[#252B36] flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-semibold text-[#F5F7FA]">
                    Two-Factor Authentication (2FA)
                  </h4>
                  <p className="text-[11px] text-[#929AAA] mt-0.5">
                    Enforce TOTP authenticator app verification on login.
                  </p>
                </div>
                <Button
                  variant={twoFactorEnabled ? 'primary' : 'outline'}
                  size="sm"
                  onClick={() => {
                    setTwoFactorEnabled(!twoFactorEnabled);
                    info(
                      '2FA Updated',
                      twoFactorEnabled ? '2FA disabled.' : '2FA hardware token active.'
                    );
                  }}
                >
                  {twoFactorEnabled ? 'Enabled' : 'Disabled'}
                </Button>
              </div>

              {/* Active Sessions */}
              <div className="pt-4 border-t border-[#252B36] space-y-3">
                <h4 className="text-xs font-semibold text-[#F5F7FA]">Active Sessions</h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-3 bg-[#10131A] rounded-xl border border-[#252B36] text-xs">
                    <div className="flex items-center gap-3">
                      <Laptop className="w-4 h-4 text-emerald-400" />
                      <div>
                        <p className="font-semibold text-[#F5F7FA]">
                          Current Session — Windows / Chrome
                        </p>
                        <p className="text-[10px] text-[#929AAA]">
                          IP: 127.0.0.1 • Localhost FastAPI JWT
                        </p>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 font-bold">
                      ACTIVE NOW
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-[#10131A] rounded-xl border border-[#252B36] text-xs">
                    <div className="flex items-center gap-3">
                      <Smartphone className="w-4 h-4 text-[#929AAA]" />
                      <div>
                        <p className="font-semibold text-[#F5F7FA]">FLOWSTATE Mobile iOS</p>
                        <p className="text-[10px] text-[#929AAA]">Last active 4 hours ago</p>
                      </div>
                    </div>
                    <button
                      onClick={() => success('Session Revoked', 'Mobile session key signed out.')}
                      className="text-xs text-red-400 hover:underline cursor-pointer"
                    >
                      Revoke
                    </button>
                  </div>
                </div>
              </div>

              {/* Account Sign Out Action */}
              <div className="pt-6 border-t border-[#252B36] space-y-3">
                <h4 className="text-xs font-semibold text-[#F5F7FA]">Sign Out & Session Termination</h4>
                <div className="p-4 bg-red-500/5 rounded-xl border border-red-500/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold text-[#F5F7FA]">Sign out of FLOWSTATE on this device</p>
                    <p className="text-[11px] text-[#929AAA] mt-0.5">
                      Terminates your active Supabase session and locks local workspace access.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => handleSignOut(true)}
                      className="text-xs border-[#252B36] text-[#929AAA] hover:text-[#F5F7FA]"
                    >
                      Sign Out & Forget Me
                    </Button>
                    <Button
                      type="button"
                      variant="primary"
                      size="sm"
                      onClick={() => handleSignOut(false)}
                      className="bg-red-600 hover:bg-red-500 text-white border-0 gap-1.5 cursor-pointer"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Sign Out</span>
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

'use client';

import React, { useState, useEffect, useCallback, useId } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import confetti from 'canvas-confetti';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { authService } from '@/services/authService';
import { SEED_USERS } from '@/lib/mock-data/seed';
import { Avatar } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  User,
  Building,
  ArrowRight,
  Sparkles,
  Check,
  CheckCircle2,
  ShieldCheck,
  Zap,
  RefreshCw,
  UserCheck,
  Phone,
} from 'lucide-react';

export interface SavedCustomerProfile {
  email: string;
  name?: string;
  avatar?: string;
  role?: string;
  savedPassword?: string;
  rememberPassword?: boolean;
  autoSignIn?: boolean;
  lastSignInAt?: string;
  isExistingUser: boolean;
}

interface AuthCardProps {
  initialMode?: 'login' | 'register';
}

function calculatePasswordStrength(pass: string): {
  score: number;
  label: string;
  color: string;
  hasLength: boolean;
  hasUpper: boolean;
  hasNumberOrSpecial: boolean;
} {
  const hasLength = pass.length >= 8;
  const hasUpper = /[A-Z]/.test(pass);
  const hasLower = /[a-z]/.test(pass);
  const hasNumberOrSpecial = /[\d!@#$%^&*(),.?":{}|<>]/.test(pass);

  let score = 0;
  if (hasLength) score++;
  if (hasUpper && hasLower) score++;
  if (hasNumberOrSpecial) score++;
  if (pass.length >= 12 && hasNumberOrSpecial && hasUpper) score++;

  if (score === 0) return { score: 0, label: 'Empty', color: '#6B7280', hasLength, hasUpper, hasNumberOrSpecial };
  if (score === 1) return { score: 1, label: 'Weak', color: '#EF4444', hasLength, hasUpper, hasNumberOrSpecial };
  if (score === 2) return { score: 2, label: 'Fair', color: '#F59E0B', hasLength, hasUpper, hasNumberOrSpecial };
  if (score === 3) return { score: 3, label: 'Strong', color: '#10B981', hasLength, hasUpper, hasNumberOrSpecial };
  return { score: 4, label: 'Enterprise Grade', color: '#8B7CFF', hasLength, hasUpper, hasNumberOrSpecial };
}

function triggerSuccessConfetti() {
  try {
    confetti({
      particleCount: 80,
      spread: 70,
      origin: { y: 0.6 },
      colors: ['#8B7CFF', '#3B82F6', '#10B981', '#EC4899', '#F59E0B'],
      disableForReducedMotion: true,
    });
  } catch {}
}

export function AuthCard({ initialMode = 'login' }: AuthCardProps) {
  const router = useRouter();
  const { switchUser, register, login } = useAuth();
  const { success, error, info } = useToast();

  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  // Customer Detection & Auto Sign-In State
  const [savedCustomer, setSavedCustomer] = useState<SavedCustomerProfile | null>(null);
  const [isExistingCustomer, setIsExistingCustomer] = useState<boolean | null>(null);
  const [isAutoSigningIn, setIsAutoSigningIn] = useState(false);
  const [autoCountdown, setAutoCountdown] = useState(3);
  const [savePassword, setSavePassword] = useState(true);
  const [autoSignInPref, setAutoSignInPref] = useState(true);
  const [autoSignInPaused, setAutoSignInPaused] = useState(false);

  // Login form state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Register form state
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regWorkspace, setRegWorkspace] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regTerms, setRegTerms] = useState(true);

  const passwordStrength = calculatePasswordStrength(regPassword);
  const workspaceSlug = regWorkspace
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '') || 'your-team';

  // 1. Detect whether existing customer or new user on mount
  useEffect(() => {
    if (typeof window === 'undefined') return;

    try {
      const rawUser = localStorage.getItem('flowstate_saved_user');
      const hasVisited = localStorage.getItem('flowstate_has_visited');
      const preventAuto = sessionStorage.getItem('flowstate_prevent_auto_login');

      if (rawUser) {
        const parsed: SavedCustomerProfile = JSON.parse(rawUser);
        setSavedCustomer(parsed);
        setIsExistingCustomer(true);
        setMode('login'); // Existing customer: ask to Sign In
        if (parsed.email) setLoginEmail(parsed.email);
        if (parsed.savedPassword) {
          setLoginPassword(parsed.savedPassword);
          setSavePassword(true);
        }
        if (parsed.autoSignIn !== undefined) {
          setAutoSignInPref(parsed.autoSignIn);
        }

        // Auto sign in if enabled & password saved (unless user explicitly signed out or cancelled)
        if (parsed.autoSignIn && parsed.savedPassword) {
          if (preventAuto === 'true') {
            setAutoSignInPaused(true);
          } else {
            setIsAutoSigningIn(true);
            setAutoCountdown(3);
          }
        }
      } else if (hasVisited === 'true') {
        // Visited before but no saved credentials
        setIsExistingCustomer(true);
        setMode('login');
      } else {
        // Completely new user! Ask them to sign up!
        setIsExistingCustomer(false);
        setMode('register');
      }
    } catch {
      setIsExistingCustomer(false);
      setMode('register');
    }
  }, []);

  // 2. Auto-Sign-In Countdown Timer
  const executeAutoLogin = useCallback(async () => {
    const targetEmail = savedCustomer?.email || loginEmail;
    const targetPass = savedCustomer?.savedPassword || loginPassword;

    if (!targetEmail || !targetPass) {
      setIsAutoSigningIn(false);
      return;
    }

    setIsLoading(true);
    try {
      await authService.login(targetEmail, targetPass);
      setIsSuccess(true);
      triggerSuccessConfetti();
      success('Welcome Back', `Auto-authenticated as ${savedCustomer?.name || targetEmail}`);
      setTimeout(() => {
        router.push('/dashboard');
      }, 600);
    } catch (err: any) {
      setIsAutoSigningIn(false);
      setIsLoading(false);
      setAutoSignInPaused(true);
      error('Auto Sign-In Failed', 'Please re-enter your password.');
    }
  }, [savedCustomer, loginEmail, loginPassword, router, success, error]);

  useEffect(() => {
    if (!isAutoSigningIn || autoCountdown <= 0) return;

    const timer = setInterval(() => {
      setAutoCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          executeAutoLogin();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isAutoSigningIn, autoCountdown, executeAutoLogin]);

  const cancelAutoSignIn = () => {
    setIsAutoSigningIn(false);
    setAutoSignInPaused(true);
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('flowstate_prevent_auto_login', 'true');
    }
  };

  const handleSwitchAccount = () => {
    setIsAutoSigningIn(false);
    setAutoSignInPaused(true);
    setSavedCustomer(null);
    setLoginEmail('');
    setLoginPassword('');
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('flowstate_prevent_auto_login', 'true');
    }
  };

  // Handle Login submission
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail.trim()) return;

    setIsLoading(true);
    try {
      await login(loginEmail.trim(), loginPassword);
      setIsSuccess(true);
      triggerSuccessConfetti();

      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('flowstate_prevent_auto_login');
        localStorage.setItem('flowstate_has_visited', 'true');

        const profileToSave: SavedCustomerProfile = {
          email: loginEmail.trim(),
          name: loginEmail.split('@')[0],
          savedPassword: savePassword ? loginPassword : '',
          rememberPassword: savePassword,
          autoSignIn: autoSignInPref && savePassword,
          lastSignInAt: new Date().toISOString(),
          isExistingUser: true,
        };
        localStorage.setItem('flowstate_saved_user', JSON.stringify(profileToSave));
      }

      success('Welcome Back', `Authenticated session active as ${loginEmail.trim()}`);
      setTimeout(() => {
        router.push('/dashboard');
      }, 700);
    } catch (err: any) {
      error('Authentication Error', err.message || 'Unable to sign in.');
      setIsLoading(false);
    }
  };

  // Handle Quick Persona Login
  const handleQuickLogin = async (userId: string) => {
    setIsLoading(true);
    try {
      await switchUser(userId);
      const persona = SEED_USERS.find((u) => u.id === userId);
      setIsSuccess(true);
      triggerSuccessConfetti();

      if (typeof window !== 'undefined' && persona) {
        sessionStorage.removeItem('flowstate_prevent_auto_login');
        localStorage.setItem('flowstate_has_visited', 'true');

        const profileToSave: SavedCustomerProfile = {
          email: persona.email,
          name: persona.name,
          avatar: persona.avatar,
          role: persona.role,
          savedPassword: 'FlowstatePass123!',
          rememberPassword: true,
          autoSignIn: true,
          lastSignInAt: new Date().toISOString(),
          isExistingUser: true,
        };
        localStorage.setItem('flowstate_saved_user', JSON.stringify(profileToSave));
      }

      success('Session Started', `Simulating active persona: ${persona?.name} (${persona?.title})`);
      setTimeout(() => {
        router.push('/dashboard');
      }, 700);
    } catch {
      setIsLoading(false);
    }
  };

  // Handle Register submission
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regName.trim() || !regEmail.trim() || !regPassword) return;

    setIsLoading(true);
    try {
      await register({
        name: regName.trim(),
        email: regEmail.trim(),
        password: regPassword,
        phone: regPhone.trim() || undefined,
        workspaceName: regWorkspace.trim() || undefined,
        workspaceSlug: workspaceSlug || undefined,
        plan: 'enterprise',
      });
      setIsSuccess(true);
      triggerSuccessConfetti();

      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('flowstate_prevent_auto_login');
        localStorage.setItem('flowstate_has_visited', 'true');

        const profileToSave: SavedCustomerProfile = {
          email: regEmail.trim(),
          name: regName.trim(),
          role: 'owner',
          savedPassword: regPassword,
          rememberPassword: true,
          autoSignIn: true,
          lastSignInAt: new Date().toISOString(),
          isExistingUser: true,
        };
        localStorage.setItem('flowstate_saved_user', JSON.stringify(profileToSave));
      }

      success('Workspace Created', `Welcome to FLOWSTATE Enterprise, ${regName.trim()}!`);
      setTimeout(() => {
        router.push('/dashboard');
      }, 700);
    } catch (err: any) {
      error('Registration Failed', err.message || 'Unable to create enterprise workspace.');
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-lg mx-auto relative z-10 animate-in fade-in duration-300">
      {/* Outer Card with Animated Glow */}
      <div className="relative bg-[#151922]/90 backdrop-blur-2xl border border-[#252B36] rounded-3xl p-6 sm:p-8 shadow-2xl shadow-black/80 transition-all duration-300 animate-border-glow">

        {/* 1. New User Welcome Banner */}
        {isExistingCustomer === false && mode === 'register' && (
          <div className="mb-6 p-4 rounded-2xl bg-gradient-to-r from-[var(--accent-subtle)] via-[#151922] to-emerald-500/10 border border-[var(--accent)]/30 flex items-center gap-3.5 animate-in fade-in duration-200">
            <div className="w-10 h-10 rounded-xl bg-[var(--accent-subtle)] border border-[var(--accent)]/40 flex items-center justify-center shrink-0">
              <span className="text-xl">👋</span>
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-bold text-[#F5F7FA]">Welcome to FLOWSTATE!</p>
              <p className="text-[11px] text-[#929AAA] leading-relaxed mt-0.5">
                New user detected — please create your workspace below to get started in seconds.
              </p>
            </div>
          </div>
        )}

        {/* 2. Recognized Existing Customer Welcome Banner (When not in countdown) */}
        {savedCustomer && mode === 'login' && !isAutoSigningIn && (
          <div className="mb-6 p-3.5 rounded-2xl bg-[#10131A] border border-[var(--accent)]/30 flex items-center justify-between gap-3 animate-in fade-in duration-200">
            <div className="flex items-center gap-2.5 min-w-0">
              <Avatar
                name={savedCustomer.name || savedCustomer.email}
                avatarUrl={savedCustomer.avatar}
                size="sm"
              />
              <div className="min-w-0">
                <p className="text-xs font-bold text-[#F5F7FA] truncate">
                  Welcome back, {savedCustomer.name || savedCustomer.email}!
                </p>
                <p className="text-[10px] text-emerald-400 flex items-center gap-1 font-medium">
                  <Check className="w-3 h-3" />
                  Saved customer • Password remembered
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={executeAutoLogin}
                disabled={isLoading}
                className="text-xs py-1 px-3 h-8 gap-1.5 font-semibold cursor-pointer"
              >
                <span>Sign In</span>
                <ArrowRight className="w-3 h-3" />
              </Button>
              <button
                type="button"
                onClick={handleSwitchAccount}
                title="Switch to another account"
                className="text-[10px] text-[#929AAA] hover:text-[#F5F7FA] transition-colors p-1 cursor-pointer"
              >
                Switch
              </button>
            </div>
          </div>
        )}

        {/* Animated Pill Mode Switcher (Sign In ⟷ Create Workspace) */}
        <div className="relative flex items-center p-1 bg-[#10131A] rounded-2xl border border-[#252B36] mb-6">
          <button
            type="button"
            onClick={() => {
              setMode('login');
              setIsSuccess(false);
              cancelAutoSignIn();
            }}
            className={`flex-1 py-2 rounded-xl text-xs font-semibold transition-all duration-200 cursor-pointer flex items-center justify-center gap-1.5 ${
              mode === 'login'
                ? 'bg-[#151922] text-[#F5F7FA] shadow-md border border-[#252B36]'
                : 'text-[#929AAA] hover:text-[#F5F7FA]'
            }`}
          >
            <span>Sign In</span>
            {isExistingCustomer && (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            )}
          </button>

          <button
            type="button"
            onClick={() => {
              setMode('register');
              setIsSuccess(false);
              cancelAutoSignIn();
            }}
            className={`flex-1 py-2 rounded-xl text-xs font-semibold transition-all duration-200 cursor-pointer flex items-center justify-center gap-1.5 ${
              mode === 'register'
                ? 'bg-[#151922] text-[#F5F7FA] shadow-md border border-[#252B36]'
                : 'text-[#929AAA] hover:text-[#F5F7FA]'
            }`}
          >
            <span>Create Workspace</span>
            {isExistingCustomer === false && (
              <span className="px-1.5 py-0.2 rounded-full text-[9px] bg-[var(--accent-subtle)] text-[var(--accent)] font-bold">
                New
              </span>
            )}
          </button>
        </div>

        {/* ===================== AUTO SIGN-IN SCREEN ===================== */}
        {isAutoSigningIn && savedCustomer && mode === 'login' ? (
          <div className="py-6 px-4 bg-[#10131A] border border-[var(--accent)]/50 rounded-2xl shadow-xl space-y-6 text-center animate-in fade-in zoom-in-95 duration-200">
            {/* Pulsing Avatar with Glow */}
            <div className="relative mx-auto w-20 h-20 flex items-center justify-center">
              <div className="absolute inset-0 rounded-full border-2 border-[var(--accent)] animate-ping opacity-25" />
              <div className="absolute -inset-1 rounded-full bg-gradient-to-tr from-[var(--accent)] to-emerald-400 opacity-30 blur-md animate-pulse" />
              <Avatar
                name={savedCustomer.name || savedCustomer.email}
                avatarUrl={savedCustomer.avatar}
                size="lg"
                className="relative z-10 w-16 h-16 ring-4 ring-[#151922]"
              />
            </div>

            <div>
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold mb-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Existing Customer Recognized
              </div>
              <h3 className="text-lg font-bold text-[#F5F7FA]">
                Welcome back, {savedCustomer.name || savedCustomer.email}!
              </h3>
              <p className="text-xs text-[#929AAA] mt-0.5">{savedCustomer.email}</p>
            </div>

            {/* Countdown Progress Meter */}
            <div className="space-y-2 max-w-xs mx-auto">
              <div className="flex items-center justify-between text-xs text-[#929AAA]">
                <span className="flex items-center gap-1 text-[#F5F7FA] font-medium">
                  <Zap className="w-3.5 h-3.5 text-amber-400 animate-bounce" />
                  Signing in automatically...
                </span>
                <span className="font-mono font-bold text-[var(--accent)]">{autoCountdown}s</span>
              </div>
              <div className="h-2 w-full bg-[#151922] rounded-full overflow-hidden border border-[#252B36]">
                <div
                  className="h-full bg-gradient-to-r from-[var(--accent)] to-emerald-400 transition-all duration-1000 ease-linear rounded-full"
                  style={{ width: `${Math.max(10, ((4 - autoCountdown) / 3) * 100)}%` }}
                />
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-2 pt-2 max-w-xs mx-auto">
              <Button
                type="button"
                variant="primary"
                size="lg"
                disabled={isLoading}
                onClick={executeAutoLogin}
                className="w-full justify-center gap-2 font-semibold shadow-lg shadow-[var(--accent-glow)] cursor-pointer"
              >
                <span>Sign In Immediately</span>
                <ArrowRight className="w-4 h-4" />
              </Button>

              <button
                type="button"
                onClick={cancelAutoSignIn}
                className="w-full py-2 text-xs text-[#929AAA] hover:text-[#F5F7FA] hover:bg-[#151922] rounded-xl transition-colors cursor-pointer"
              >
                Cancel Auto-Sign In / Switch Account
              </button>
            </div>
          </div>
        ) : mode === 'login' ? (
          <div className="space-y-6">
            {/* Header */}
            <div>
              <h2 className="text-xl font-bold tracking-tight text-[#F5F7FA] flex items-center gap-2">
                <span>Sign in to FLOWSTATE</span>
                <Sparkles className="w-4 h-4 text-[var(--accent)]" />
              </h2>
              <p className="text-xs text-[#929AAA] mt-1">
                Enter your credentials or launch an instant one-click demo persona.
              </p>
            </div>

            {/* Quick Demo Personas 2x2 Grid */}
            <div className="p-3 bg-[#10131A] rounded-2xl border border-[#252B36] space-y-2">
              <div className="flex items-center justify-between px-1">
                <span className="text-[10px] font-semibold text-[#929AAA] uppercase tracking-wider">
                  One-Click Demo Personas
                </span>
                <span className="text-[10px] text-emerald-400 font-mono font-medium flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Instant Access
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {SEED_USERS.map((persona) => (
                  <button
                    key={persona.id}
                    type="button"
                    onClick={() => handleQuickLogin(persona.id)}
                    disabled={isLoading}
                    className="flex items-center justify-between p-2 rounded-xl bg-[#151922] hover:bg-[#1B202C] border border-[#252B36] hover:border-[var(--accent)]/50 transition-all text-left cursor-pointer group"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <Avatar user={persona} size="xs" />
                      <div className="truncate">
                        <p className="text-xs font-semibold text-[#F5F7FA] group-hover:text-[var(--accent)] transition-colors truncate">
                          {persona.name}
                        </p>
                        <p className="text-[10px] text-[#929AAA] truncate">{persona.title}</p>
                      </div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-[#929AAA] group-hover:text-[var(--accent)] group-hover:translate-x-0.5 transition-all shrink-0 ml-1" />
                  </button>
                ))}
              </div>
            </div>

            {/* Glowing Divider */}
            <div className="relative flex items-center justify-center">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-[#252B36]" />
              </div>
              <span className="relative bg-[#151922] px-3 text-[11px] font-medium text-[#929AAA] uppercase tracking-wider">
                Or Continue With Email
              </span>
            </div>

            {/* Standard Login Form */}
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-1.5">
                <label className="block text-xs font-medium text-[#929AAA]">Email Address</label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#929AAA] pointer-events-none" />
                  <input
                    type="email"
                    required
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    placeholder="alex@flowstate.dev"
                    className="w-full h-10 pl-10 pr-3.5 rounded-xl bg-[#10131A] border border-[#252B36] text-xs text-[#F5F7FA] placeholder-[#929AAA]/60 focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-subtle)] transition-all"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-medium text-[#929AAA]">Password</label>
                  <Link
                    href="/forgot-password"
                    className="text-xs text-[var(--accent)] hover:underline"
                  >
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#929AAA] pointer-events-none" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full h-10 pl-10 pr-10 rounded-xl bg-[#10131A] border border-[#252B36] text-xs text-[#F5F7FA] placeholder-[#929AAA]/60 focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-subtle)] transition-all font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[#929AAA] hover:text-[#F5F7FA] transition-colors cursor-pointer"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="space-y-2 pt-1">
                <label className="flex items-center gap-2 cursor-pointer text-xs text-[#929AAA]">
                  <input
                    type="checkbox"
                    checked={savePassword}
                    onChange={(e) => setSavePassword(e.target.checked)}
                    className="w-3.5 h-3.5 rounded text-[var(--accent)] accent-[var(--accent)] cursor-pointer"
                  />
                  <span className="text-[#F5F7FA] font-medium">Save password securely on this browser</span>
                </label>
                {savePassword && (
                  <label className="flex items-center gap-2 cursor-pointer text-xs text-[#929AAA] pl-5 animate-in fade-in duration-150">
                    <input
                      type="checkbox"
                      checked={autoSignInPref}
                      onChange={(e) => setAutoSignInPref(e.target.checked)}
                      className="w-3.5 h-3.5 rounded text-emerald-400 accent-emerald-400 cursor-pointer"
                    />
                    <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
                      <Zap className="w-3 h-3" />
                      Sign in automatically on next visit
                    </span>
                  </label>
                )}
              </div>

              {/* Submit Button with Animated States */}
              <Button
                type="submit"
                variant="primary"
                size="lg"
                disabled={isLoading || isSuccess}
                className="w-full relative overflow-hidden group shadow-lg"
              >
                {isSuccess ? (
                  <span className="flex items-center gap-2 text-white font-semibold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-300 animate-bounce" />
                    <span>Authenticated! Redirecting...</span>
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    <span>Sign In to Workspace</span>
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </span>
                )}
              </Button>
            </form>

            {/* Social SSO Section */}
            <div className="pt-4 border-t border-[#252B36] space-y-3">
              <span className="text-[10px] font-semibold text-[#929AAA] uppercase tracking-wider block text-center">
                Enterprise SSO & Integrations
              </span>
              <div className="grid grid-cols-2 gap-2.5">
                <button
                  type="button"
                  onClick={() => handleQuickLogin(SEED_USERS[0].id)}
                  className="flex items-center justify-center gap-2 py-2 px-3 bg-[#10131A] hover:bg-[#1B202C] border border-[#252B36] rounded-xl text-xs font-medium text-[#F5F7FA] transition-all cursor-pointer group"
                >
                  <svg className="w-4 h-4 fill-current text-white" viewBox="0 0 24 24">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                  </svg>
                  <span>GitHub SSO</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickLogin(SEED_USERS[1].id)}
                  className="flex items-center justify-center gap-2 py-2 px-3 bg-[#10131A] hover:bg-[#1B202C] border border-[#252B36] rounded-xl text-xs font-medium text-[#F5F7FA] transition-all cursor-pointer group"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                    />
                  </svg>
                  <span>Google Workspace</span>
                </button>
              </div>
            </div>
          </div>
        ) : null}

        {/* ===================== SIGN UP MODE ===================== */}
        {mode === 'register' && (
          <form onSubmit={handleRegister} className="space-y-4">
            {/* Header */}
            <div>
              <h2 className="text-xl font-bold tracking-tight text-[#F5F7FA] flex items-center gap-2">
                <span>Create FLOWSTATE Workspace</span>
                <Sparkles className="w-4 h-4 text-[var(--accent)]" />
              </h2>
              <p className="text-xs text-[#929AAA] mt-1">
                Deploy an isolated tenant workspace with FastAPI + PostgreSQL.
              </p>
            </div>

            {/* Name Input */}
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-[#929AAA]">Your Full Name</label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#929AAA] pointer-events-none" />
                <input
                  type="text"
                  required
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  placeholder="e.g. Jordan Vance"
                  className="w-full h-10 pl-10 pr-3.5 rounded-xl bg-[#10131A] border border-[#252B36] text-xs text-[#F5F7FA] placeholder-[#929AAA]/60 focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-subtle)] transition-all"
                />
              </div>
            </div>

            {/* Work Email */}
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-[#929AAA]">Work Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#929AAA] pointer-events-none" />
                <input
                  type="email"
                  required
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  placeholder="jordan@company.com"
                  className="w-full h-10 pl-10 pr-3.5 rounded-xl bg-[#10131A] border border-[#252B36] text-xs text-[#F5F7FA] placeholder-[#929AAA]/60 focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-subtle)] transition-all"
                />
              </div>
            </div>

            {/* Contact Phone Number */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-medium text-[#929AAA]">Contact Phone Number</label>
                <span className="text-[10px] text-[#929AAA]/70">Optional</span>
              </div>
              <div className="relative">
                <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#929AAA] pointer-events-none" />
                <input
                  type="tel"
                  value={regPhone}
                  onChange={(e) => setRegPhone(e.target.value)}
                  placeholder="+1 (555) 019-2834"
                  className="w-full h-10 pl-10 pr-3.5 rounded-xl bg-[#10131A] border border-[#252B36] text-xs text-[#F5F7FA] placeholder-[#929AAA]/60 focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-subtle)] transition-all"
                />
              </div>
            </div>

            {/* Organization / Workspace Name */}
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-[#929AAA]">Workspace Name</label>
              <div className="relative">
                <Building className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#929AAA] pointer-events-none" />
                <input
                  type="text"
                  value={regWorkspace}
                  onChange={(e) => setRegWorkspace(e.target.value)}
                  placeholder="Acme Product Studio"
                  className="w-full h-10 pl-10 pr-3.5 rounded-xl bg-[#10131A] border border-[#252B36] text-xs text-[#F5F7FA] placeholder-[#929AAA]/60 focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-subtle)] transition-all"
                />
              </div>

              {/* Dynamic Workspace URL Preview */}
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#10131A] rounded-lg border border-[#252B36] text-[11px] text-[#929AAA]">
                <span>Workspace URL:</span>
                <span className="font-mono text-[#F5F7FA] font-medium">flowstate.dev/</span>
                <span className="font-mono text-[var(--accent)] font-semibold truncate">
                  {workspaceSlug}
                </span>
              </div>
            </div>

            {/* Password with Real-Time Strength Meter */}
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-[#929AAA]">Create Strong Password</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#929AAA] pointer-events-none" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  className="w-full h-10 pl-10 pr-10 rounded-xl bg-[#10131A] border border-[#252B36] text-xs text-[#F5F7FA] placeholder-[#929AAA]/60 focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-subtle)] transition-all font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[#929AAA] hover:text-[#F5F7FA] transition-colors cursor-pointer"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>

              {/* Dynamic 4-Segment Strength Gauge */}
              {regPassword.length > 0 && (
                <div className="space-y-2 pt-1 animate-in fade-in duration-200">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-[#929AAA]">Security Strength:</span>
                    <span
                      className="font-semibold text-xs transition-colors"
                      style={{ color: passwordStrength.color }}
                    >
                      {passwordStrength.label}
                    </span>
                  </div>

                  <div className="grid grid-cols-4 gap-1.5">
                    {[1, 2, 3, 4].map((level) => (
                      <div
                        key={level}
                        className="h-1.5 rounded-full transition-all duration-300"
                        style={{
                          backgroundColor:
                            passwordStrength.score >= level ? passwordStrength.color : '#252B36',
                        }}
                      />
                    ))}
                  </div>

                  {/* Requirements Pills */}
                  <div className="flex flex-wrap gap-2 text-[10px]">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border transition-colors ${
                        passwordStrength.hasLength
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                          : 'bg-[#10131A] text-[#929AAA] border-[#252B36]'
                      }`}
                    >
                      <Check className="w-3 h-3" /> 8+ Characters
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border transition-colors ${
                        passwordStrength.hasUpper
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                          : 'bg-[#10131A] text-[#929AAA] border-[#252B36]'
                      }`}
                    >
                      <Check className="w-3 h-3" /> Uppercase & Lowercase
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border transition-colors ${
                        passwordStrength.hasNumberOrSpecial
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                          : 'bg-[#10131A] text-[#929AAA] border-[#252B36]'
                      }`}
                    >
                      <Check className="w-3 h-3" /> Numbers & Symbols
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Terms checkbox */}
            <label className="flex items-start gap-2.5 cursor-pointer text-xs text-[#929AAA] pt-1">
              <input
                type="checkbox"
                required
                checked={regTerms}
                onChange={(e) => setRegTerms(e.target.checked)}
                className="mt-0.5 w-3.5 h-3.5 rounded text-[var(--accent)] accent-[var(--accent)] cursor-pointer"
              />
              <span>
                I agree to the{' '}
                <span className="text-[var(--accent)] hover:underline">Terms of Service</span> and{' '}
                <span className="text-[var(--accent)] hover:underline">Privacy Policy</span>.
              </span>
            </label>

            {/* Create Account CTA */}
            <Button
              type="submit"
              variant="primary"
              size="lg"
              disabled={isLoading || isSuccess}
              className="w-full relative overflow-hidden group shadow-lg"
            >
              {isSuccess ? (
                <span className="flex items-center gap-2 text-white font-semibold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-300 animate-bounce" />
                  <span>Workspace Initialized! Entering...</span>
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <span>Create Enterprise Workspace</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </span>
              )}
            </Button>

            {/* Footer link to switch */}
            <div className="pt-3 border-t border-[#252B36] text-center text-xs text-[#929AAA]">
              Already have an existing organization?{' '}
              <button
                type="button"
                onClick={() => setMode('login')}
                className="text-[var(--accent)] hover:underline font-semibold cursor-pointer"
              >
                Sign In
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Security Proof Badge */}
      <div className="mt-4 flex items-center justify-center gap-2 text-xs text-[#929AAA]">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
        <span>End-to-end encrypted with Supabase JWT & Row-Level Security</span>
      </div>
    </div>
  );
}

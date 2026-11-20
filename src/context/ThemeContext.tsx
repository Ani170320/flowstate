'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { organizationService } from '@/services/organizationService';
import { useAuth } from './AuthContext';
import { useToast } from './ToastContext';

export type ThemeMode = 'dark' | 'midnight';

export interface ThemeConfig {
  theme: ThemeMode;
  accentColor: string;
}

export const THEME_STORAGE_KEY = 'flowstate_theme';
export const ACCENT_STORAGE_KEY = 'flowstate_accent_color';

export const DEFAULT_THEME: ThemeMode = 'dark';
export const DEFAULT_ACCENT = '#8B7CFF';

export const ACCENT_OPTIONS = [
  { label: 'Purple / Indigo', hex: '#8B7CFF' },
  { label: 'Electric Blue', hex: '#3B82F6' },
  { label: 'Emerald Green', hex: '#10B981' },
  { label: 'Hot Pink', hex: '#EC4899' },
  { label: 'Amber Gold', hex: '#F59E0B' },
];

function hexToRgba(hex: string, alpha: number): string {
  const cleanHex = hex.replace('#', '');
  const r = parseInt(cleanHex.substring(0, 2), 16) || 0;
  const g = parseInt(cleanHex.substring(2, 4), 16) || 0;
  const b = parseInt(cleanHex.substring(4, 6), 16) || 0;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function adjustBrightness(hex: string, factor: number): string {
  const cleanHex = hex.replace('#', '');
  let r = parseInt(cleanHex.substring(0, 2), 16) || 0;
  let g = parseInt(cleanHex.substring(2, 4), 16) || 0;
  let b = parseInt(cleanHex.substring(4, 6), 16) || 0;

  r = Math.min(255, Math.max(0, Math.round(r * factor)));
  g = Math.min(255, Math.max(0, Math.round(g * factor)));
  b = Math.min(255, Math.max(0, Math.round(b * factor)));

  const toHex = (n: number) => n.toString(16).padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

export function applyThemeToDom(theme: ThemeMode, accentColor: string) {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;

  // Set data-theme attribute
  root.setAttribute('data-theme', theme);

  // Set theme background & surface variables
  if (theme === 'midnight') {
    root.style.setProperty('--bg-primary', '#000000');
    root.style.setProperty('--bg-sidebar', '#050608');
    root.style.setProperty('--bg-card', '#090C11');
    root.style.setProperty('--bg-card-hover', '#121620');
    root.style.setProperty('--border-color', '#1A1F2B');
    root.style.setProperty('--border-light', '#252B36');
  } else {
    root.style.setProperty('--bg-primary', '#0B0D12');
    root.style.setProperty('--bg-sidebar', '#10131A');
    root.style.setProperty('--bg-card', '#151922');
    root.style.setProperty('--bg-card-hover', '#1B202C');
    root.style.setProperty('--border-color', '#252B36');
    root.style.setProperty('--border-light', '#323A4A');
  }

  // Set accent variables
  const hoverColor = adjustBrightness(accentColor, 0.9);
  const subtleColor = hexToRgba(accentColor, 0.16);
  const glowColor = hexToRgba(accentColor, 0.35);

  root.style.setProperty('--accent', accentColor);
  root.style.setProperty('--color-brand-accent', accentColor);
  root.style.setProperty('--accent-hover', hoverColor);
  root.style.setProperty('--accent-subtle', subtleColor);
  root.style.setProperty('--accent-glow', glowColor);
}

interface ThemeContextType {
  theme: ThemeMode;
  accentColor: string;
  setTheme: (theme: ThemeMode) => void;
  setAccentColor: (color: string) => void;
  saveAppearance: () => Promise<void>;
  isSaving: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { activeOrg } = useAuth();
  const { success, error: toastError } = useToast();

  const [theme, setThemeState] = useState<ThemeMode>(DEFAULT_THEME);
  const [accentColor, setAccentColorState] = useState<string>(DEFAULT_ACCENT);
  const [isSaving, setIsSaving] = useState(false);

  // 1. Initial hydration from localStorage
  useEffect(() => {
    try {
      const storedTheme = localStorage.getItem(THEME_STORAGE_KEY) as ThemeMode | null;
      const storedAccent = localStorage.getItem(ACCENT_STORAGE_KEY);

      const activeTheme: ThemeMode =
        storedTheme === 'midnight' || storedTheme === 'dark' ? storedTheme : DEFAULT_THEME;
      const activeAccent = storedAccent || DEFAULT_ACCENT;

      setThemeState(activeTheme);
      setAccentColorState(activeAccent);
      applyThemeToDom(activeTheme, activeAccent);
    } catch {
      applyThemeToDom(DEFAULT_THEME, DEFAULT_ACCENT);
    }
  }, []);

  // 2. Load workspace theme from backend if organization is active
  useEffect(() => {
    if (!activeOrg?.id) return;

    let isCancelled = false;
    organizationService
      .getWorkspaceSettings(activeOrg.id)
      .then((settings) => {
        if (isCancelled || !settings) return;
        if (settings.theme === 'midnight' || settings.theme === 'dark') {
          setThemeState(settings.theme);
        }
        // If settings have accent color, apply it
        const backendSettings = settings as any;
        if (backendSettings.accent_color || backendSettings.accentColor) {
          const acc = backendSettings.accent_color || backendSettings.accentColor;
          setAccentColorState(acc);
          applyThemeToDom(settings.theme as ThemeMode, acc);
        } else {
          applyThemeToDom(settings.theme as ThemeMode, accentColor);
        }
      })
      .catch(() => {
        // Fallback gracefully to local storage
      });

    return () => {
      isCancelled = true;
    };
  }, [activeOrg?.id]);

  // Set theme with immediate DOM update
  const setTheme = useCallback(
    (newTheme: ThemeMode) => {
      setThemeState(newTheme);
      applyThemeToDom(newTheme, accentColor);
      try {
        localStorage.setItem(THEME_STORAGE_KEY, newTheme);
      } catch {}
    },
    [accentColor]
  );

  // Set accent color with immediate DOM update
  const setAccentColor = useCallback(
    (newAccent: string) => {
      setAccentColorState(newAccent);
      applyThemeToDom(theme, newAccent);
      try {
        localStorage.setItem(ACCENT_STORAGE_KEY, newAccent);
      } catch {}
    },
    [theme]
  );

  // Explicit Save action for Settings button
  const saveAppearance = useCallback(async () => {
    setIsSaving(true);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
      localStorage.setItem(ACCENT_STORAGE_KEY, accentColor);
      applyThemeToDom(theme, accentColor);

      if (activeOrg?.id) {
        await organizationService.updateWorkspaceSettings(activeOrg.id, {
          theme,
          accent_color: accentColor,
        });
      }

      success(
        'Appearance Saved',
        `Active theme set to ${theme === 'midnight' ? 'Deep Midnight' : 'Linear Dark'} with custom accent.`
      );
    } catch (err) {
      console.warn('Backend appearance sync warning:', err);
      // Local changes still took effect
      success('Appearance Applied', 'Styles updated and saved to this browser.');
    } finally {
      setIsSaving(false);
    }
  }, [theme, accentColor, activeOrg, success]);

  return (
    <ThemeContext.Provider
      value={{
        theme,
        accentColor,
        setTheme,
        setAccentColor,
        saveAppearance,
        isSaving,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

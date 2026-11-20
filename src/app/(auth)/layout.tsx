'use client';

import React from 'react';
import Link from 'next/link';
import { Sparkles, ShieldCheck, Activity } from 'lucide-react';
import { AuthParticles } from '@/components/auth/AuthParticles';
import { AuthShowcase } from '@/components/auth/AuthShowcase';

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[#F5F7FA] relative overflow-x-hidden flex flex-col justify-between selection:bg-[var(--accent-subtle)]">
      {/* Background Interactive Particles */}
      <AuthParticles />

      {/* Top Navigation Bar */}
      <header className="relative z-20 border-b border-[#252B36]/60 backdrop-blur-md bg-[#0B0D12]/60 px-6 sm:px-10 h-16 flex items-center justify-between">
        <Link href="/dashboard" className="flex items-center gap-2.5 group cursor-pointer">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[var(--accent)] to-[#6351E6] flex items-center justify-center text-white shadow-lg shadow-[var(--accent)]/25 group-hover:scale-105 transition-transform">
            <Sparkles className="w-4 h-4 fill-white/20" />
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-base tracking-tight text-[#F5F7FA] font-mono leading-none">
              FLOWSTATE
            </span>
            <span className="text-[10px] text-[#929AAA] font-mono mt-0.5">SaaS Platform</span>
          </div>
        </Link>

        <div className="flex items-center gap-4 text-xs text-[#929AAA]">
          <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#10131A] border border-[#252B36]">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-mono text-[11px] text-[#F5F7FA]">FastAPI + Supabase Online</span>
          </div>

          <Link
            href="/dashboard"
            className="hover:text-[#F5F7FA] transition-colors font-medium flex items-center gap-1"
          >
            <span>Live Workspace</span>
            <span className="text-[var(--accent)]">&rarr;</span>
          </Link>
        </div>
      </header>

      {/* Main Split Grid (Showcase + Auth Form) */}
      <main className="relative z-10 flex-1 max-w-7xl w-full mx-auto grid grid-cols-1 lg:grid-cols-2 items-center px-4 sm:px-8 py-8 lg:py-12 gap-8 lg:gap-12">
        {/* Left: Floating Interactive Kanban Showcase (desktop) */}
        <AuthShowcase />

        {/* Right: Flagship Auth Form */}
        <div className="w-full flex items-center justify-center">
          {children}
        </div>
      </main>

      {/* Footer System Status */}
      <footer className="relative z-20 border-t border-[#252B36]/60 py-4 px-6 sm:px-10 text-xs text-[#929AAA] flex flex-col sm:flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span>&copy; {new Date().getFullYear()} FLOWSTATE Inc.</span>
          <span>•</span>
          <span>High-Craft Engineering Operations</span>
        </div>

        <div className="flex items-center gap-4 text-[11px]">
          <span className="flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>PostgreSQL 17.12 RLS</span>
          </span>
          <span className="flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-[var(--accent)]" />
            <span>Sub-50ms Latency</span>
          </span>
        </div>
      </footer>
    </div>
  );
}

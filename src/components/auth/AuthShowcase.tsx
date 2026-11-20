'use client';

import React, { useState } from 'react';
import {
  Sparkles,
  CheckCircle2,
  Circle,
  Clock,
  Layers,
  ShieldCheck,
  Zap,
  TrendingUp,
  Cpu,
  ArrowUpRight,
} from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';
import { SEED_USERS } from '@/lib/mock-data/seed';

export function AuthShowcase() {
  const [subtasks, setSubtasks] = useState([
    { id: '1', title: 'Supabase PostgreSQL 17.12 Schema Finalized', done: true },
    { id: '2', title: 'FastAPI JWT Auth & RBAC Security Layer', done: true },
    { id: '3', title: 'Turbopack Next.js Frontend Integration', done: false },
    { id: '4', title: 'Autonomous Realtime State Sync', done: false },
  ]);

  const toggleSubtask = (id: string) => {
    setSubtasks((prev) =>
      prev.map((s) => (s.id === id ? { ...s, done: !s.done } : s))
    );
  };

  const completedCount = subtasks.filter((s) => s.done).length;
  const progressPercent = Math.round((completedCount / subtasks.length) * 100);

  return (
    <div className="hidden lg:flex flex-col justify-between p-12 relative z-10 select-none">
      {/* Ambient background glow */}
      <div className="absolute top-1/3 left-1/4 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-[var(--accent)]/15 blur-[140px] pointer-events-none rounded-full" />
      <div className="absolute bottom-1/4 right-1/4 w-[350px] h-[350px] bg-blue-500/10 blur-[130px] pointer-events-none rounded-full" />

      {/* Top Banner & Value Proposition */}
      <div className="space-y-4 max-w-lg">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--accent-subtle)] border border-[var(--accent)]/30 text-xs font-medium text-[var(--accent)] backdrop-blur-md shadow-sm">
          <Sparkles className="w-3.5 h-3.5 animate-spin-slow" />
          <span>Next-Generation Project Operations</span>
        </div>

        <h1 className="text-3xl xl:text-4xl font-extrabold tracking-tight text-[#F5F7FA] leading-tight">
          Where high-velocity engineering meets pure architectural craft.
        </h1>

        <p className="text-sm text-[#929AAA] leading-relaxed">
          Unify task coordination, sprint cadences, team bandwidth, and deep multi-tenant security
          in one cohesive, high-contrast dark experience.
        </p>
      </div>

      {/* Centerpiece: Interactive Floating Glassmorphic Kanban Card */}
      <div className="my-8 relative max-w-md w-full">
        {/* Main Floating Card */}
        <div className="relative bg-[#151922]/85 backdrop-blur-xl border border-[#252B36] rounded-2xl p-6 shadow-2xl shadow-black/60 animate-float-slow transition-all duration-300 hover:border-[var(--accent)]/50 group">
          {/* Subtle gradient border highlight */}
          <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-[var(--accent)]/10 via-transparent to-blue-500/10 opacity-50 pointer-events-none" />

          {/* Ticket Header */}
          <div className="flex items-center justify-between mb-3 relative z-10">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#10131A] text-[#929AAA] border border-[#252B36]">
                FL-2048
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Active Sprint
              </span>
            </div>

            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-500/15 text-red-400 border border-red-500/25 flex items-center gap-1">
              <Zap className="w-3 h-3" />
              Urgent
            </span>
          </div>

          {/* Title */}
          <h3 className="text-sm font-bold text-[#F5F7FA] mb-2 relative z-10">
            Platform Modernization & Realtime Pipeline
          </h3>

          <p className="text-xs text-[#929AAA] mb-4 relative z-10">
            Click tasks below to interact with live sprint velocity metrics:
          </p>

          {/* Interactive Checklist */}
          <div className="space-y-2 mb-4 relative z-10">
            {subtasks.map((task) => (
              <div
                key={task.id}
                onClick={() => toggleSubtask(task.id)}
                className={`flex items-center justify-between p-2 rounded-lg text-xs cursor-pointer transition-all border ${
                  task.done
                    ? 'bg-[#10131A]/70 text-[#F5F7FA] border-emerald-500/30'
                    : 'bg-[#10131A]/40 text-[#929AAA] hover:text-[#F5F7FA] border-[#252B36]'
                }`}
              >
                <div className="flex items-center gap-2.5 truncate">
                  {task.done ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : (
                    <Circle className="w-4 h-4 text-[#929AAA]/60 shrink-0" />
                  )}
                  <span className={`truncate ${task.done ? 'line-through text-[#929AAA]' : ''}`}>
                    {task.title}
                  </span>
                </div>
                <span className="text-[10px] font-mono text-[#929AAA] shrink-0">
                  {task.done ? 'Done' : 'Todo'}
                </span>
              </div>
            ))}
          </div>

          {/* Dynamic Progress Bar */}
          <div className="space-y-1.5 relative z-10 pt-2 border-t border-[#252B36]">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[#929AAA] font-medium text-[11px]">Sprint Velocity</span>
              <span className="font-mono font-bold text-[var(--accent)] text-[11px]">
                {progressPercent}% Complete
              </span>
            </div>
            <div className="w-full h-1.5 bg-[#10131A] rounded-full overflow-hidden border border-[#252B36]">
              <div
                className="h-full bg-gradient-to-r from-[var(--accent)] to-[#7968EE] transition-all duration-500 rounded-full"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Card Footer: Assignees & Meta */}
          <div className="flex items-center justify-between pt-3 mt-3 border-t border-[#252B36] relative z-10">
            <div className="flex -space-x-1.5">
              {SEED_USERS.slice(0, 3).map((u) => (
                <div key={u.id} className="ring-2 ring-[#151922] rounded-full">
                  <Avatar user={u} size="xs" />
                </div>
              ))}
            </div>

            <div className="flex items-center gap-1.5 text-[11px] text-[#929AAA]">
              <Clock className="w-3.5 h-3.5 text-[var(--accent)]" />
              <span>Dec 15, 2026</span>
            </div>
          </div>
        </div>

        {/* Secondary Floating Mini Metric Card */}
        <div className="absolute -bottom-6 -right-6 bg-[#10131A]/90 backdrop-blur-xl border border-[#252B36] rounded-xl p-3.5 shadow-xl animate-float-reverse hidden xl:block w-48">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-semibold text-[#929AAA] uppercase tracking-wider">
              JWT Latency
            </span>
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl font-bold font-mono text-[#F5F7FA]">38ms</span>
            <span className="text-[10px] text-emerald-400 font-semibold flex items-center">
              <TrendingUp className="w-3 h-3" /> 99.98%
            </span>
          </div>
          <p className="text-[10px] text-[#929AAA] mt-0.5">PostgreSQL Connection Pool</p>
        </div>
      </div>

      {/* Bottom Proof Points & Enterprise Badges */}
      <div className="pt-6 border-t border-[#252B36]/80 grid grid-cols-3 gap-4 max-w-lg">
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-[#F5F7FA]">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>FastAPI RBAC</span>
          </div>
          <p className="text-[11px] text-[#929AAA]">Strict tenant isolation</p>
        </div>

        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-[#F5F7FA]">
            <Cpu className="w-3.5 h-3.5 text-[var(--accent)]" />
            <span>Postgres 17</span>
          </div>
          <p className="text-[11px] text-[#929AAA]">16 core table schema</p>
        </div>

        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-[#F5F7FA]">
            <Layers className="w-3.5 h-3.5 text-blue-400" />
            <span>Turbopack</span>
          </div>
          <p className="text-[11px] text-[#929AAA]">Zero-lag interface</p>
        </div>
      </div>
    </div>
  );
}

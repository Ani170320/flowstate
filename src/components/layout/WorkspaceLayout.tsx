'use client';

import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import { TopNav } from './TopNav';
import { GlobalSearchModal } from './GlobalSearchModal';
import { CreateTaskModal } from '@/components/tasks/CreateTaskModal';
import { CreateProjectModal } from '@/components/projects/CreateProjectModal';
import { TaskDetailModal } from '@/components/tasks/TaskDetailModal';
import { AICopilotModal } from '@/components/ai/AICopilotModal';
import { X } from 'lucide-react';

export function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <div className="flex h-screen bg-[var(--bg-primary)] text-[#F5F7FA] overflow-hidden">
      {/* Desktop Persistent Sidebar */}
      <div className="hidden md:flex shrink-0">
        <Sidebar />
      </div>

      {/* Mobile Drawer Sidebar */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            className="fixed inset-0 bg-[#0B0D12]/80 backdrop-blur-sm"
            onClick={() => setIsMobileMenuOpen(false)}
          />
          <div className="relative flex flex-col w-72 max-w-[85vw] bg-[#10131A] z-10 animate-in slide-in-from-left duration-200 shadow-2xl">
            <button
              onClick={() => setIsMobileMenuOpen(false)}
              className="absolute top-4 right-4 p-1.5 text-[#929AAA] hover:text-[#F5F7FA] rounded-lg cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
            <Sidebar />
          </div>
        </div>
      )}

      {/* Right Column: TopNav + Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopNav onMobileMenuToggle={() => setIsMobileMenuOpen(true)} />

        <main className="flex-1 overflow-y-auto px-4 sm:px-8 py-6">
          <div className="max-w-7xl mx-auto">{children}</div>
        </main>
      </div>

      {/* Persistent Global Modals */}
      <GlobalSearchModal />
      <CreateTaskModal />
      <CreateProjectModal />
      <TaskDetailModal />
      <AICopilotModal />
    </div>
  );
}

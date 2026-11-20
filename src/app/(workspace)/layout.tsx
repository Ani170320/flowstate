'use client';

import React, { Suspense } from 'react';
import { WorkspaceLayout } from '@/components/layout/WorkspaceLayout';

export default function WorkspaceRouteLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="h-screen bg-[#0B0D12] flex items-center justify-center text-xs text-[#929AAA]">Loading workspace...</div>}>
      <WorkspaceLayout>{children}</WorkspaceLayout>
    </Suspense>
  );
}

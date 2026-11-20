'use client';

import { use } from 'react';
import { redirect } from 'next/navigation';

export default function ProjectBoardRedirect({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  redirect(`/projects/${resolvedParams.id}?tab=board`);
}

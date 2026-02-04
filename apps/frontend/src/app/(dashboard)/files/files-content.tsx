'use client';

import React, { useState, useMemo, useEffect, useCallback, Suspense } from 'react';
import { useRouter } from 'next/navigation';
import { useThreads } from '@/hooks/threads/use-threads';
import { FileBrowserView } from '@/components/thread/kortix-computer/FileBrowserView';
import { FileViewerView } from '@/components/thread/kortix-computer/FileViewerView';
import { SandboxStatusView } from '@/components/thread/kortix-computer/components/SandboxStatusView';
import { useKortixComputerStore } from '@/stores/kortix-computer-store';
import { useSandboxStatusWithAutoStart, isSandboxUsable } from '@/hooks/files/use-sandbox-details';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { HardDrive, MessageSquare, Folder, FileText } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

// Skeleton for the file browser - shows immediately while data loads
function FilesPageSkeleton() {
  return (
    <div className="h-[100dvh] bg-background flex flex-col">
      {/* Header skeleton */}
      <div className="px-4 py-3 border-b flex items-center justify-between flex-shrink-0">
        <Skeleton className="h-7 w-16" />
        <div className="flex items-center gap-2">
          <Skeleton className="h-9 w-[200px]" />
          <Skeleton className="h-9 w-9" />
        </div>
      </div>
      {/* Content skeleton - file browser layout */}
      <div className="flex-1 p-4 space-y-4">
        {/* Breadcrumb skeleton */}
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-5" />
          <Skeleton className="h-5 w-24" />
        </div>
        {/* File list skeleton */}
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="flex items-center gap-3 p-3 rounded-md border">
              <Skeleton className="h-5 w-5" />
              <Skeleton className="h-4 w-32" />
              <div className="flex-1" />
              <Skeleton className="h-4 w-16" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Lazy-loaded sandbox status component - only fetches after threads are ready
function LazySandboxContent({ 
  projectId, 
  sandboxId, 
  project, 
  threadId 
}: { 
  projectId: string;
  sandboxId: string;
  project: any;
  threadId?: string;
}) {
  const router = useRouter();
  const { filesSubView, selectedFilePath } = useKortixComputerStore();
  
  // Sandbox status is fetched lazily - after initial render
  const { data: sandboxStatus, isLoading: isStatusLoading } = useSandboxStatusWithAutoStart(projectId);
  const isSandboxLive = sandboxStatus?.status ? isSandboxUsable(sandboxStatus.status) : false;

  const handleNavigateToThread = useCallback(() => {
    if (threadId && projectId) {
      router.push(`/projects/${projectId}/thread/${threadId}`);
    } else {
      router.push('/dashboard');
    }
  }, [router, projectId, threadId]);

  // Show skeleton while sandbox status is loading
  if (isStatusLoading) {
    return (
      <div className="flex-1 p-4 space-y-4">
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-5" />
          <Skeleton className="h-5 w-32" />
        </div>
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="flex items-center gap-3 p-3 rounded-md border">
              <Skeleton className="h-5 w-5" />
              <Skeleton className="h-4 w-40" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Show status view if sandbox is not LIVE
  if (!isSandboxLive) {
    return <SandboxStatusView projectId={projectId} />;
  }

  // Show file viewer if viewing a specific file
  if (filesSubView === 'viewer' && selectedFilePath) {
    return (
      <FileViewerView
        sandboxId={sandboxId}
        filePath={selectedFilePath}
        project={project}
        projectId={projectId}
      />
    );
  }

  // Show file browser
  return (
    <FileBrowserView
      sandboxId={sandboxId}
      project={project}
      projectId={projectId}
      variant="inline-library"
    />
  );
}

export default function FilesContent() {
  const router = useRouter();
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  
  // Get store state
  const { navigateToPath } = useKortixComputerStore();

  // Fetch threads - uses SSR-prefetched data from HydrationBoundary
  const { data: threadsResponse, isLoading: isThreadsLoading } = useThreads({
    page: 1,
    limit: 50,
  });

  // Build list of unique projects with sandboxes
  const projectsWithSandboxes = useMemo(() => {
    if (!threadsResponse?.threads) return [];
    
    const projectMap = new Map<string, { 
      projectId: string; 
      projectName: string; 
      sandboxId: string; 
      threadId: string; 
      updatedAt: string;
      project: typeof threadsResponse.threads[0]['project'];
    }>();
    
    for (const thread of threadsResponse.threads) {
      if (thread.project_id && thread.project?.sandbox?.id) {
        const existing = projectMap.get(thread.project_id);
        if (!existing || new Date(thread.updated_at) > new Date(existing.updatedAt)) {
          projectMap.set(thread.project_id, {
            projectId: thread.project_id,
            projectName: thread.project?.name || thread.metadata?.title || `Project ${thread.project_id.slice(0, 8)}`,
            sandboxId: thread.project.sandbox.id,
            threadId: thread.thread_id,
            updatedAt: thread.updated_at,
            project: thread.project,
          });
        }
      }
    }
    
    return Array.from(projectMap.values()).sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    );
  }, [threadsResponse]);

  // Auto-select first project
  const projectId = selectedProjectId || projectsWithSandboxes[0]?.projectId || '';
  const selectedProject = projectsWithSandboxes.find(p => p.projectId === projectId);
  const sandboxId = selectedProject?.sandboxId || '';
  const threadId = selectedProject?.threadId;
  const project = selectedProject?.project;

  // Reset path when project changes
  useEffect(() => {
    navigateToPath('/workspace');
  }, [projectId, navigateToPath]);

  const handleNavigateToThread = useCallback(() => {
    if (threadId && projectId) {
      router.push(`/projects/${projectId}/thread/${threadId}`);
    } else {
      router.push('/dashboard');
    }
  }, [router, projectId, threadId]);

  // Show skeleton while threads are loading
  if (isThreadsLoading) {
    return <FilesPageSkeleton />;
  }

  // No projects - show empty state
  if (projectsWithSandboxes.length === 0) {
    return (
      <div className="flex items-center justify-center h-[100dvh] bg-background">
        <div className="text-center space-y-4">
          <HardDrive className="h-12 w-12 mx-auto text-muted-foreground" />
          <h2 className="text-lg font-semibold">No Computers Yet</h2>
          <p className="text-sm text-muted-foreground max-w-xs">
            Start a conversation to create your first computer.
          </p>
          <Button onClick={() => router.push('/dashboard')}>Start a Chat</Button>
        </div>
      </div>
    );
  }

  // Project selector
  const projectSelector = (
    <div className="flex items-center gap-2">
      <Select value={projectId} onValueChange={setSelectedProjectId}>
        <SelectTrigger className="w-[200px] h-9">
          <HardDrive className="h-4 w-4 mr-2 text-muted-foreground" />
          <SelectValue placeholder="Select computer" />
        </SelectTrigger>
        <SelectContent>
          {projectsWithSandboxes.map((p) => (
            <SelectItem key={p.projectId} value={p.projectId}>
              {p.projectName}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {threadId && (
        <Button variant="ghost" size="icon" onClick={handleNavigateToThread}>
          <MessageSquare className="h-4 w-4" />
        </Button>
      )}
    </div>
  );

  return (
    <div className="h-[100dvh] bg-background flex flex-col">
      {/* Header with project selector */}
      <div className="px-4 py-3 border-b flex items-center justify-between flex-shrink-0">
        <h1 className="text-lg font-semibold">Files</h1>
        {projectSelector}
      </div>
      {/* Content - lazy loads sandbox status */}
      <div className="flex-1 overflow-hidden">
        <LazySandboxContent 
          projectId={projectId}
          sandboxId={sandboxId}
          project={project}
          threadId={threadId}
        />
      </div>
    </div>
  );
}

'use client';

import dynamic from 'next/dynamic';
import { SharePageWrapper } from './SharePageWrapper';

// Dynamic import to avoid SSR issues with browser-only dependencies
const ThreadComponent = dynamic(
  () => import('@/components/thread/ThreadComponent').then(mod => ({ default: mod.ThreadComponent })),
  { ssr: false }
);

export function ThreadLoaderClient({ threadId }: { threadId: string }) {
  return (
    <SharePageWrapper>
      <ThreadComponent
        projectId=""
        threadId={threadId}
        isShared={true}
      />
    </SharePageWrapper>
  );
}

import { Suspense } from 'react';
import { ThreadLoaderClient } from './_components/ThreadLoaderClient';
import {
  ThreadParams,
} from '@/components/thread/types';

export default async function ShareThreadPage({
  params,
}: {
  params: Promise<ThreadParams>;
}) {
  const { threadId } = await params;

  return (
    <Suspense fallback={<div className="flex items-center justify-center h-screen">Loading...</div>}>
      <ThreadLoaderClient threadId={threadId} />
    </Suspense>
  );
}

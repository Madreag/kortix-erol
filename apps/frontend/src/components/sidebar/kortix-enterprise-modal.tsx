'use client';

import { ReactNode } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

interface KortixProcessModalProps {
  children: ReactNode;
}

export function KortixProcessModal({ children }: KortixProcessModalProps) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Enterprise Demo</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <p className="text-sm text-muted-foreground">
            Contact us for custom AI Agents implementation tailored to your business needs.
          </p>
          <p className="text-sm text-muted-foreground">
            Email: <a href="mailto:enterprise@kortix.com" className="text-primary hover:underline">enterprise@kortix.com</a>
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}

'use client';

import { useState, useEffect, useRef, useOptimistic, useTransition } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface RenameProjectDialogProps {
  isOpen: boolean;
  projectId: string | null;
  currentName: string;
  onClose: () => void;
  onSave: (projectId: string, newName: string) => Promise<void>;
}

export function RenameProjectDialog({
  isOpen,
  projectId,
  currentName,
  onClose,
  onSave,
}: RenameProjectDialogProps) {
  const [name, setName] = useState(currentName);
  const [isPending, startTransition] = useTransition();
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Optimistic state for instant UI feedback
  const [optimisticName, setOptimisticName] = useOptimistic(
    currentName,
    (_current, newName: string) => newName
  );

  useEffect(() => {
    if (isOpen) {
      setName(currentName);
      setTimeout(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      }, 50);
    }
  }, [isOpen, currentName]);

  const handleSave = async () => {
    if (!projectId || name.trim() === '') return;
    
    const trimmedName = name.trim();
    
    // Close dialog immediately for instant feedback
    onClose();
    
    // Start optimistic update
    startTransition(async () => {
      setOptimisticName(trimmedName);
      try {
        await onSave(projectId, trimmedName);
      } catch (error) {
        // Error handling is done in parent - will revert via query invalidation
      }
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Rename Project</DialogTitle>
        </DialogHeader>
        <div className="py-4">
          <Input
            ref={inputRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter project name..."
            maxLength={50}
            disabled={isPending}
          />
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={isPending || name.trim() === ''}
          >
            {isPending ? 'Saving...' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


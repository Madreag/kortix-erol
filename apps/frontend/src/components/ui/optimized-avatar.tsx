'use client';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';

interface OptimizedAvatarProps {
  src?: string | null;
  alt: string;
  fallback: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  /** Set true if avatar is in header/above fold */
  priority?: boolean;
  className?: string;
}

const sizeClasses = {
  sm: 'h-6 w-6',
  md: 'h-8 w-8',
  lg: 'h-10 w-10',
  xl: 'h-12 w-12',
};

/**
 * OptimizedAvatar - Avatar with priority loading hints
 *
 * Header avatars should use priority={true} for faster LCP
 */
export function OptimizedAvatar({
  src,
  alt,
  fallback,
  size = 'md',
  priority = false,
  className,
}: OptimizedAvatarProps) {
  return (
    <Avatar className={cn(sizeClasses[size], className)}>
      {src && (
        <AvatarImage
          src={src}
          alt={alt}
          // Apply fetchpriority via native img attribute
          {...(priority && { fetchPriority: 'high' as const })}
        />
      )}
      <AvatarFallback delayMs={priority ? 0 : 600}>
        {fallback}
      </AvatarFallback>
    </Avatar>
  );
}

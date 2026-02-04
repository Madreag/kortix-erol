'use client';

import { OptimizedImage } from './optimized-image';
import { cn } from '@/lib/utils';

interface LCPHeroProps {
  src: string;
  alt: string;
  className?: string;
  overlayContent?: React.ReactNode;
}

/**
 * LCPHero - Optimized hero image component for above-the-fold content
 *
 * Features:
 * - fetchpriority="high" for fastest loading
 * - Blur placeholder for perceived performance
 * - Responsive sizes for optimal bandwidth
 */
export function LCPHero({ src, alt, className, overlayContent }: LCPHeroProps) {
  return (
    <div className={cn('relative w-full overflow-hidden', className)}>
      <OptimizedImage
        src={src}
        alt={alt}
        fill
        lcpCandidate
        sizes="100vw"
        className="object-cover"
      />
      {overlayContent && (
        <div className="absolute inset-0 flex items-center justify-center">
          {overlayContent}
        </div>
      )}
    </div>
  );
}

'use client';

import Image, { type ImageProps } from 'next/image';

interface OptimizedImageProps extends Omit<ImageProps, 'loading'> {
  alt: string; // Explicitly require alt for accessibility
  /** Mark as LCP candidate for priority loading */
  lcpCandidate?: boolean;
  /** Override loading behavior */
  loading?: 'eager' | 'lazy';
  /** React 19: ref as prop */
  ref?: React.Ref<HTMLImageElement>;
}

const BLUR_DATA_URL =
  'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAAIAAoDASIAAhEBAxEB/8QAFgABAQEAAAAAAAAAAAAAAAAAAAUH/8QAIhAAAgEDAwUBAAAAAAAAAAAAAQIDAAQRBQYhEhMiMUFR/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAaEQACAgMAAAAAAAAAAAAAAAAAAQIRAxIh/9oADAMBAAIRAxEAPwC3s3X7qHTXttVdpbmMnplY5Cj+fQHsKKp7Z1O5hsxHJI7BWIJY5xRWmLa2Rjj/2Q==';

/**
 * OptimizedImage - Automatically applies fetchpriority hints
 *
 * Use lcpCandidate={true} for:
 * - Hero images above the fold
 * - Main product images
 * - Avatar in the header (if large)
 */
export function OptimizedImage({
  alt,
  lcpCandidate = false,
  priority,
  loading,
  ref,
  ...props
}: OptimizedImageProps) {
  // LCP candidates get highest priority
  const shouldPrioritize = lcpCandidate || priority;

  return (
    <Image
      ref={ref}
      alt={alt}
      priority={shouldPrioritize}
      loading={shouldPrioritize ? 'eager' : (loading ?? 'lazy')}
      // Next.js 15+ automatically adds fetchpriority="high" when priority=true
      placeholder="blur"
      blurDataURL={BLUR_DATA_URL}
      sizes={props.sizes || '(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw'}
      {...props}
    />
  );
}

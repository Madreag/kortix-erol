import Image, { type ImageProps } from 'next/image';

interface OptimizedImageProps extends Omit<ImageProps, 'placeholder'> {
  priority?: boolean;
  isLCP?: boolean;
}

const BLUR_DATA_URL = 
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';

export function OptimizedImage({
  priority = false,
  isLCP = false,
  ...props
}: OptimizedImageProps) {
  return (
    <Image
      {...props}
      priority={priority || isLCP}
      loading={priority || isLCP ? 'eager' : 'lazy'}
      placeholder="blur"
      blurDataURL={BLUR_DATA_URL}
      sizes={props.sizes || '(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw'}
    />
  );
}

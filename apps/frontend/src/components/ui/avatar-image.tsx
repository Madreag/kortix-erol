import { OptimizedImage } from './optimized-image';

interface AvatarImageProps {
  src: string | null | undefined;
  alt: string;
  size?: 'sm' | 'md' | 'lg';
  fallback?: string;
}

const SIZES = {
  sm: 32,
  md: 40,
  lg: 64,
};

export function AvatarImage({ 
  src, 
  alt, 
  size = 'md',
  fallback,
}: AvatarImageProps) {
  const dimension = SIZES[size];
  
  if (!src) {
    return (
      <div 
        className="rounded-full bg-gray-700 flex items-center justify-center text-gray-400"
        style={{ width: dimension, height: dimension }}
      >
        {fallback || alt.charAt(0).toUpperCase()}
      </div>
    );
  }
  
  return (
    <OptimizedImage
      src={src}
      alt={alt}
      width={dimension}
      height={dimension}
      className="rounded-full object-cover"
      sizes={`${dimension}px`}
    />
  );
}

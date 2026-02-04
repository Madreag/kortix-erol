import type { NextConfig } from 'next';
import createBundleStatsPlugin from 'next-plugin-bundle-stats';
import withSerwistInit from '@serwist/next';

// Initialize Serwist for PWA - disabled in development
const withSerwist = withSerwistInit({
  swSrc: 'src/sw.ts',
  swDest: 'public/sw.js',
  disable: process.env.NODE_ENV === 'development',
  reloadOnOnline: true,
  cacheOnNavigation: true,
});

// Dynamically determine backend URL based on Vercel environment
const getBackendUrl = (): string => {
  // If explicitly set via Vercel dashboard/env, use that (highest priority)
  const explicitUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (explicitUrl && explicitUrl.trim() !== '') {
    return explicitUrl;
  }
  
  // Vercel environment detection
  const vercelEnv = process.env.VERCEL_ENV; // 'production', 'preview', or 'development'
  const gitRef = process.env.VERCEL_GIT_COMMIT_REF || ''; // Branch name
  
  // Production environment
  if (vercelEnv === 'production') {
    return 'https://api.kortix.com/v1';
  }
  
  // Preview deployments (non-main branches)
  if (vercelEnv === 'preview' && gitRef && gitRef !== 'main') {
    // Sanitize branch name for URL
    const sanitizedBranch = gitRef
      .toLowerCase()
      .replace(/[^a-z0-9-]/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');
    return `https://${sanitizedBranch}.staging-api.kortix.com/v1`;
  }

  // Main branch / staging (default)
  return 'https://staging-api.kortix.com/v1';
};

const nextConfig = (): NextConfig => ({
  output: (process.env.NEXT_OUTPUT as 'standalone') || undefined,
  
  // Transpile shared package
  transpilePackages: ['@agentpress/shared'],
  
  // Set environment variables
  env: {
    NEXT_PUBLIC_BACKEND_URL: getBackendUrl(),
  },
  
  // Webpack configuration for Konva + bundle splitting
  webpack: (config, { isServer }) => {
    // Required to make Konva & react-konva work
    config.externals = [...config.externals, { canvas: 'canvas' }];
    
    // Bundle splitting for better caching (client-side only)
    if (!isServer) {
      config.optimization.splitChunks = {
        chunks: 'all',
        cacheGroups: {
          // React core - changes rarely
          react: {
            test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
            name: 'react',
            priority: 30,
            reuseExistingChunk: true,
          },
          // TanStack - data layer
          tanstack: {
            test: /[\\/]node_modules[\\/]@tanstack[\\/]/,
            name: 'tanstack',
            priority: 25,
            reuseExistingChunk: true,
          },
          // UI libraries
          ui: {
            test: /[\\/]node_modules[\\/](@radix-ui|lucide-react)[\\/]/,
            name: 'ui-libs',
            priority: 20,
            reuseExistingChunk: true,
          },
          // Common chunks
          commons: {
            minChunks: 2,
            priority: 10,
            reuseExistingChunk: true,
          },
        },
      };
    }
    return config;
  },
  
  // Turbopack configuration
  turbopack: {
    // Handle Node.js modules that shouldn't be bundled for browser builds
    // Canvas is a Node.js native module that needs to be externalized (required for Konva & react-konva)
    resolveAlias: {
      canvas: {
        browser: './src/lib/empty-module.ts', // Exclude canvas from browser builds
      },
    },
  },
  
  // React Compiler for automatic memoization (top-level in Next.js 16)
  // Disabled in dev mode for faster TTFB - only needed for production optimization
  reactCompiler: process.env.NODE_ENV === 'production',
  
  // Performance optimizations
  experimental: {
    // TODO: Enable cacheComponents (includes PPR) after refactoring app to use 
    // Suspense boundaries for all dynamic data access in layouts/providers.
    // Currently disabled because DashboardLayoutContent, AuthProvider, etc.
    // use hooks (useParams, useAuth) that access uncached data during static generation.
    // See: https://nextjs.org/docs/app/building-your-application/caching
    // cacheComponents: true,
    
    // Client router cache configuration
    staleTimes: {
      dynamic: 30,   // seconds for dynamic pages
      static: 180,   // seconds for static pages
    },
    
    // Optimize package imports for faster builds and smaller bundles
    optimizePackageImports: [
      'lucide-react',
      'framer-motion',
      '@radix-ui/react-icons',
      'recharts',
      'date-fns',
      '@tanstack/react-query',
      'react-icons',
    ],
  },
  
  // Enable compression
  compress: true,
  
  // Optimize images
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    qualities: [75, 100],
    // Cache optimized images for 1 year
    minimumCacheTTL: 31536000,
    // Remote patterns for external images
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.supabase.co',
      },
      {
        protocol: 'https',
        hostname: 'avatars.githubusercontent.com',
      },
    ],
    dangerouslyAllowSVG: true,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },
  
  async rewrites() {
    return [
      {
        source: '/ingest/static/:path*',
        destination: 'https://eu-assets.i.posthog.com/static/:path*',
      },
      {
        source: '/ingest/:path*',
        destination: 'https://eu.i.posthog.com/:path*',
      },
      {
        source: '/ingest/flags',
        destination: 'https://eu.i.posthog.com/flags',
      },
    ];
  },
  
  // HTTP headers for caching, performance, and security
  async headers() {
    return [
      // Early Hints - Link preload headers for critical pages
      {
        source: '/',
        headers: [
          {
            key: 'Link',
            value: '</fonts/roobert/RoobertUprightsVF.woff2>; rel=preload; as=font; type=font/woff2; crossorigin',
          },
        ],
      },
      {
        source: '/dashboard',
        headers: [
          {
            key: 'Link',
            value: '</fonts/roobert/RoobertUprightsVF.woff2>; rel=preload; as=font; type=font/woff2; crossorigin',
          },
        ],
      },
      // Static assets - aggressive caching (fonts)
      {
        source: '/fonts/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/:path*.woff2',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      // Static assets - aggressive caching (JS/CSS/images)
      {
        source: '/:path*.(js|css|png|jpg|svg|ico|webp|avif)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      // API routes - short cache with revalidation
      {
        source: '/api/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'private, max-age=0, must-revalidate',
          },
        ],
      },
      // Client hints for adaptive optimization
      {
        source: '/:path*',
        headers: [
          {
            key: 'Accept-CH',
            value: 'Sec-CH-UA, Sec-CH-UA-Mobile, Sec-CH-UA-Platform, Downlink, RTT, ECT',
          },
          {
            key: 'Critical-CH',
            value: 'Sec-CH-UA-Mobile',
          },
        ],
      },
      // Security headers
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
      // Service Worker headers
      {
        source: '/sw.js',
        headers: [
          {
            key: 'Content-Type',
            value: 'application/javascript; charset=utf-8',
          },
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate',
          },
          {
            key: 'Service-Worker-Allowed',
            value: '/',
          },
        ],
      },
    ];
  },
  
  skipTrailingSlashRedirect: true,
});

// Bundle analysis - only enable in CI or when ANALYZE=true
const withBundleStats = createBundleStatsPlugin({
  outDir: '.next/analyze',
});

// Compose plugins: Serwist for PWA, optional bundle stats for analysis
const baseConfig = nextConfig();
const withPWA = withSerwist(baseConfig);

const config = process.env.ANALYZE === 'true'
  ? withBundleStats(withPWA)
  : withPWA;

export default config;

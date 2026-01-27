import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwind from '@astrojs/tailwind';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';

export default defineConfig({
  site: 'https://kortix.ai',
  
  integrations: [
    // React for interactive islands
    react(),
    
    // Tailwind CSS
    tailwind({
      applyBaseStyles: false, // Use custom base styles
    }),
    
    // Sitemap generation
    sitemap(),
    
    // MDX for docs/blog
    mdx(),
  ],
  
  // Output static (SSG) - default in Astro 5
  output: 'static',
  
  // Prefetch links
  prefetch: {
    prefetchAll: true,
    defaultStrategy: 'viewport',
  },
  
  // Build optimization
  build: {
    inlineStylesheets: 'auto',
  },
  
  // Vite config
  vite: {
    build: {
      cssCodeSplit: true,
      rollupOptions: {
        output: {
          assetFileNames: 'assets/[hash][extname]',
        },
      },
    },
  },
});

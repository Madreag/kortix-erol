import { getOrGenerateCSRFToken } from '@/lib/auth/csrf';

/**
 * CSRFMeta Component
 * 
 * Server component that generates a CSRF token and renders it as a meta tag.
 * Client-side code can read this token for API requests.
 */
export async function CSRFMeta() {
  const token = await getOrGenerateCSRFToken();
  
  return (
    <meta name="csrf-token" content={token} />
  );
}

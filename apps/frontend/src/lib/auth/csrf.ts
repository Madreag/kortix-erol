import { cookies } from 'next/headers';

const CSRF_COOKIE_NAME = 'csrf_token';

function generateRandomToken(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Get or generate a CSRF token.
 * Note: In Next.js 15+, cookies can only be SET in Server Actions or Route Handlers.
 * This function only reads the existing token or generates one for display.
 * The actual cookie should be set via middleware or a route handler.
 */
export async function getOrGenerateCSRFToken(): Promise<string> {
  const cookieStore = await cookies();
  const existingToken = cookieStore.get(CSRF_COOKIE_NAME)?.value;
  
  if (existingToken) {
    return existingToken;
  }
  
  // Generate a new token for display (will be set by middleware on next request)
  return generateRandomToken();
}

export async function getCSRFToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(CSRF_COOKIE_NAME)?.value || null;
}

export async function validateCSRFToken(headerToken: string | null): Promise<boolean> {
  if (!headerToken) return false;
  
  const cookieToken = await getCSRFToken();
  if (!cookieToken) return false;
  
  if (headerToken.length !== cookieToken.length) return false;
  
  let result = 0;
  for (let i = 0; i < headerToken.length; i++) {
    result |= headerToken.charCodeAt(i) ^ cookieToken.charCodeAt(i);
  }
  
  return result === 0;
}

import { createRemoteJWKSet, jwtVerify, type JWTPayload } from 'jose';

let jwks: ReturnType<typeof createRemoteJWKSet> | null = null;

function getJWKS() {
  if (!jwks) {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    if (!supabaseUrl) {
      throw new Error('NEXT_PUBLIC_SUPABASE_URL not configured');
    }
    jwks = createRemoteJWKSet(
      new URL(`${supabaseUrl}/auth/v1/.well-known/jwks.json`)
    );
  }
  return jwks;
}

export interface VerifiedToken extends JWTPayload {
  sub: string;
  email?: string;
  role?: string;
  aud?: string;
}

export async function verifySupabaseJWT(token: string): Promise<VerifiedToken> {
  const { payload } = await jwtVerify(token, getJWKS(), {
    issuer: process.env.NEXT_PUBLIC_SUPABASE_URL,
    audience: 'authenticated',
  });
  
  if (!payload.sub) {
    throw new Error('JWT missing subject claim');
  }
  
  return payload as VerifiedToken;
}

export function unsafeDecodeJWT(token: string): Partial<VerifiedToken> {
  try {
    const [, payload] = token.split('.');
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decoded);
  } catch {
    return {};
  }
}

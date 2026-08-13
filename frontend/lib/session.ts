import { NextRequest } from 'next/server';
import { jwtVerify } from 'jose';

// Shared session utilities -- extracted from app/api/auth/route.ts so that
// this file is NOT a Next.js route file (which forbids non-handler exports).

export const JWT_SECRET = new TextEncoder().encode(process.env.JWT_SECRET!);
export const COOKIE_NAME = 'bb_session';

export async function verifySessionCookie(
  req: NextRequest
): Promise<{ child_id: string; name: string } | null> {
  const cookie = req.cookies.get(COOKIE_NAME);
  if (!cookie?.value) return null;
  try {
    const { payload } = await jwtVerify(cookie.value, JWT_SECRET);
    return { child_id: payload.child_id as string, name: payload.name as string };
  } catch {
    return null;
  }
}

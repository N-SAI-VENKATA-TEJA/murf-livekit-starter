import { NextRequest, NextResponse } from 'next/server';
import { verifySessionCookie } from '../route';

// ── GET /api/auth/me ──────────────────────────────────────────────────────────
// Used by the frontend on load to check if there is already a valid session.
export async function GET(req: NextRequest) {
  const session = await verifySessionCookie(req);
  if (!session) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }
  return NextResponse.json({ authenticated: true, child_id: session.child_id, name: session.name });
}

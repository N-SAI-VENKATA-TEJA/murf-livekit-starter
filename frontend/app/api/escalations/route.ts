import { NextRequest, NextResponse } from 'next/server';
import { MongoClient, ObjectId } from 'mongodb';
import { verifySessionCookie } from '@/app/api/auth/route';

// ── Environment ───────────────────────────────────────────────────────────────
const MONGODB_URI = process.env.MONGODB_URI!;

// ── MongoDB client (reused across requests) ───────────────────────────────────
let _mongoClient: MongoClient | null = null;
async function getMongoClient(): Promise<MongoClient> {
  if (!_mongoClient) {
    _mongoClient = new MongoClient(MONGODB_URI);
    await _mongoClient.connect();
  }
  return _mongoClient;
}

async function getEscalationsCollection() {
  const client = await getMongoClient();
  return client.db('bolobuddy').collection('escalations');
}

// ── GET /api/escalations ──────────────────────────────────────────────────────
//
// Security: child_id is taken EXCLUSIVELY from the signed JWT session cookie.
// The browser cannot supply or override this value.
// Only escalations belonging to the authenticated child are returned.
//
export async function GET(req: NextRequest) {
  if (!MONGODB_URI) {
    return NextResponse.json({ error: 'MONGODB_URI not set' }, { status: 500 });
  }

  // ── 1. Verify session — extract trusted child_id from JWT ─────────────────
  const session = await verifySessionCookie(req);
  if (!session) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
  }

  // child_id comes from the signed JWT — not from any query parameter.
  const { child_id: trustedChildId } = session;

  // ── 2. Query escalations for this child only ───────────────────────────────
  try {
    const col = await getEscalationsCollection();

    // Return open escalations first, then others, sorted by created_at desc.
    const docs = await col
      .find(
        { child_id: trustedChildId },
        {
          projection: {
            _id: 0, // never expose raw MongoDB _id
            reference_id: 1,
            reason: 1,
            what_happened: 1,
            what_checked: 1,
            language: 1,
            follow_up_method: 1,
            status: 1,
            created_at: 1,
          },
        }
      )
      .sort({ status: 1, created_at: -1 }) // "open" < "closed" alphabetically → open first
      .toArray();

    return NextResponse.json({ escalations: docs });
  } catch (err) {
    console.error('[escalations] MongoDB query failed:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

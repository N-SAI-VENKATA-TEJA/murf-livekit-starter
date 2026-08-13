import { NextRequest, NextResponse } from 'next/server';
import { MongoClient } from 'mongodb';
import { verifySessionCookie } from '@/lib/session';

// -- Environment -------------------------------------------------------------
const MONGODB_URI = process.env.MONGODB_URI!;

// -- MongoDB client (reused across requests in the same process) -------------
let _mongoClient: MongoClient | null = null;
async function getMongoClient(): Promise<MongoClient> {
  if (!_mongoClient) {
    _mongoClient = new MongoClient(MONGODB_URI);
    await _mongoClient.connect();
  }
  return _mongoClient;
}

async function getCallsCollection() {
  const client = await getMongoClient();
  return client.db('bolobuddy').collection('calls');
}

// -- GET /api/analytics -------------------------------------------------------
// Returns aggregate call metrics for the currently authenticated child.
// child_id is derived from the existing bb_session JWT cookie -- never from
// the request body or query string.
export async function GET(req: NextRequest) {
  if (!MONGODB_URI) {
    return NextResponse.json({ error: 'MONGODB_URI not set' }, { status: 500 });
  }

  // Verify the existing child session cookie
  const session = await verifySessionCookie(req);
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { child_id } = session;

  try {
    const col = await getCallsCollection();

    // Calculate aggregate metrics server-side
    const total_calls = await col.countDocuments({ child_id });
    const successful_calls = await col.countDocuments({ child_id, outcome: 'success' });
    const failed_calls = await col.countDocuments({ child_id, outcome: 'failed' });

    return NextResponse.json(
      { total_calls, successful_calls, failed_calls },
      { headers: { 'Cache-Control': 'no-store' } }
    );
  } catch (err) {
    console.error('[analytics] Error querying calls collection:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

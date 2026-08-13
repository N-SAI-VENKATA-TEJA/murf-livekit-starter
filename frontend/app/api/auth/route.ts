import { NextRequest, NextResponse } from 'next/server';
import bcrypt from 'bcryptjs';
import { SignJWT } from 'jose';
import { MongoClient } from 'mongodb';
import { JWT_SECRET, COOKIE_NAME } from '@/lib/session';

// -- Environment -------------------------------------------------------------
const MONGODB_URI = process.env.MONGODB_URI!;
const COOKIE_MAX_AGE = 60 * 60 * 24 * 30; // 30 days

// -- MongoDB client (reused across requests in the same process) -------------
let _mongoClient: MongoClient | null = null;
async function getMongoClient(): Promise<MongoClient> {
  if (!_mongoClient) {
    _mongoClient = new MongoClient(MONGODB_URI);
    await _mongoClient.connect();
  }
  return _mongoClient;
}

async function getCollection() {
  const client = await getMongoClient();
  return client.db('bolobuddy').collection('children');
}

// -- JWT helpers -------------------------------------------------------------
async function signSessionToken(child_id: string, name: string): Promise<string> {
  return new SignJWT({ child_id, name })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('30d')
    .sign(JWT_SECRET);
}

function setSessionCookie(response: NextResponse, token: string) {
  response.cookies.set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: COOKIE_MAX_AGE,
    path: '/',
  });
}

// -- Request body type -------------------------------------------------------
type AuthBody = {
  action: 'signup' | 'login';
  name: string;
  password: string;
};

// -- POST /api/auth ----------------------------------------------------------
export async function POST(req: NextRequest) {
  if (!MONGODB_URI) return NextResponse.json({ error: 'MONGODB_URI not set' }, { status: 500 });
  if (!process.env.JWT_SECRET)
    return NextResponse.json({ error: 'JWT_SECRET not set' }, { status: 500 });

  let body: AuthBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
  }

  const { action, name, password } = body;

  if (!name || !password) {
    return NextResponse.json({ error: 'Name and password are required' }, { status: 400 });
  }
  if (!['signup', 'login'].includes(action)) {
    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
  }

  const col = await getCollection();

  // -- SIGNUP ----------------------------------------------------------------
  if (action === 'signup') {
    const existing = await col.findOne({ name: name.trim() });
    if (existing) {
      return NextResponse.json(
        {
          error:
            'A child account with this name already exists. Please choose a different name or log in.',
        },
        { status: 409 }
      );
    }

    const password_hash = await bcrypt.hash(password, 12);

    const result = await col.insertOne({
      name: name.trim(),
      password_hash,
      language_preference: '',
      words_learned: [],
      word_mistakes: [],
      last_interaction: null,
    });

    const child_id = result.insertedId.toHexString();
    const token = await signSessionToken(child_id, name.trim());

    const res = NextResponse.json({ child_id, name: name.trim() }, { status: 201 });
    setSessionCookie(res, token);
    return res;
  }

  // -- LOGIN -----------------------------------------------------------------
  const doc = await col.findOne({ name: name.trim() });
  if (!doc) {
    return NextResponse.json({ error: 'No account found with that name.' }, { status: 401 });
  }

  const passwordValid = await bcrypt.compare(password, doc.password_hash);
  if (!passwordValid) {
    return NextResponse.json({ error: 'Incorrect password. Please try again.' }, { status: 401 });
  }

  const child_id = doc._id.toHexString();
  const token = await signSessionToken(child_id, doc.name);

  const res = NextResponse.json({ child_id, name: doc.name }, { status: 200 });
  setSessionCookie(res, token);
  return res;
}

// -- DELETE /api/auth (logout) -----------------------------------------------
export async function DELETE() {
  const res = NextResponse.json({ success: true });
  res.cookies.set(COOKIE_NAME, '', { maxAge: 0, path: '/' });
  return res;
}

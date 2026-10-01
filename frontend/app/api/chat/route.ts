import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenerativeAI } from '@google/generative-ai';

// Initialize the Google Generative AI with the API key from environment variables
const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY || '');

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const message = body.message || '';

    if (!message) {
      return NextResponse.json({ reply: 'Please provide a message.' }, { status: 400 });
    }

    if (!process.env.GOOGLE_API_KEY) {
      return NextResponse.json({ reply: 'Server configuration error: Missing API Key.' }, { status: 500 });
    }

    // Get the generative model
    const model = genAI.getGenerativeModel({ model: 'gemini-3.5-flash' });

    const systemPrompt = `You are Chinnu, the warm and playful voice companion of BoloBuddy.
BoloBuddy helps children aged 2-6 learn language naturally through conversation.
Keep your response short, playful, and very encouraging, just like a preschool teacher.
Keep sentences short and toddler-friendly.`;

    // Generate content using the Gemini model
    const result = await model.generateContent([
      { text: systemPrompt },
      { text: `Child says: ${message}` }
    ]);
    
    const responseText = result.response.text();

    return NextResponse.json({ reply: responseText });
  } catch (error) {
    console.error('API Chat Error:', error);
    return NextResponse.json({ reply: 'Sorry, I encountered an error.' }, { status: 500 });
  }
}

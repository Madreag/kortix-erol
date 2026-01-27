import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const { metrics } = await request.json();
    
    if (process.env.NODE_ENV === 'development') {
      console.log('[RUM]', JSON.stringify(metrics, null, 2));
    }
    
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json({ error: 'Invalid payload' }, { status: 400 });
  }
}

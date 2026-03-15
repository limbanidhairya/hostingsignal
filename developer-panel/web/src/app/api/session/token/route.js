import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function GET() {
    const token = cookies().get('hsdev_session')?.value || '';
    if (!token) {
        return NextResponse.json({ detail: 'No session token' }, { status: 401 });
    }
    return NextResponse.json({ access_token: token }, { status: 200 });
}

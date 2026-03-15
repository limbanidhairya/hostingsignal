import { NextResponse } from 'next/server';

export async function POST() {
    const res = NextResponse.json({ success: true }, { status: 200 });
    res.cookies.set('hsdev_session', '', { path: '/', maxAge: 0 });
    return res;
}

import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const buildApiBaseCandidates = () => {
    const raw = [
        process.env.HSDEV_INTERNAL_API_BASE,
        process.env.NEXT_PUBLIC_HSDEV_API_BASE,
        'http://host.docker.internal:2087',
        'http://127.0.0.1:2087',
        'http://localhost:2087',
    ];
    const cleaned = raw
        .filter(Boolean)
        .map((value) => String(value).trim())
        .map((value) => value.replace(/\/+$/, ''))
        .filter((value) => value.startsWith('http://') || value.startsWith('https://'));
    return [...new Set(cleaned)];
};

export async function GET() {
    const token = cookies().get('hsdev_session')?.value || '';
    if (!token) {
        return NextResponse.json({ detail: 'No session' }, { status: 401 });
    }

    try {
        const apiBases = buildApiBaseCandidates();
        let finalError = null;

        for (const apiBase of apiBases) {
            try {
                const upstream = await fetch(`${apiBase}/api/auth/me`, {
                    method: 'GET',
                    headers: { Authorization: `Bearer ${token}` },
                    cache: 'no-store',
                });

                const payload = await upstream.json().catch(() => ({}));
                if (!upstream.ok) {
                    const status = upstream.status || 401;
                    const detail = payload?.detail || 'Invalid session';
                    const retryable = [404, 405, 502, 503, 504].includes(status);
                    if (retryable) {
                        finalError = detail;
                        continue;
                    }
                    const res = NextResponse.json({ detail }, { status: 401 });
                    res.cookies.set('hsdev_session', '', { path: '/', maxAge: 0 });
                    return res;
                }

                return NextResponse.json(payload, { status: 200 });
            } catch {
                finalError = 'Session check failed';
            }
        }

        const res = NextResponse.json({ detail: finalError || 'Invalid session' }, { status: 401 });
        res.cookies.set('hsdev_session', '', { path: '/', maxAge: 0 });
        return res;
    } catch {
        return NextResponse.json({ detail: 'Session check failed' }, { status: 500 });
    }
}

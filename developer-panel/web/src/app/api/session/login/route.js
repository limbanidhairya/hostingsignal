import { NextResponse } from 'next/server';

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

export async function POST(request) {
    try {
        const body = await request.json();
        const apiBases = buildApiBaseCandidates();
        let finalError = null;

        for (const apiBase of apiBases) {
            try {
                const upstream = await fetch(`${apiBase}/api/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                    cache: 'no-store',
                });

                const payload = await upstream.json().catch(() => ({}));
                if (!upstream.ok || !payload?.access_token) {
                    const status = upstream.status || 401;
                    const detail = payload?.detail || 'Login failed';
                    const retryable = [404, 405, 502, 503, 504].includes(status);
                    if (retryable) {
                        finalError = { status, detail };
                        continue;
                    }
                    return NextResponse.json({ detail }, { status });
                }

                const maxAge = Number(payload.expires_in || 86400);
                const res = NextResponse.json({ success: true, access_token: payload.access_token }, { status: 200 });
                res.cookies.set('hsdev_session', payload.access_token, {
                    httpOnly: true,
                    secure: false,
                    sameSite: 'lax',
                    path: '/',
                    maxAge,
                });
                return res;
            } catch {
                finalError = { status: 500, detail: 'Session login failed' };
            }
        }

        return NextResponse.json(
            { detail: finalError?.detail || 'Session login failed' },
            { status: finalError?.status || 500 }
        );
    } catch {
        return NextResponse.json({ detail: 'Session login failed' }, { status: 500 });
    }
}

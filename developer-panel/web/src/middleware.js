import { NextResponse } from 'next/server';

const SECTION_ROUTES = new Set([
    '/shell',
    '/domains',
    '/email',
    '/docker',
    '/backups',
    '/security',
    '/files',
    '/licenses',
    '/plugins',
    '/containers',
    '/whmcs-audit',
    '/clusters',
    '/updates',
    '/analytics',
    '/monitoring',
]);

const isPublicPath = (pathname) => (
    pathname === '/login' ||
    pathname.startsWith('/login/') ||
    pathname === '/auth/login' ||
    pathname.startsWith('/auth/login/')
);
const isPublicAsset = (pathname) => {
    if (pathname.startsWith('/branding/')) return true;
    return /\.(png|jpg|jpeg|gif|svg|webp|ico|css|js|map|txt|woff|woff2)$/i.test(pathname);
};

export function middleware(request) {
    const { pathname } = request.nextUrl;

    // Skip internal/static and API proxy paths.
    if (
        pathname.startsWith('/_next') ||
        pathname.startsWith('/devapi') ||
        pathname.startsWith('/hspanel') ||
        pathname.startsWith('/api') ||
        pathname === '/favicon.ico'
    ) {
        return NextResponse.next();
    }

    if (isPublicPath(pathname)) {
        return NextResponse.next();
    }

    if (isPublicAsset(pathname)) {
        return NextResponse.next();
    }

    const token = request.cookies.get('hsdev_session')?.value;
    if (!token) {
        const loginUrl = request.nextUrl.clone();
        loginUrl.pathname = '/login';
        loginUrl.search = '';
        return NextResponse.redirect(loginUrl);
    }

    if (SECTION_ROUTES.has(pathname)) {
        const url = request.nextUrl.clone();
        url.pathname = '/';
        url.searchParams.set('section', pathname.slice(1));
        return NextResponse.rewrite(url);
    }

    return NextResponse.next();
}

export const config = {
    matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};

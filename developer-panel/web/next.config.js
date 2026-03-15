/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    output: 'standalone',
    async rewrites() {
        const devApiTarget = process.env.HSDEV_INTERNAL_API_BASE || 'http://devpanel-api:2087';
        const panelApiTarget = process.env.HSPANEL_INTERNAL_API_BASE || 'http://backend:2083';
        return [
            {
                source: '/devapi/:path*',
                destination: `${devApiTarget}/:path*`,
            },
            {
                source: '/hspanel/:path*',
                destination: `${panelApiTarget}/:path*`,
            },
        ];
    },
};

module.exports = nextConfig;

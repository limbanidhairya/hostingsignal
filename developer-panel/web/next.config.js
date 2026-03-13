/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    output: 'standalone',
    async rewrites() {
        const devApiTarget = process.env.HSDEV_INTERNAL_API_BASE || 'http://127.0.0.1:2087';
        return [
            {
                source: '/devapi/:path*',
                destination: `${devApiTarget}/:path*`,
            },
        ];
    },
};

module.exports = nextConfig;

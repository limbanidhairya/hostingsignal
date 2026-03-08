import './globals.css';

export const metadata = {
    title: 'HostingSignal Developer Panel',
    description: 'Central management for licenses, plugins, clusters, updates & analytics',
};

export default function RootLayout({ children }) {
    return (
        <html lang="en">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
            </head>
            <body>{children}</body>
        </html>
    );
}

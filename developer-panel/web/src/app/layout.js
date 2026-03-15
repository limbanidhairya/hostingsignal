import './globals.css';

export const metadata = {
    title: 'HS-Panel Developer Panel',
    description: 'Central management for licenses, plugins, clusters, updates & analytics',
};

export default function RootLayout({ children }) {
    return (
        <html lang="en" className="dark">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet" />
                <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet" />
                <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries" async></script>
                <script dangerouslySetInnerHTML={{
                    __html: `
                    window.tailwind = window.tailwind || {};
                    window.tailwind.config = {
                        darkMode: "class",
                        theme: {
                            extend: {
                                colors: {
                                    "primary": "#0ea5e9",
                                    "accent": "#38bdf8",
                                    "background-light": "#f5f7f8",
                                    "background-dark": "#061529",
                                    "card-dark": "#0d243d",
                                    "border-dark": "#1f3a56",
                                },
                                fontFamily: {
                                    "display": ["Inter", "sans-serif"]
                                },
                                borderRadius: {"DEFAULT": "0.25rem", "lg": "0.5rem", "xl": "0.75rem", "full": "9999px"},
                            },
                        },
                    }
                `}} />
            </head>
            <body className="bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 min-h-screen m-0 p-0">
                {children}
            </body>
        </html>
    );
}

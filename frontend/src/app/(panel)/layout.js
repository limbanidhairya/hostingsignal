'use client';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import { usePathname } from 'next/navigation';

const pageTitles = {
    '/dashboard': 'Dashboard',
    '/websites': 'Websites',
    '/domains': 'Domains',
    '/dns': 'DNS Management',
    '/databases': 'Databases',
    '/email': 'Email',
    '/docker': 'Docker',
    '/files': 'File Manager',
    '/monitoring': 'Monitoring',
    '/backups': 'Backups',
    '/security': 'Security',
    '/settings': 'Settings',
    '/license': 'License',
    '/admin': 'Admin',
    '/plugins': 'Plugins',
};

export default function PanelLayout({ children }) {
    const pathname = usePathname();
    const title = pageTitles[pathname] || 'HostingSignal';

    return (
        <div className="hs-layout">
            <Sidebar />
            <main className="hs-main">
                <Header title={title} />
                <div className="hs-content hs-animate-in">
                    {children}
                </div>
            </main>
        </div>
    );
}

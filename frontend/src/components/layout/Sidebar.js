'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navSections = [
    {
        title: 'Overview',
        items: [
            { label: 'Dashboard', href: '/dashboard', icon: '📊' },
            { label: 'Websites', href: '/websites', icon: '🌐' },
            { label: 'Domains', href: '/domains', icon: '🔗' },
        ],
    },
    {
        title: 'Services',
        items: [
            { label: 'DNS', href: '/dns', icon: '🗂️' },
            { label: 'Databases', href: '/databases', icon: '🗄️' },
            { label: 'Email', href: '/email', icon: '📧' },
            { label: 'PHP Manager', href: '/php-manager', icon: '🐘' },
            { label: 'Docker', href: '/docker', icon: '🐳' },
            { label: 'Files', href: '/files', icon: '📁' },
        ],
    },
    {
        title: 'System',
        items: [
            { label: 'Monitoring', href: '/monitoring', icon: '📈' },
            { label: 'Backups', href: '/backups', icon: '💾' },
            { label: 'Security', href: '/security', icon: '🛡️' },
            { label: 'Plugins', href: '/plugins', icon: '🔌' },
            { label: 'Settings', href: '/settings', icon: '⚙️' },
            { label: 'License', href: '/license', icon: '🔑' },
        ],
    },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="hs-sidebar">
            <div className="hs-sidebar-logo">
                <div className="logo-icon">HS</div>
                <div className="logo-text">HostingSignal</div>
            </div>

            <nav className="hs-sidebar-nav">
                {navSections.map((section) => (
                    <div key={section.title} className="hs-sidebar-section">
                        <div className="hs-sidebar-section-title">{section.title}</div>
                        {section.items.map((item) => (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`hs-nav-item ${pathname === item.href ? 'active' : ''}`}
                            >
                                <span className="nav-icon">{item.icon}</span>
                                <span>{item.label}</span>
                            </Link>
                        ))}
                    </div>
                ))}
            </nav>

            <div style={{ padding: '16px 20px', borderTop: '1px solid var(--hs-border)', fontSize: '12px', color: 'var(--hs-text-muted)' }}>
                HostingSignal v1.0.0
            </div>
        </aside>
    );
}

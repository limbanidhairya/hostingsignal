'use client';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

export default function TopBar({ collapsed }) {
    const pathname = usePathname();
    const { user, logout } = useAuth();

    const segments = pathname.split('/').filter(Boolean);
    const breadcrumbs = segments.map((s, i) => ({
        label: s.charAt(0).toUpperCase() + s.slice(1),
        path: '/' + segments.slice(0, i + 1).join('/'),
    }));

    const initials = user?.name
        ? user.name.split(' ').map(n => n[0]).join('').toUpperCase()
        : 'U';

    return (
        <div className="topbar" style={{ left: collapsed ? '70px' : '260px' }}>
            <div className="breadcrumbs">
                <span>HostingSignal</span>
                {breadcrumbs.map((b, i) => (
                    <span key={i}> / <strong>{b.label}</strong></span>
                ))}
            </div>

            <div className="topbar-search">
                <span className="search-icon">🔍</span>
                <input type="text" placeholder="Search settings, tools, domains..." className="search-input" />
            </div>

            <div className="topbar-actions">
                <button className="topbar-btn" title="Help">❓</button>
                <button className="topbar-btn" title="Notifications">
                    🔔
                    <span className="notification-dot"></span>
                </button>
                <div className="user-menu">
                    <div className="user-avatar">{initials}</div>
                    <div className="user-info">
                        <span className="user-name">{user?.name || 'User'}</span>
                        <span className="user-role">{user?.role === 'admin' ? 'Administrator' : user?.role === 'reseller' ? 'Reseller' : 'Client'}</span>
                    </div>
                    <button className="topbar-btn" onClick={logout} title="Logout" style={{ marginLeft: '8px', fontSize: '12px' }}>
                        🚪
                    </button>
                </div>
            </div>
        </div>
    );
}

'use client';
import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navSections = [
    {
        title: 'Main',
        items: [
            { icon: '📊', label: 'Dashboard', href: '/dashboard' },
            { icon: '🌐', label: 'Websites', href: '/websites', badge: '3' },
            { icon: '🔗', label: 'Domains', href: '/domains' },
        ]
    },
    {
        title: 'Services',
        items: [
            { icon: '📧', label: 'Email', href: '/email' },
            { icon: '🗄️', label: 'Databases', href: '/databases' },
            { icon: '📁', label: 'File Manager', href: '/files' },
        ]
    },
    {
        title: 'Security & System',
        items: [
            { icon: '🔒', label: 'Security', href: '/security' },
            { icon: '🌍', label: 'DNS Zone', href: '/dns' },
            { icon: '💾', label: 'Backups', href: '/backups' },
            { icon: '🧩', label: 'Plugins', href: '/plugins' },
        ]
    },
    {
        title: 'Administration',
        items: [
            { icon: '🔑', label: 'Licenses', href: '/admin/licenses' },
            { icon: '👥', label: 'Users', href: '/admin/users' },
            { icon: '⚙️', label: 'Settings', href: '/settings' },
        ]
    }
];

export default function Sidebar({ collapsed, onToggle }) {
    const pathname = usePathname();

    return (
        <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
            <div className="sidebar-logo">
                <div className="logo-icon">HS</div>
                <span className="logo-text">HostingSignal</span>
            </div>

            <nav className="sidebar-nav">
                {navSections.map((section, si) => (
                    <div key={si} className="nav-section">
                        <div className="nav-section-title">{section.title}</div>
                        {section.items.map((item, ii) => {
                            const isActive = pathname === item.href ||
                                (item.href !== '/dashboard' && pathname?.startsWith(item.href));
                            return (
                                <Link
                                    key={ii}
                                    href={item.href}
                                    className={`nav-item ${isActive ? 'active' : ''}`}
                                    title={collapsed ? item.label : undefined}
                                >
                                    <span className="nav-icon">{item.icon}</span>
                                    <span className="nav-label">{item.label}</span>
                                    {item.badge && <span className="nav-badge">{item.badge}</span>}
                                </Link>
                            );
                        })}
                    </div>
                ))}
            </nav>

            <div className="sidebar-footer">
                <button className="sidebar-collapse-btn" onClick={onToggle}>
                    {collapsed ? '▶' : '◀'}
                </button>
            </div>
        </aside>
    );
}

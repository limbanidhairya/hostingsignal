'use client';
import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

export default function DashboardPage() {
    const { user } = useAuth();
    const { showToast, ToastContainer } = useToast();
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadStats();
    }, []);

    async function loadStats() {
        try {
            const data = await api.getDashboardStats();
            setStats(data);
        } catch (err) {
            // Fallback to demo data
            setStats({
                total_licenses: 6, active_licenses: 4, expired_licenses: 1, suspended_licenses: 1,
                monthly_revenue: 270, tier_breakdown: { free: 0, pro: 2, business: 1, enterprise: 1 },
                total_users: 4, active_users: 3
            });
        } finally {
            setLoading(false);
        }
    }

    const quickActions = [
        { icon: '🌐', label: 'New Website', href: '/websites' },
        { icon: '🔒', label: 'SSL Certificates', href: '/security' },
        { icon: '📧', label: 'Create Email', href: '/email' },
        { icon: '💾', label: 'Backup Now', href: '/backups' },
        { icon: '🛡️', label: 'Firewall', href: '/security' },
        { icon: '📁', label: 'File Manager', href: '/files' },
    ];

    function ResourceCircle({ percent, color, label, detail }) {
        const radius = 45;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (percent / 100) * circumference;
        return (
            <div className="clay-card" style={{ padding: 'var(--space-md)', display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
                <svg width="120" height="120" viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r={radius} fill="none" stroke="var(--border-light)" strokeWidth="8" />
                    <circle cx="60" cy="60" r={radius} fill="none" stroke={color} strokeWidth="8"
                        strokeDasharray={circumference} strokeDashoffset={offset}
                        strokeLinecap="round" transform="rotate(-90 60 60)"
                        style={{ transition: 'stroke-dashoffset 1s ease' }} />
                    <text x="60" y="55" textAnchor="middle" fill="var(--text-primary)" fontSize="20" fontWeight="700">{percent}%</text>
                    <text x="60" y="75" textAnchor="middle" fill="var(--text-muted)" fontSize="10">usage</text>
                </svg>
                <div style={{ marginLeft: 'var(--space-md)' }}>
                    <div style={{ fontWeight: 600 }}>{label}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{detail}</div>
                    <div className="progress-bar" style={{ marginTop: '8px', width: '120px' }}>
                        <div className="progress-fill" style={{ width: `${percent}%`, background: color }} />
                    </div>
                </div>
            </div>
        );
    }

    if (loading) {
        return <div className="animate-fade" style={{ padding: 'var(--space-xl)', textAlign: 'center', color: 'var(--text-muted)' }}>Loading dashboard...</div>;
    }

    return (
        <div className="animate-fade">
            <ToastContainer />
            <div className="page-header">
                <div>
                    <h1 className="glow-text">Dashboard</h1>
                    <p>Welcome back, {user?.name}! Here&apos;s an overview of your hosting environment.</p>
                </div>
                <a href="/websites"><button className="btn skeuo-btn-primary">+ Create Website</button></a>
            </div>

            {/* Stats */}
            <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
                <div className="stat-card green clay-card" style={{ background: 'transparent' }}>
                    <div className="stat-icon green">🌐</div>
                    <div className="stat-content">
                        <div className="stat-value glow-text">{stats.active_licenses}</div>
                        <div className="stat-label">Active Licenses</div>
                    </div>
                </div>
                <div className="stat-card blue clay-card" style={{ background: 'transparent' }}>
                    <div className="stat-icon blue">👥</div>
                    <div className="stat-content">
                        <div className="stat-value glow-text">{stats.total_users}</div>
                        <div className="stat-label">Total Users</div>
                    </div>
                </div>
                <div className="stat-card purple clay-card" style={{ background: 'transparent' }}>
                    <div className="stat-icon purple">🔑</div>
                    <div className="stat-content">
                        <div className="stat-value glow-text">{stats.total_licenses}</div>
                        <div className="stat-label">Total Licenses</div>
                    </div>
                </div>
                <div className="stat-card orange clay-card" style={{ background: 'transparent' }}>
                    <div className="stat-icon orange">💰</div>
                    <div className="stat-content">
                        <div className="stat-value glow-text">${stats.monthly_revenue}</div>
                        <div className="stat-label">Monthly Revenue</div>
                    </div>
                </div>
            </div>

            {/* Resource Usage */}
            <h2 style={{ fontSize: '18px', fontWeight: 600, margin: 'var(--space-lg) 0 var(--space-md)' }}>Resource Usage</h2>
            <div className="resource-grid">
                <ResourceCircle percent={34} color="var(--primary)" label="CPU" detail="34% / 4 vCPU" />
                <ResourceCircle percent={62} color="var(--accent-green)" label="RAM" detail="2.5 GB / 4 GB" />
                <ResourceCircle percent={45} color="var(--accent-blue)" label="Disk" detail="22.5 GB / 50 GB" />
                <ResourceCircle percent={18} color="var(--accent-orange)" label="Bandwidth" detail="180 GB / 1 TB" />
            </div>

            {/* Quick Actions */}
            <h2 style={{ fontSize: '18px', fontWeight: 600, margin: 'var(--space-lg) 0 var(--space-md)' }} className="glow-text">Quick Actions</h2>
            <div className="quick-actions">
                {quickActions.map((action, i) => (
                    <a key={i} href={action.href} className="quick-action-card clay-card" style={{ padding: 'var(--space-lg)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-sm)', textAlign: 'center', textDecoration: 'none' }}>
                        <div className="quick-action-icon" style={{ fontSize: '24px' }}>{action.icon}</div>
                        <span className="quick-action-label" style={{ color: 'var(--text-primary)', fontWeight: '600' }}>{action.label}</span>
                    </a>
                ))}
            </div>

            {/* License Tier Breakdown */}
            <h2 style={{ fontSize: '18px', fontWeight: 600, margin: 'var(--space-lg) 0 var(--space-md)' }} className="glow-text">License Distribution</h2>
            <div className="liquid-glass" style={{ padding: 'var(--space-lg)' }}>
                {Object.entries(stats.tier_breakdown).map(([tier, count], i) => {
                    const total = stats.total_licenses || 1;
                    const pct = Math.round((count / total) * 100);
                    const colors = { free: 'var(--accent-blue)', pro: 'var(--primary)', business: 'var(--accent-orange)', enterprise: 'var(--accent-green)' };
                    return (
                        <div key={tier} style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: i < 3 ? '14px' : 0 }}>
                            <span style={{ width: '80px', fontSize: '13px', fontWeight: 600, textTransform: 'capitalize' }}>{tier}</span>
                            <div className="progress-bar" style={{ flex: 1 }}>
                                <div className="progress-fill" style={{ width: `${pct}%`, background: colors[tier] }} />
                            </div>
                            <span style={{ fontSize: '13px', fontWeight: 600, width: '40px', textAlign: 'right' }}>{count}</span>
                        </div>
                    );
                })}
            </div>

            {/* Server Info */}
            <h2 style={{ fontSize: '18px', fontWeight: 600, margin: 'var(--space-lg) 0 var(--space-md)' }} className="glow-text">Server Information</h2>
            <div className="liquid-glass" style={{ padding: 'var(--space-lg)' }}>
                <div className="grid-2">
                    {[
                        { label: 'Hostname', value: 'srv1.hostingsignal.com' },
                        { label: 'OS', value: 'Ubuntu 22.04 LTS' },
                        { label: 'Web Server', value: 'OpenLiteSpeed 1.7' },
                        { label: 'PHP Version', value: '8.1, 8.2, 8.3' },
                        { label: 'MySQL', value: 'MariaDB 11.2' },
                        { label: 'Panel Version', value: 'HostingSignal v1.0.0' },
                    ].map((item, i) => (
                        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>{item.label}</span>
                            <span style={{ fontWeight: 600, fontSize: '13px' }}>{item.value}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

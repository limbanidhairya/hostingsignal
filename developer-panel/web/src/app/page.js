'use client';
import { useState, useEffect } from 'react';

const NAV_ITEMS = [
    { label: 'Dashboard', icon: '📊', id: 'dashboard' },
    { label: 'Licenses', icon: '🔑', id: 'licenses' },
    { label: 'Plugins', icon: '🔌', id: 'plugins' },
    { label: 'Clusters', icon: '🖥️', id: 'clusters' },
    { label: 'Updates', icon: '📦', id: 'updates' },
    { label: 'Analytics', icon: '📈', id: 'analytics' },
    { label: 'Monitoring', icon: '💓', id: 'monitoring' },
];

const API_URL = typeof window !== 'undefined'
    ? `${window.location.protocol}//${window.location.hostname}:9000`
    : 'http://localhost:9000';

export default function DevPanelPage() {
    const [activePage, setActivePage] = useState('dashboard');
    const [stats, setStats] = useState({
        totalServers: 142, activeServers: 128, totalLicenses: 856,
        activeLicenses: 734, totalPlugins: 23, totalDownloads: 45200,
    });

    return (
        <div className="dev-layout">
            {/* Sidebar */}
            <aside className="dev-sidebar">
                <div className="dev-sidebar-logo">
                    <div className="icon">HS</div>
                    <div className="text">
                        HostingSignal
                        <small>Developer Panel</small>
                    </div>
                </div>
                <div className="dev-nav-section">Management</div>
                {NAV_ITEMS.map(item => (
                    <a key={item.id}
                        className={`dev-nav-item ${activePage === item.id ? 'active' : ''}`}
                        onClick={() => setActivePage(item.id)}
                        style={{ cursor: 'pointer' }}>
                        <span>{item.icon}</span>
                        <span>{item.label}</span>
                    </a>
                ))}
            </aside>

            {/* Main Content */}
            <main className="dev-main">
                {activePage === 'dashboard' && <DashboardView stats={stats} />}
                {activePage === 'licenses' && <LicensesView />}
                {activePage === 'plugins' && <PluginsView />}
                {activePage === 'clusters' && <ClustersView />}
                {activePage === 'updates' && <UpdatesView />}
                {activePage === 'analytics' && <AnalyticsView />}
                {activePage === 'monitoring' && <MonitoringView />}
            </main>
        </div>
    );
}

function DashboardView({ stats }) {
    const statCards = [
        { label: 'Total Servers', value: stats.totalServers, change: '+12 this week', up: true, color: 'var(--accent-blue)' },
        { label: 'Active Licenses', value: stats.activeLicenses, change: '+45 this month', up: true, color: 'var(--accent-green)' },
        { label: 'Published Plugins', value: stats.totalPlugins, change: '+3 new', up: true, color: 'var(--accent-purple)' },
        { label: 'Total Downloads', value: stats.totalDownloads.toLocaleString(), change: '+2.4k today', up: true, color: 'var(--accent-cyan)' },
    ];

    const recentActivity = [
        { text: 'New server registered: srv-eu-03.hostingsignal.com', time: '2 min ago', color: 'var(--accent-blue)' },
        { text: 'Plugin "backup-s3" v2.1.0 published to marketplace', time: '15 min ago', color: 'var(--accent-green)' },
        { text: 'License HS-A4F2 activated for domain example.com', time: '32 min ago', color: 'var(--accent-purple)' },
        { text: 'Panel update v1.2.1 deployed to stable channel', time: '1 hour ago', color: 'var(--accent-yellow)' },
        { text: 'Server srv-us-07 reported high CPU (92%)', time: '2 hours ago', color: 'var(--accent-red)' },
        { text: 'Cluster "asia-pacific" created with 5 nodes', time: '3 hours ago', color: 'var(--accent-cyan)' },
    ];

    return (
        <>
            <div className="dev-header">
                <div>
                    <h1>Developer Dashboard</h1>
                    <p>Overview of the HostingSignal ecosystem</p>
                </div>
                <button className="btn btn-primary">+ Create License</button>
            </div>

            <div className="stats-grid">
                {statCards.map(s => (
                    <div key={s.label} className="stat-card">
                        <div className="label">{s.label}</div>
                        <div className="value" style={{ color: s.color }}>{s.value}</div>
                        <div className={`change ${s.up ? 'up' : 'down'}`}>{s.up ? '↑' : '↓'} {s.change}</div>
                    </div>
                ))}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                <div className="card">
                    <div className="card-header"><h3>Recent Activity</h3></div>
                    <div className="card-body">
                        {recentActivity.map((item, i) => (
                            <div key={i} className="activity-item">
                                <div className="activity-dot" style={{ background: item.color }} />
                                <div>
                                    <div className="activity-text">{item.text}</div>
                                    <div className="activity-time">{item.time}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="card">
                    <div className="card-header"><h3>Server Fleet Health</h3></div>
                    <div className="card-body">
                        {[
                            { region: 'US East', servers: 24, online: 24, cpu: '34%' },
                            { region: 'US West', servers: 18, online: 17, cpu: '41%' },
                            { region: 'EU Central', servers: 32, online: 30, cpu: '28%' },
                            { region: 'Asia Pacific', servers: 28, online: 28, cpu: '52%' },
                            { region: 'South America', servers: 12, online: 11, cpu: '38%' },
                        ].map((r, i) => (
                            <div key={i} style={{
                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                padding: '10px 0', borderBottom: i < 4 ? '1px solid var(--border)' : 'none'
                            }}>
                                <div style={{ fontWeight: 600, fontSize: 14 }}>{r.region}</div>
                                <div style={{ display: 'flex', gap: 16, fontSize: 13, color: 'var(--text-secondary)' }}>
                                    <span>{r.online}/{r.servers} online</span>
                                    <span>CPU: {r.cpu}</span>
                                    <span className="badge green">{r.online === r.servers ? 'Healthy' : 'Degraded'}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </>
    );
}

function LicensesView() {
    const licenses = [
        { key: 'HS-A4F2-B8C1-D9E0', plan: 'Enterprise', status: 'active', domain: 'example.com', created: '2025-12-01', expires: '2026-12-01' },
        { key: 'HS-F1G2-H3I4-J5K6', plan: 'Professional', status: 'active', domain: 'mysite.net', created: '2025-11-15', expires: '2026-11-15' },
        { key: 'HS-L7M8-N9O0-P1Q2', plan: 'Starter', status: 'expired', domain: 'oldsite.org', created: '2024-10-01', expires: '2025-10-01' },
        { key: 'HS-R3S4-T5U6-V7W8', plan: 'Enterprise', status: 'active', domain: 'bigco.io', created: '2026-01-10', expires: '2027-01-10' },
    ];

    return (
        <>
            <div className="dev-header">
                <div><h1>License Management</h1><p>Create, manage, and monitor license keys</p></div>
                <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-secondary">Bulk Create</button>
                    <button className="btn btn-primary">+ Create License</button>
                </div>
            </div>
            <div className="stats-grid">
                <div className="stat-card"><div className="label">Total Licenses</div><div className="value" style={{ color: 'var(--accent-blue)' }}>856</div></div>
                <div className="stat-card"><div className="label">Active</div><div className="value" style={{ color: 'var(--accent-green)' }}>734</div></div>
                <div className="stat-card"><div className="label">Expired</div><div className="value" style={{ color: 'var(--accent-yellow)' }}>98</div></div>
                <div className="stat-card"><div className="label">Revoked</div><div className="value" style={{ color: 'var(--accent-red)' }}>24</div></div>
            </div>
            <div className="card">
                <div className="card-header"><h3>Recent Licenses</h3></div>
                <table>
                    <thead><tr><th>License Key</th><th>Plan</th><th>Domain</th><th>Status</th><th>Expires</th><th>Actions</th></tr></thead>
                    <tbody>
                        {licenses.map(l => (
                            <tr key={l.key}>
                                <td style={{ fontFamily: 'monospace', fontSize: 13 }}>{l.key}</td>
                                <td><span className="badge purple">{l.plan}</span></td>
                                <td style={{ fontWeight: 600 }}>{l.domain}</td>
                                <td><span className={`badge ${l.status === 'active' ? 'green' : 'red'}`}>{l.status}</span></td>
                                <td style={{ color: 'var(--text-muted)' }}>{l.expires}</td>
                                <td><button className="btn btn-sm btn-secondary">Manage</button></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </>
    );
}

function PluginsView() {
    const plugins = [
        { name: 'Security Scanner', slug: 'security-scanner', version: '1.0.0', category: 'security', status: 'published', downloads: 12400 },
        { name: 'Backup S3', slug: 'backup-s3', version: '2.1.0', category: 'backup', status: 'published', downloads: 8750 },
        { name: 'Analytics Widget', slug: 'analytics-widget', version: '1.0.0', category: 'analytics', status: 'published', downloads: 5200 },
        { name: 'Redis Manager', slug: 'redis-manager', version: '1.2.0', category: 'utility', status: 'pending', downloads: 0 },
    ];

    return (
        <>
            <div className="dev-header">
                <div><h1>Plugin Marketplace</h1><p>Manage plugin submissions, reviews, and publishing</p></div>
                <button className="btn btn-primary">+ Submit Plugin</button>
            </div>
            <div className="stats-grid">
                <div className="stat-card"><div className="label">Published</div><div className="value" style={{ color: 'var(--accent-green)' }}>23</div></div>
                <div className="stat-card"><div className="label">Pending Review</div><div className="value" style={{ color: 'var(--accent-yellow)' }}>5</div></div>
                <div className="stat-card"><div className="label">Total Downloads</div><div className="value" style={{ color: 'var(--accent-blue)' }}>45.2K</div></div>
                <div className="stat-card"><div className="label">Developers</div><div className="value" style={{ color: 'var(--accent-purple)' }}>18</div></div>
            </div>
            <div className="card">
                <div className="card-header"><h3>All Plugins</h3></div>
                <table>
                    <thead><tr><th>Plugin</th><th>Version</th><th>Category</th><th>Status</th><th>Downloads</th><th>Actions</th></tr></thead>
                    <tbody>
                        {plugins.map(p => (
                            <tr key={p.slug}>
                                <td style={{ fontWeight: 600 }}>{p.name}</td>
                                <td style={{ fontFamily: 'monospace' }}>v{p.version}</td>
                                <td><span className="badge blue">{p.category}</span></td>
                                <td><span className={`badge ${p.status === 'published' ? 'green' : 'yellow'}`}>{p.status}</span></td>
                                <td>{p.downloads.toLocaleString()}</td>
                                <td><div style={{ display: 'flex', gap: 6 }}>
                                    {p.status === 'pending' && <button className="btn btn-sm btn-primary">Approve</button>}
                                    <button className="btn btn-sm btn-secondary">View</button>
                                </div></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </>
    );
}

function ClustersView() {
    const clusters = [
        { name: 'us-east-01', region: 'US East', servers: 24, online: 24, status: 'healthy', cpu: 34 },
        { name: 'eu-central-01', region: 'EU Central', servers: 32, online: 30, status: 'degraded', cpu: 48 },
        { name: 'asia-pacific-01', region: 'Asia Pacific', servers: 28, online: 28, status: 'healthy', cpu: 52 },
    ];

    return (
        <>
            <div className="dev-header">
                <div><h1>Cluster Management</h1><p>Monitor and control server clusters across regions</p></div>
                <button className="btn btn-primary">+ Create Cluster</button>
            </div>
            <div className="stats-grid">
                <div className="stat-card"><div className="label">Total Clusters</div><div className="value" style={{ color: 'var(--accent-blue)' }}>6</div></div>
                <div className="stat-card"><div className="label">Total Servers</div><div className="value" style={{ color: 'var(--accent-cyan)' }}>142</div></div>
                <div className="stat-card"><div className="label">Online</div><div className="value" style={{ color: 'var(--accent-green)' }}>128</div></div>
                <div className="stat-card"><div className="label">Avg CPU</div><div className="value" style={{ color: 'var(--accent-yellow)' }}>38%</div></div>
            </div>
            <div className="card">
                <div className="card-header"><h3>Cluster Overview</h3></div>
                <table>
                    <thead><tr><th>Cluster</th><th>Region</th><th>Servers</th><th>Health</th><th>Avg CPU</th><th>Actions</th></tr></thead>
                    <tbody>
                        {clusters.map(c => (
                            <tr key={c.name}>
                                <td style={{ fontWeight: 600 }}>{c.name}</td>
                                <td>{c.region}</td>
                                <td>{c.online}/{c.servers}</td>
                                <td><span className={`badge ${c.status === 'healthy' ? 'green' : 'yellow'}`}>{c.status}</span></td>
                                <td>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <div style={{
                                            width: 80, height: 6, background: 'rgba(255,255,255,0.1)',
                                            borderRadius: 3, overflow: 'hidden'
                                        }}>
                                            <div style={{
                                                width: `${c.cpu}%`, height: '100%',
                                                background: c.cpu > 70 ? 'var(--accent-red)' : c.cpu > 50 ? 'var(--accent-yellow)' : 'var(--accent-green)',
                                                borderRadius: 3,
                                            }} />
                                        </div>
                                        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{c.cpu}%</span>
                                    </div>
                                </td>
                                <td><button className="btn btn-sm btn-secondary">Manage</button></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </>
    );
}

function UpdatesView() {
    const updates = [
        { version: '1.2.1', channel: 'stable', status: 'published', critical: false, size: '24.5 MB', date: '2026-03-08' },
        { version: '1.3.0-beta', channel: 'beta', status: 'published', critical: false, size: '26.1 MB', date: '2026-03-05' },
        { version: '1.2.0', channel: 'stable', status: 'published', critical: true, size: '23.8 MB', date: '2026-02-28' },
    ];

    return (
        <>
            <div className="dev-header">
                <div><h1>Update Management</h1><p>Package and distribute panel updates</p></div>
                <button className="btn btn-primary">+ Create Update</button>
            </div>
            <div className="card">
                <div className="card-header"><h3>Recent Updates</h3></div>
                <table>
                    <thead><tr><th>Version</th><th>Channel</th><th>Status</th><th>Size</th><th>Released</th><th>Actions</th></tr></thead>
                    <tbody>
                        {updates.map(u => (
                            <tr key={u.version}>
                                <td style={{ fontWeight: 600, fontFamily: 'monospace' }}>
                                    v{u.version} {u.critical && <span className="badge red" style={{ marginLeft: 6 }}>Critical</span>}
                                </td>
                                <td><span className={`badge ${u.channel === 'stable' ? 'green' : 'blue'}`}>{u.channel}</span></td>
                                <td><span className="badge green">{u.status}</span></td>
                                <td style={{ color: 'var(--text-muted)' }}>{u.size}</td>
                                <td style={{ color: 'var(--text-muted)' }}>{u.date}</td>
                                <td><div style={{ display: 'flex', gap: 6 }}>
                                    <button className="btn btn-sm btn-secondary">Changelog</button>
                                    <button className="btn btn-sm btn-secondary">Unpublish</button>
                                </div></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </>
    );
}

function AnalyticsView() {
    return (
        <>
            <div className="dev-header">
                <div><h1>Analytics</h1><p>Installation statistics, usage patterns, and growth metrics</p></div>
            </div>
            <div className="stats-grid">
                <div className="stat-card"><div className="label">Installs (30d)</div><div className="value" style={{ color: 'var(--accent-green)' }}>1,247</div><div className="change up">↑ +18% vs last month</div></div>
                <div className="stat-card"><div className="label">Active Panels</div><div className="value" style={{ color: 'var(--accent-blue)' }}>3,891</div><div className="change up">↑ +8% vs last month</div></div>
                <div className="stat-card"><div className="label">Error Rate</div><div className="value" style={{ color: 'var(--accent-red)' }}>0.12%</div><div className="change up">↓ -0.03%</div></div>
                <div className="stat-card"><div className="label">Avg Uptime</div><div className="value" style={{ color: 'var(--accent-cyan)' }}>99.7%</div></div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                <div className="card">
                    <div className="card-header"><h3>Version Distribution</h3></div>
                    <div className="card-body">
                        {[
                            { version: 'v1.2.1', count: 1203, pct: 42 },
                            { version: 'v1.2.0', count: 892, pct: 31 },
                            { version: 'v1.1.x', count: 534, pct: 19 },
                            { version: 'v1.0.x', count: 231, pct: 8 },
                        ].map(v => (
                            <div key={v.version} style={{ marginBottom: 12 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, marginBottom: 4 }}>
                                    <span style={{ fontWeight: 600 }}>{v.version}</span>
                                    <span style={{ color: 'var(--text-muted)' }}>{v.count} servers ({v.pct}%)</span>
                                </div>
                                <div style={{ height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 3 }}>
                                    <div style={{ width: `${v.pct}%`, height: '100%', background: 'var(--primary)', borderRadius: 3 }} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="card">
                    <div className="card-header"><h3>OS Distribution</h3></div>
                    <div className="card-body">
                        {[
                            { os: 'Ubuntu 22.04', count: 1450, pct: 51 },
                            { os: 'Ubuntu 24.04', count: 680, pct: 24 },
                            { os: 'Debian 12', count: 420, pct: 15 },
                            { os: 'AlmaLinux 9', count: 310, pct: 10 },
                        ].map(o => (
                            <div key={o.os} style={{ marginBottom: 12 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, marginBottom: 4 }}>
                                    <span style={{ fontWeight: 600 }}>{o.os}</span>
                                    <span style={{ color: 'var(--text-muted)' }}>{o.count} ({o.pct}%)</span>
                                </div>
                                <div style={{ height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 3 }}>
                                    <div style={{ width: `${o.pct}%`, height: '100%', background: 'var(--accent-cyan)', borderRadius: 3 }} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </>
    );
}

function MonitoringView() {
    const servers = [
        { hostname: 'srv-us-01', ip: '203.0.113.10', cpu: 28, ram: 45, disk: 62, status: 'online' },
        { hostname: 'srv-us-02', ip: '203.0.113.11', cpu: 73, ram: 68, disk: 41, status: 'online' },
        { hostname: 'srv-eu-01', ip: '198.51.100.5', cpu: 15, ram: 32, disk: 58, status: 'online' },
        { hostname: 'srv-eu-03', ip: '198.51.100.7', cpu: 0, ram: 0, disk: 0, status: 'offline' },
        { hostname: 'srv-ap-01', ip: '192.0.2.20', cpu: 92, ram: 87, disk: 78, status: 'online' },
    ];

    const metricBar = (val) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 60, height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{
                    width: `${val}%`, height: '100%',
                    background: val > 80 ? 'var(--accent-red)' : val > 60 ? 'var(--accent-yellow)' : 'var(--accent-green)',
                    borderRadius: 3,
                }} />
            </div>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', minWidth: 30 }}>{val}%</span>
        </div>
    );

    return (
        <>
            <div className="dev-header">
                <div><h1>Server Monitoring</h1><p>Real-time server fleet health and metrics</p></div>
            </div>
            <div className="card">
                <div className="card-header"><h3>Server Fleet</h3></div>
                <table>
                    <thead><tr><th>Hostname</th><th>IP Address</th><th>Status</th><th>CPU</th><th>RAM</th><th>Disk</th></tr></thead>
                    <tbody>
                        {servers.map(s => (
                            <tr key={s.hostname}>
                                <td style={{ fontWeight: 600 }}>{s.hostname}</td>
                                <td style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{s.ip}</td>
                                <td><span className={`badge ${s.status === 'online' ? 'green' : 'red'}`}>{s.status}</span></td>
                                <td>{s.status === 'online' ? metricBar(s.cpu) : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
                                <td>{s.status === 'online' ? metricBar(s.ram) : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
                                <td>{s.status === 'online' ? metricBar(s.disk) : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </>
    );
}

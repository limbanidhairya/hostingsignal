'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_HSDEV_API_BASE || 'http://localhost:2087';

const NAV_ITEMS = [
    { label: 'Dashboard', icon: 'dashboard', id: 'dashboard' },
    { label: 'Licenses', icon: 'key', id: 'licenses' },
    { label: 'Plugins', icon: 'extension', id: 'plugins' },
    { label: 'Clusters', icon: 'dns', id: 'clusters' },
    { label: 'Updates', icon: 'system_update', id: 'updates' },
    { label: 'Analytics', icon: 'query_stats', id: 'analytics' },
    { label: 'Monitoring', icon: 'monitoring', id: 'monitoring' },
];

export default function DevPanelPage() {
    const router = useRouter();
    const [activePage, setActivePage] = useState('dashboard');
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [authReady, setAuthReady] = useState(false);
    const [currentUser, setCurrentUser] = useState(null);

    useEffect(() => {
        const token = localStorage.getItem('hsdev_token');
        if (!token) {
            router.replace('/login');
            return;
        }

        const bootstrap = async () => {
            try {
                const meRes = await fetch(`${API_BASE}/api/auth/me`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!meRes.ok) {
                    throw new Error('Session expired');
                }
                const me = await meRes.json();
                setCurrentUser(me);
                setAuthReady(true);

                const statsRes = await fetch(`${API_BASE}/api/analytics/stats`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                const data = statsRes.ok ? await statsRes.json() : null;
                setStats(
                    data || {
                        totalServers: 0, activeServers: 0, totalLicenses: 0,
                        activeLicenses: 0, totalPlugins: 0, totalDownloads: 0,
                        recentActivity: []
                    }
                );
            } catch (err) {
                console.error('Auth/bootstrap failed:', err);
                localStorage.removeItem('hsdev_token');
                router.replace('/login');
            } finally {
                setLoading(false);
            }
        };

        bootstrap();
    }, [router]);

    const handleLogout = () => {
        localStorage.removeItem('hsdev_token');
        router.replace('/login');
    };

    if (loading || !authReady || !stats) {
        return <div className="flex h-screen items-center justify-center bg-background-dark text-slate-100">Authenticating developer session...</div>;
    }

    return (
        <div className="flex h-screen overflow-hidden">
            {/* Sidebar */}
            <aside className="w-64 flex-shrink-0 bg-card-dark/50 border-r border-border-dark hidden lg:flex flex-col">
                <div className="p-6 flex items-center gap-3">
                    <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center text-white shadow-lg shadow-primary/20">
                        <span className="material-symbols-outlined text-2xl">rocket_launch</span>
                    </div>
                    <h1 className="text-xl font-bold tracking-tight text-slate-100 uppercase">HS-Dev</h1>
                </div>

                <nav className="flex-1 px-4 mt-4 space-y-1">
                    {NAV_ITEMS.map(item => (
                        <a key={item.id}
                            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors cursor-pointer ${activePage === item.id
                                ? 'bg-primary/10 text-primary font-medium border border-primary/20 shadow-inner'
                                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50'
                                }`}
                            onClick={() => setActivePage(item.id)}>
                            <span className="material-symbols-outlined">{item.icon}</span>
                            {item.label}
                        </a>
                    ))}
                </nav>

                <div className="p-4 border-t border-border-dark">
                    <div className="flex items-center gap-3 px-2">
                        <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center text-slate-300 font-bold border-2 border-primary/30">
                            {(currentUser?.username || 'A').charAt(0).toUpperCase()}
                        </div>
                        <div>
                            <p className="text-sm font-semibold text-slate-100">{currentUser?.username || 'Developer'}</p>
                            <p className="text-xs text-slate-500">{currentUser?.role || 'admin'}</p>
                        </div>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="mt-3 w-full px-3 py-2 text-xs font-semibold rounded border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                    >
                        Logout
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-background-dark">
                <header className="h-16 flex items-center justify-between px-8 bg-background-dark/80 backdrop-blur-md border-b border-border-dark sticky top-0 z-10">
                    <div className="flex items-center flex-1">
                        <div className="relative w-96 max-w-full">
                            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xl">search</span>
                            <input type="text" placeholder="Search resources or logs..."
                                className="w-full bg-slate-800/50 border-none rounded-lg pl-10 pr-4 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:ring-1 focus:ring-primary outline-none" />
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <button className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-slate-800 transition-colors relative text-slate-400">
                            <span className="material-symbols-outlined">notifications</span>
                            <span className="absolute top-2 right-2.5 w-2 h-2 bg-accent rounded-full border border-background-dark"></span>
                        </button>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto p-8">
                    {activePage === 'dashboard' && <DashboardView stats={stats} />}
                    {activePage === 'licenses' && <LicensesView />}
                    {activePage === 'plugins' && <PluginsView />}
                    {activePage === 'clusters' && <ClustersView />}
                    {activePage === 'updates' && <UpdatesView />}
                    {activePage === 'analytics' && <AnalyticsView />}
                    {activePage === 'monitoring' && <MonitoringView />}
                </div>
            </main>
        </div>
    );
}

function StatCard({ label, value, change, isUp, colorClass, iconClass }) {
    return (
        <div className="glass p-6 rounded-xl flex flex-col gap-2 relative overflow-hidden group hover:border-primary/50 transition-all">
            <div className="flex items-center justify-between mb-2 z-10">
                <span className="text-slate-400 text-sm font-medium uppercase tracking-wider">{label}</span>
                <span className={`material-symbols-outlined ${colorClass}`}>{iconClass}</span>
            </div>
            <div className="text-3xl font-bold text-slate-100 z-10">{value}</div>
            {change && (
                <div className={`text-xs ${isUp ? 'text-green-400' : 'text-red-400'} flex items-center gap-1 z-10`}>
                    <span className="material-symbols-outlined text-xs">{isUp ? 'trending_up' : 'trending_down'}</span>
                    {change}
                </div>
            )}
        </div>
    );
}

function DashboardView({ stats }) {
    const recentActivity = [
        { text: 'New server registered: srv-eu-03', time: '2 min ago', type: 'info' },
        { text: 'Plugin "backup-s3" updated', time: '15 min ago', type: 'success' },
        { text: 'License activated: example.com', time: '32 min ago', type: 'success' },
        { text: 'Server srv-us-07 reported high CPU (92%)', time: '2 hours ago', type: 'warning' },
    ];

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-2xl font-bold text-slate-100">Global Overview</h2>
                    <p className="text-slate-400 mt-1">HostingSignal ecosystem metrics in real-time.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard label="Total Servers" value={stats.totalServers} change="+12 this week" isUp={true} colorClass="text-blue-500" iconClass="dns" />
                <StatCard label="Active Licenses" value={stats.activeLicenses} change="+45 this month" isUp={true} colorClass="text-green-500" iconClass="key" />
                <StatCard label="Plugins" value={stats.totalPlugins} change="+3 new" isUp={true} colorClass="text-purple-500" iconClass="extension" />
                <StatCard label="Downloads" value={stats.totalDownloads.toLocaleString()} change="+2.4k today" isUp={true} colorClass="text-accent" iconClass="download" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="glass rounded-xl overflow-hidden">
                    <div className="px-6 py-4 border-b border-border-dark flex justify-between items-center">
                        <h3 className="font-semibold text-slate-100">Recent Activity</h3>
                        <button className="text-sm text-primary hover:underline">View All</button>
                    </div>
                    <div className="p-0">
                        <table className="w-full text-left text-sm">
                            <tbody className="divide-y divide-border-dark/50">
                                {recentActivity.map((a, i) => (
                                    <tr key={i} className="hover:bg-slate-800/20 transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-3">
                                                    <span className={`w-2 h-2 rounded-full ${a.type === 'warning' ? 'bg-red-500' : 'bg-green-500'}`}></span>
                                                    <span className="text-slate-300">{a.text}</span>
                                                </div>
                                                <span className="text-slate-500 text-xs">{a.time}</span>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div className="glass rounded-xl overflow-hidden">
                    <div className="px-6 py-4 border-b border-border-dark flex justify-between items-center">
                        <h3 className="font-semibold text-slate-100">Server Fleet Health</h3>
                    </div>
                    <div className="p-6 space-y-4">
                        {[
                            { region: 'US East', servers: 24, online: 24, cpu: 34 },
                            { region: 'US West', servers: 18, online: 17, cpu: 41 },
                            { region: 'EU Central', servers: 32, online: 30, cpu: 28 },
                            { region: 'Asia Pacific', servers: 28, online: 28, cpu: 52 },
                        ].map((r, i) => (
                            <div key={i} className="flex justify-between items-center pb-4 border-b border-border-dark last:border-0 last:pb-0">
                                <div className="text-sm font-medium text-slate-200">{r.region}</div>
                                <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
                                    <span>{r.online}/{r.servers} online</span>
                                    <span className={`px-2 py-0.5 rounded border ${r.online === r.servers ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'} uppercase tracking-widest text-[10px] font-bold`}>
                                        {r.online === r.servers ? 'Healthy' : 'Degraded'}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

function LicensesView() {
    const licenses = [
        { key: 'HS-A4F2-B8C1-D9E0', plan: 'Enterprise', status: 'active', domain: 'example.com', expires: '2026-12-01' },
        { key: 'HS-F1G2-H3I4-J5K6', plan: 'Professional', status: 'active', domain: 'mysite.net', expires: '2026-11-15' },
        { key: 'HS-L7M8-N9O0-P1Q2', plan: 'Starter', status: 'expired', domain: 'oldsite.org', expires: '2025-10-01' },
        { key: 'HS-R3S4-T5U6-V7W8', plan: 'Enterprise', status: 'active', domain: 'bigco.io', expires: '2027-01-10' },
    ];

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-2xl font-bold text-slate-100">License Management</h2>
                    <p className="text-slate-400 mt-1">Manage software licenses issued to clients.</p>
                </div>
                <button className="px-4 py-2 bg-primary text-white text-sm font-bold rounded-lg hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20 flex items-center gap-2">
                    <span className="material-symbols-outlined text-[20px]">add</span> Generate License
                </button>
            </div>

            <div className="glass rounded-xl overflow-hidden">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-slate-800/30 border-b border-border-dark text-xs font-bold text-slate-400 uppercase tracking-widest">
                        <tr>
                            <th className="px-6 py-4">License Key</th>
                            <th className="px-6 py-4">Plan</th>
                            <th className="px-6 py-4">Domain</th>
                            <th className="px-6 py-4">Status</th>
                            <th className="px-6 py-4 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border-dark/50 text-sm">
                        {licenses.map(l => (
                            <tr key={l.key} className="hover:bg-slate-800/20 transition-colors">
                                <td className="px-6 py-4 font-mono font-bold text-primary">{l.key}</td>
                                <td className="px-6 py-4"><span className="px-2 py-1 rounded bg-purple-500/10 text-purple-400 text-xs font-bold border border-purple-500/20">{l.plan}</span></td>
                                <td className="px-6 py-4 font-medium text-slate-300">{l.domain}</td>
                                <td className="px-6 py-4"><span className={`px-2 py-1 rounded text-xs font-bold border ${l.status === 'active' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-500 border-red-500/20'}`}>{l.status}</span></td>
                                <td className="px-6 py-4 text-right space-x-2">
                                    <button className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-xs hover:bg-slate-700 text-slate-300 transition-colors">Manage</button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function PluginsView() {
    return <div className="p-8 text-center text-slate-400">Plugins View (To be styled)</div>;
}
function ClustersView() {
    return <div className="p-8 text-center text-slate-400">Clusters View (To be styled)</div>;
}
function UpdatesView() {
    return <div className="p-8 text-center text-slate-400">Updates View (To be styled)</div>;
}
function AnalyticsView() {
    return <div className="p-8 text-center text-slate-400">Analytics View (To be styled)</div>;
}
function MonitoringView() {
    return <div className="p-8 text-center text-slate-400">Monitoring View (To be styled)</div>;
}

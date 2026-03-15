'use client';
import { useState, useEffect, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_HSDEV_API_BASE || '/devapi';

const DEFAULT_STATS = {
    totalServers: 0,
    activeServers: 0,
    totalLicenses: 0,
    activeLicenses: 0,
    totalPlugins: 0,
    totalDownloads: 0,
    recentActivity: [],
};

const resolveApiBases = () => {
    const bases = [];
    if (typeof window !== 'undefined') {
        const host = window.location.hostname;
        const directBase = `${window.location.protocol}//${host}:2087`;
        const isLocalHost = host === 'localhost' || host === '127.0.0.1' || host === '::1';

        // For local runtime, authenticate against direct API first.
        if (isLocalHost) {
            bases.push(directBase, API_BASE);
        } else {
            bases.push(API_BASE, directBase);
        }
    } else {
        bases.push(API_BASE);
    }
    return [...new Set(bases)];
};

const requestWithFallback = async (path, init = {}) => {
    const bases = resolveApiBases();
    let lastError = null;
    for (const base of bases) {
        try {
            const res = await fetch(`${base}${path}`, init);
            const shouldRetry = [404, 405, 502, 503, 504].includes(res.status);
            if (shouldRetry) {
                lastError = new Error(`HTTP ${res.status} from ${base}`);
                continue;
            }
            return { res, base };
        } catch (err) {
            lastError = err;
        }
    }
    throw lastError || new Error('API unavailable');
};

const getCookieToken = () => {
    if (typeof document === 'undefined') return '';
    const match = document.cookie.match(/(?:^|;\s*)hsdev_token=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
};

const getStoredToken = () => {
    try {
        const token = localStorage.getItem('hsdev_token');
        if (token) return token;
    } catch {
        // ignore localStorage issues
    }
    return getCookieToken();
};

const clearStoredToken = () => {
    try {
        localStorage.removeItem('hsdev_token');
    } catch {
        // ignore
    }
    if (typeof document !== 'undefined') {
        document.cookie = 'hsdev_token=; Path=/; Max-Age=0; SameSite=Lax';
    }
};

const NAV_ITEMS = [
    { label: 'Dashboard', icon: 'dashboard', id: 'dashboard' },
    { label: 'Shell', icon: 'terminal', id: 'shell' },
    { label: 'Domains', icon: 'language', id: 'domains' },
    { label: 'Email', icon: 'mail', id: 'email' },
    { label: 'Files', icon: 'folder_open', id: 'files' },
    { label: 'Backups', icon: 'history', id: 'backups' },
    { label: 'Security', icon: 'security', id: 'security' },
    { label: 'Docker', icon: 'deployed_code', id: 'docker' },
    { label: 'Licenses', icon: 'key', id: 'licenses' },
    { label: 'Plugins', icon: 'extension', id: 'plugins' },
    { label: 'Containers', icon: 'deployed_code', id: 'containers' },
    { label: 'WHMCS Audit', icon: 'history', id: 'whmcs-audit' },
    { label: 'Clusters', icon: 'dns', id: 'clusters' },
    { label: 'Updates', icon: 'system_update', id: 'updates' },
    { label: 'Analytics', icon: 'query_stats', id: 'analytics' },
    { label: 'Monitoring', icon: 'monitoring', id: 'monitoring' },
];

const PATH_TO_PAGE = {
    '/': 'dashboard',
    '/shell': 'shell',
    '/domains': 'domains',
    '/email': 'email',
    '/files': 'files',
    '/backups': 'backups',
    '/security': 'security',
    '/docker': 'docker',
    '/licenses': 'licenses',
    '/plugins': 'plugins',
    '/containers': 'containers',
    '/whmcs-audit': 'whmcs-audit',
    '/clusters': 'clusters',
    '/updates': 'updates',
    '/analytics': 'analytics',
    '/monitoring': 'monitoring',
};

const PAGE_TO_PATH = Object.fromEntries(Object.entries(PATH_TO_PAGE).map(([path, page]) => [page, path]));

export default function DevPanelPage() {
    const router = useRouter();
    const pathname = usePathname();
    const [activePage, setActivePage] = useState('dashboard');
    const [stats, setStats] = useState(DEFAULT_STATS);
    const [loading, setLoading] = useState(true);
    const [authReady, setAuthReady] = useState(false);
    const [currentUser, setCurrentUser] = useState(null);
    const [software, setSoftware] = useState([]);
    const [pluginCatalog, setPluginCatalog] = useState([]);
    const [preflightReport, setPreflightReport] = useState(null);
    const [licenseRuntime, setLicenseRuntime] = useState(null);
    const [containerRuntime, setContainerRuntime] = useState(null);
    const [containerInventory, setContainerInventory] = useState([]);
    const [accountMenuOpen, setAccountMenuOpen] = useState(false);
    const accountMenuRef = useRef(null);
    const [notifOpen, setNotifOpen] = useState(false);
    const notifRef = useRef(null);
    const [alerts, setAlerts] = useState([]);
    const [alertsLoading, setAlertsLoading] = useState(false);

    useEffect(() => {
        const normalizedFromPath = PATH_TO_PAGE[pathname || '/'];
        const nextPage = normalizedFromPath || 'dashboard';
        if (nextPage !== activePage) {
            setActivePage(nextPage);
        }
    }, [pathname, activePage]);

    useEffect(() => {
        const closeMenu = (event) => {
            if (accountMenuRef.current && !accountMenuRef.current.contains(event.target)) {
                setAccountMenuOpen(false);
            }
            if (notifRef.current && !notifRef.current.contains(event.target)) {
                setNotifOpen(false);
            }
        };

        document.addEventListener('mousedown', closeMenu);
        return () => document.removeEventListener('mousedown', closeMenu);
    }, []);

    const loadAlerts = async (token) => {
        if (alertsLoading) return;
        setAlertsLoading(true);
        try {
            const t = token || getStoredToken();
            const res = await fetch('/devapi/api/monitoring/alerts', {
                headers: t ? { Authorization: `Bearer ${t}` } : {},
            });
            if (res.ok) {
                const data = await res.json();
                setAlerts(Array.isArray(data.alerts) ? data.alerts : []);
            }
        } catch (_) {}
        finally { setAlertsLoading(false); }
    };

    useEffect(() => {
        const bootstrap = async () => {
            try {
                const sessionRes = await fetch('/api/session/me', { cache: 'no-store' });
                if (!sessionRes.ok) {
                    clearStoredToken();
                    router.replace('/login');
                    return;
                }

                const me = await sessionRes.json();
                setCurrentUser(me);
                setAuthReady(true);

                let token = getStoredToken();
                if (!token) {
                    const tokenRes = await fetch('/api/session/token', { cache: 'no-store' });
                    if (tokenRes.ok) {
                        const tokenPayload = await tokenRes.json();
                        token = tokenPayload?.access_token || '';
                        if (token) {
                            try {
                                localStorage.setItem('hsdev_token', token);
                            } catch {
                                // ignore storage issues
                            }
                        }
                    }
                }

                if (!token) {
                    setLoading(false);
                    return;
                }

                const { res: meRes } = await requestWithFallback(`/api/auth/me`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!meRes.ok) {
                    throw new Error(`Session check failed (${meRes.status})`);
                }
            } catch (err) {
                console.error('Auth/bootstrap failed:', err);
                clearStoredToken();
                router.replace('/login');
                return;
            } finally {
                setLoading(false);
            }

            // Non-critical data loading should not block authenticated UI render.
            const token = getStoredToken();
            if (!token) {
                return;
            }
            const [statsResult, softwareResult, catalogResult, preflightResult, licenseRuntimeResult, containerStatusResult, containerListResult] = await Promise.allSettled([
                requestWithFallback(`/api/analytics/stats`, {
                    headers: { Authorization: `Bearer ${token}` },
                }).then(({ res }) => res),
                requestWithFallback(`/api/software/list`, {
                    headers: { Authorization: `Bearer ${token}` },
                }).then(({ res }) => res),
                requestWithFallback(`/api/plugins/catalog`, {
                    headers: { Authorization: `Bearer ${token}` },
                }).then(({ res }) => res),
                requestWithFallback(`/api/system/preflight`, {
                    headers: { Authorization: `Bearer ${token}` },
                }).then(({ res }) => res),
                requestWithFallback(`/api/system/license/runtime-status`, {
                    headers: { Authorization: `Bearer ${token}` },
                }).then(({ res }) => res),
                requestWithFallback(`/api/containers/status`, {
                    headers: { Authorization: `Bearer ${token}` },
                }).then(({ res }) => res),
                requestWithFallback(`/api/containers/list?include_all=true`, {
                    headers: { Authorization: `Bearer ${token}` },
                }).then(({ res }) => res),
            ]);

            if (statsResult.status === 'fulfilled' && statsResult.value.ok) {
                const data = await statsResult.value.json();
                setStats(data || DEFAULT_STATS);
            }

            if (softwareResult.status === 'fulfilled' && softwareResult.value.ok) {
                const softwareData = await softwareResult.value.json();
                setSoftware(Array.isArray(softwareData) ? softwareData : []);
            }

            if (catalogResult.status === 'fulfilled' && catalogResult.value.ok) {
                const catalogData = await catalogResult.value.json();
                setPluginCatalog(catalogData.plugins || []);
            }

            if (preflightResult.status === 'fulfilled' && preflightResult.value.ok) {
                const preflightData = await preflightResult.value.json();
                setPreflightReport(preflightData.report || null);
            }

            if (licenseRuntimeResult.status === 'fulfilled' && licenseRuntimeResult.value.ok) {
                const runtimeData = await licenseRuntimeResult.value.json();
                setLicenseRuntime(runtimeData.data || null);
            }

            if (containerStatusResult.status === 'fulfilled' && containerStatusResult.value.ok) {
                const statusData = await containerStatusResult.value.json();
                setContainerRuntime(statusData.data || null);
            }

            if (containerListResult.status === 'fulfilled' && containerListResult.value.ok) {
                const listData = await containerListResult.value.json();
                setContainerInventory(Array.isArray(listData.containers) ? listData.containers : []);
            }

            // Pre-fetch alerts for notification badge
            loadAlerts(token);
        };

        bootstrap();
    }, [router]);

    const handleLogout = () => {
        fetch('/api/session/logout', { method: 'POST' }).catch(() => {});
        clearStoredToken();
        router.replace('/login');
    };

    const handleNavChange = (nextPage) => {
        setActivePage(nextPage);
        setAccountMenuOpen(false);
        router.push(PAGE_TO_PATH[nextPage] || '/');
    };

    if (loading || !authReady) {
        return (
            <div className="min-h-screen bg-[#061529] text-slate-100 flex items-center justify-center px-6">
                <div className="glass rounded-2xl border border-border-dark/60 p-8 w-full max-w-md text-center">
                    <div className="mx-auto w-14 h-14 rounded-full border-2 border-primary/30 border-t-primary animate-spin"></div>
                    <h2 className="mt-6 text-xl font-bold">Preparing Developer Workspace</h2>
                    <p className="mt-2 text-sm text-slate-400">Authenticating session and loading control-plane telemetry...</p>
                    <div className="mt-6 grid grid-cols-3 gap-3">
                        <div className="h-2 rounded bg-slate-800/70 animate-pulse"></div>
                        <div className="h-2 rounded bg-slate-800/70 animate-pulse delay-150"></div>
                        <div className="h-2 rounded bg-slate-800/70 animate-pulse delay-300"></div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen md:h-screen overflow-hidden">
            {/* Sidebar */}
            <aside className="w-64 flex-shrink-0 bg-card-dark/50 border-r border-border-dark hidden lg:flex flex-col">
                <div className="p-6 flex items-center gap-3">
                    <div className="w-12 h-12 bg-primary/10 rounded-lg border border-primary/30 flex items-center justify-center shadow-lg shadow-primary/15">
                        <img
                            src="/branding/hostingsignal-logo.png"
                            alt="HostingSignal"
                            className="h-8 w-auto object-contain"
                        />
                    </div>
                    <h1 className="text-xl font-bold tracking-tight text-slate-100 uppercase">HS-Panel</h1>
                </div>

                <nav className="flex-1 px-4 mt-4 space-y-1 overflow-y-auto min-h-0">
                    {NAV_ITEMS.map(item => (
                        <a key={item.id}
                            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors cursor-pointer ${activePage === item.id
                                ? 'bg-primary/10 text-primary font-medium border border-primary/20 shadow-inner'
                                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50'
                                }`}
                            onClick={() => handleNavChange(item.id)}>
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
                <header className="h-16 flex items-center justify-between px-3 sm:px-4 lg:px-8 gap-2 bg-background-dark/80 backdrop-blur-md border-b border-border-dark sticky top-0 z-10">
                    <div className="flex items-center flex-1">
                        <div className="hidden sm:block relative w-full max-w-[17rem] md:max-w-[20rem] lg:max-w-[26rem]">
                            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xl">search</span>
                            <input type="text" placeholder="Search resources or logs..."
                                className="w-full bg-slate-800/50 border-none rounded-lg pl-10 pr-4 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:ring-1 focus:ring-primary outline-none" />
                        </div>
                    </div>
                    <div className="flex items-center gap-2 sm:gap-4">
                        <div className="relative" ref={notifRef}>
                            <button
                                onClick={() => { setNotifOpen(prev => !prev); if (!notifOpen) loadAlerts(); }}
                                className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-slate-800 transition-colors relative text-slate-400"
                                aria-label="Notifications"
                            >
                                <span className="material-symbols-outlined">notifications</span>
                                {alerts.length > 0 && (
                                    <span className="absolute top-1.5 right-1.5 min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full bg-red-500 text-white text-[10px] font-bold border border-background-dark leading-none">
                                        {alerts.length > 9 ? '9+' : alerts.length}
                                    </span>
                                )}
                                {alerts.length === 0 && (
                                    <span className="absolute top-2 right-2.5 w-2 h-2 bg-slate-600 rounded-full border border-background-dark"></span>
                                )}
                            </button>
                            {notifOpen && (
                                <div className="absolute right-0 mt-2 w-[92vw] sm:w-80 max-w-sm rounded-xl border border-border-dark bg-slate-900/95 shadow-2xl overflow-hidden z-50">
                                    <div className="px-4 py-3 border-b border-border-dark flex items-center justify-between">
                                        <p className="text-sm font-semibold text-slate-100">Notifications</p>
                                        <div className="flex items-center gap-2">
                                            {alerts.length > 0 && (
                                                <button onClick={() => setAlerts([])} className="text-xs text-slate-400 hover:text-slate-200">Dismiss all</button>
                                            )}
                                            <button onClick={() => loadAlerts()} className="text-xs text-primary hover:underline">Refresh</button>
                                        </div>
                                    </div>
                                    <div className="max-h-80 overflow-y-auto">
                                        {alertsLoading && (
                                            <div className="px-4 py-6 text-center text-slate-500 text-sm">Loading…</div>
                                        )}
                                        {!alertsLoading && alerts.length === 0 && (
                                            <div className="px-4 py-6 text-center">
                                                <span className="material-symbols-outlined text-slate-600 text-3xl">notifications_none</span>
                                                <p className="text-sm text-slate-500 mt-2">No active alerts</p>
                                            </div>
                                        )}
                                        {!alertsLoading && alerts.map((a, i) => (
                                            <div key={i} className={`px-4 py-3 border-b border-border-dark/40 last:border-0 flex items-start gap-3 ${a.severity === 'critical' ? 'bg-red-500/5' : 'bg-amber-500/5'}`}>
                                                <span className={`material-symbols-outlined text-[18px] mt-0.5 shrink-0 ${a.severity === 'critical' ? 'text-red-400' : 'text-amber-400'}`}>
                                                    {a.severity === 'critical' ? 'error' : 'warning'}
                                                </span>
                                                <div className="min-w-0">
                                                    <p className="text-sm text-slate-100 leading-snug">{a.message}</p>
                                                    <p className="text-xs text-slate-500 mt-1">{a.server} · {a.time ? new Date(a.time).toLocaleTimeString() : ''}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                        <div className="relative" ref={accountMenuRef}>
                            <button
                                onClick={() => setAccountMenuOpen((prev) => !prev)}
                                className="w-10 h-10 rounded-full bg-slate-700/80 border border-primary/30 flex items-center justify-center text-slate-200 font-bold hover:bg-slate-700"
                                aria-label="Account menu"
                            >
                                {(currentUser?.username || 'A').charAt(0).toUpperCase()}
                            </button>
                            {accountMenuOpen && (
                                <div className="absolute right-0 mt-2 w-[86vw] sm:w-52 max-w-xs rounded-xl border border-border-dark bg-slate-900/95 shadow-xl overflow-hidden">
                                    <div className="px-4 py-3 border-b border-border-dark">
                                        <p className="text-sm font-semibold text-slate-100">{currentUser?.username || 'Developer'}</p>
                                        <p className="text-xs text-slate-400">{currentUser?.role || 'admin'}</p>
                                    </div>
                                    <button
                                        onClick={handleLogout}
                                        className="w-full text-left px-4 py-3 text-sm text-slate-200 hover:bg-slate-800 transition-colors"
                                    >
                                        <span className="material-symbols-outlined align-middle mr-2 text-base">logout</span>
                                        Logout
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </header>

                <div className="lg:hidden border-b border-border-dark bg-slate-900/40 px-3 py-2 overflow-x-auto">
                    <div className="flex items-center gap-2 min-w-max">
                        {NAV_ITEMS.map((item) => (
                            <button
                                key={item.id}
                                onClick={() => handleNavChange(item.id)}
                                className={`px-3 py-2 rounded-lg text-xs font-semibold border transition-colors whitespace-nowrap ${activePage === item.id
                                    ? 'bg-primary/15 text-primary border-primary/30'
                                    : 'bg-slate-900/50 text-slate-300 border-slate-700 hover:bg-slate-800'
                                    }`}
                            >
                                {item.label}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-3 sm:p-4 lg:p-8">
                    {activePage === 'dashboard' && <DashboardView stats={stats} preflightReport={preflightReport} licenseRuntime={licenseRuntime} />}
                    {activePage === 'shell' && <ShellView />}
                    {activePage === 'domains' && <DomainsView />}
                    {activePage === 'email' && <EmailView />}
                    {activePage === 'files' && <FilesView />}
                    {activePage === 'backups' && <BackupsView />}
                    {activePage === 'security' && <SecurityView />}
                    {activePage === 'docker' && <DockerView runtimeState={containerRuntime} containers={containerInventory} />}
                    {activePage === 'licenses' && <LicensesView />}
                    {activePage === 'plugins' && <PluginsView plugins={pluginCatalog} />}
                    {activePage === 'containers' && <ContainersView runtimeState={containerRuntime} containers={containerInventory} />}
                    {activePage === 'whmcs-audit' && <WhmcsAuditView />}
                    {activePage === 'clusters' && <ClustersView />}
                    {activePage === 'updates' && <UpdatesView />}
                    {activePage === 'analytics' && <AnalyticsView />}
                    {activePage === 'monitoring' && <MonitoringView software={software} />}
                </div>
            </main>
        </div>
    );
}

function ShellView() {
    const [command, setCommand] = useState('');
    const [cwd, setCwd] = useState('');
    const [running, setRunning] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [history, setHistory] = useState([]);

    const runCommand = async () => {
        const trimmed = command.trim();
        if (!trimmed || running) return;

        setRunning(true);
        setError(null);
        try {
            const token = localStorage.getItem('hsdev_token');
            const res = await fetch('/devapi/api/shell/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    command: trimmed,
                    cwd: cwd.trim() || null,
                }),
            });

            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data?.detail || `HTTP ${res.status}`);
            }

            setResult(data);
            setHistory((prev) => [trimmed, ...prev.filter((x) => x !== trimmed)].slice(0, 12));
        } catch (err) {
            setError(err.message || 'Command execution failed');
        } finally {
            setRunning(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            runCommand();
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div>
                <h2 className="text-2xl font-bold text-slate-100">Server Shell</h2>
                <p className="text-slate-400 mt-1">Run server commands directly from the dashboard. Use with care.</p>
            </div>

            <div className="glass rounded-xl border border-border-dark/60 p-5 space-y-4">
                <div>
                    <label className="block text-xs uppercase tracking-wider text-slate-500 mb-2">Command</label>
                    <textarea
                        value={command}
                        onChange={(e) => setCommand(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Example: docker ps -a"
                        rows={4}
                        className="w-full bg-slate-900/70 border border-border-dark/80 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <p className="mt-2 text-xs text-slate-500">Tip: Press Ctrl+Enter to execute.</p>
                </div>

                <div>
                    <label className="block text-xs uppercase tracking-wider text-slate-500 mb-2">Working Directory (optional)</label>
                    <input
                        value={cwd}
                        onChange={(e) => setCwd(e.target.value)}
                        placeholder="Example: /usr/local/hspanel"
                        className="w-full bg-slate-900/70 border border-border-dark/80 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={runCommand}
                        disabled={running || !command.trim()}
                        className="px-4 py-2 bg-primary rounded-lg text-white text-sm font-bold hover:bg-primary/90 transition-colors disabled:opacity-50"
                    >
                        {running ? 'Running...' : 'Run Command'}
                    </button>
                    <button
                        onClick={() => { setResult(null); setError(null); }}
                        className="px-4 py-2 border border-slate-700 rounded-lg text-slate-300 text-sm font-semibold hover:bg-slate-800 transition-colors"
                    >
                        Clear Output
                    </button>
                </div>
            </div>

            {history.length > 0 && (
                <div className="glass rounded-xl border border-border-dark/60 p-4">
                    <p className="text-xs uppercase tracking-wider text-slate-500 mb-3">Recent Commands</p>
                    <div className="flex flex-wrap gap-2">
                        {history.map((item, idx) => (
                            <button
                                key={`${item}-${idx}`}
                                onClick={() => setCommand(item)}
                                className="px-3 py-1.5 text-xs rounded border border-slate-700 text-slate-300 hover:bg-slate-800 font-mono"
                            >
                                {item}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {(error || result) && (
                <div className="glass rounded-xl border border-border-dark/60 overflow-hidden">
                    <div className="px-4 py-3 border-b border-border-dark/60 flex items-center justify-between">
                        <p className="text-sm font-semibold text-slate-100">Execution Output</p>
                        {result && (
                            <span className={`px-2 py-1 rounded text-xs font-bold border ${result.success ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                exit {result.exit_code}
                            </span>
                        )}
                    </div>
                    <div className="p-4 space-y-3">
                        {error && <p className="text-sm text-red-400">{error}</p>}
                        {result && (
                            <>
                                <p className="text-xs text-slate-500">Executed in {result.duration_ms} ms {result.cwd ? `at ${result.cwd}` : ''}</p>
                                <pre className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 overflow-auto max-h-[420px] whitespace-pre-wrap font-mono">{result.stdout || ''}</pre>
                                {result.stderr && <pre className="bg-red-950/30 border border-red-900/40 rounded-lg p-3 text-xs text-red-300 overflow-auto max-h-[220px] whitespace-pre-wrap font-mono">{result.stderr}</pre>}
                            </>
                        )}
                    </div>
                </div>
            )}
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

function DashboardView({ stats, preflightReport, licenseRuntime }) {
    const recentActivity = stats?.recentActivity?.length ? stats.recentActivity : [
        { text: 'No recent events yet', time: 'just now', type: 'info' },
    ];
    const failedChecks = (preflightReport?.checks || []).filter((item) => !item.passed);

    const [fleetServers, setFleetServers] = useState([]);
    const [fleetLoading, setFleetLoading] = useState(true);

    useEffect(() => {
        const fetchFleet = async () => {
            setFleetLoading(true);
            try {
                const token = getStoredToken();
                const res = await fetch('/devapi/api/monitoring/servers', {
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                });
                if (res.ok) {
                    const data = await res.json();
                    setFleetServers(Array.isArray(data.servers) ? data.servers : []);
                }
            } catch (_) {}
            finally { setFleetLoading(false); }
        };
        fetchFleet();
    }, []);

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

            <div className="glass rounded-xl overflow-hidden border border-border-dark/60">
                <div className="px-6 py-4 border-b border-border-dark flex items-center justify-between gap-4 flex-wrap">
                    <div>
                        <h3 className="font-semibold text-slate-100">Launch Readiness</h3>
                        <p className="text-sm text-slate-400 mt-1">Preflight checks for secrets, database, WHMCS hardening, and operator setup.</p>
                    </div>
                    <div className={`px-3 py-1 rounded-full text-xs font-bold border ${preflightReport?.ready ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                        {preflightReport?.ready ? 'Ready to launch' : 'Launch blockers detected'}
                    </div>
                </div>
                <div className="p-6 space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="rounded-lg border border-border-dark/60 bg-slate-900/40 p-4">
                            <p className="text-xs uppercase tracking-wider text-slate-500">Environment</p>
                            <p className="mt-2 text-lg font-semibold text-slate-100">{preflightReport?.environment || 'unknown'}</p>
                        </div>
                        <div className="rounded-lg border border-border-dark/60 bg-slate-900/40 p-4">
                            <p className="text-xs uppercase tracking-wider text-slate-500">Critical Failures</p>
                            <p className="mt-2 text-lg font-semibold text-red-400">{preflightReport?.critical_failures ?? '-'}</p>
                        </div>
                        <div className="rounded-lg border border-border-dark/60 bg-slate-900/40 p-4">
                            <p className="text-xs uppercase tracking-wider text-slate-500">Warnings</p>
                            <p className="mt-2 text-lg font-semibold text-amber-400">{preflightReport?.warning_count ?? '-'}</p>
                        </div>
                    </div>

                    <div className="rounded-lg border border-border-dark/60 bg-slate-900/40 overflow-hidden">
                        <div className="px-4 py-3 border-b border-border-dark/60 flex items-center justify-between">
                            <p className="text-sm font-semibold text-slate-100">Current blockers and warnings</p>
                            <p className="text-xs text-slate-500">{failedChecks.length} open items</p>
                        </div>
                        <div className="divide-y divide-border-dark/50">
                            {failedChecks.length === 0 && (
                                <div className="px-4 py-4 text-sm text-green-400">No active launch blockers detected.</div>
                            )}
                            {failedChecks.map((item) => (
                                <div key={item.key} className="px-4 py-4 flex items-start justify-between gap-4">
                                    <div>
                                        <p className="text-sm font-semibold text-slate-100">{item.key}</p>
                                        <p className="text-sm text-slate-400 mt-1">{item.message}</p>
                                    </div>
                                    <span className={`px-2 py-1 rounded text-[11px] font-bold uppercase tracking-wider border ${item.severity === 'critical' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>
                                        {item.severity}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            <div className="glass rounded-xl overflow-hidden border border-border-dark/60">
                <div className="px-6 py-4 border-b border-border-dark flex items-center justify-between gap-4 flex-wrap">
                    <div>
                        <h3 className="font-semibold text-slate-100">Distributed License Runtime</h3>
                        <p className="text-sm text-slate-400 mt-1">Cache-first license state with outage grace handling.</p>
                    </div>
                    <div className={`px-3 py-1 rounded-full text-xs font-bold border ${(licenseRuntime?.valid || licenseRuntime?.status === 'grace') ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                        {licenseRuntime?.status || 'unknown'}
                    </div>
                </div>
                <div className="p-6 grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="rounded-lg border border-border-dark/60 bg-slate-900/40 p-4">
                        <p className="text-xs uppercase tracking-wider text-slate-500">Source</p>
                        <p className="mt-2 text-lg font-semibold text-slate-100">{licenseRuntime?.source || 'n/a'}</p>
                    </div>
                    <div className="rounded-lg border border-border-dark/60 bg-slate-900/40 p-4">
                        <p className="text-xs uppercase tracking-wider text-slate-500">License Key</p>
                        <p className="mt-2 text-sm font-semibold text-slate-100 break-all">{licenseRuntime?.license_key || 'not set'}</p>
                    </div>
                    <div className="rounded-lg border border-border-dark/60 bg-slate-900/40 p-4">
                        <p className="text-xs uppercase tracking-wider text-slate-500">Grace Deadline</p>
                        <p className="mt-2 text-sm font-semibold text-slate-100">{licenseRuntime?.grace_deadline || 'none'}</p>
                    </div>
                    <div className="rounded-lg border border-border-dark/60 bg-slate-900/40 p-4">
                        <p className="text-xs uppercase tracking-wider text-slate-500">Message</p>
                        <p className="mt-2 text-sm font-semibold text-slate-100">{licenseRuntime?.message || 'no runtime state yet'}</p>
                    </div>
                </div>
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
                        <span className="text-xs text-slate-500">{fleetLoading ? 'Loading…' : `${fleetServers.length} servers`}</span>
                    </div>
                    <div className="p-6 space-y-3">
                        {fleetLoading && (
                            <div className="text-center text-slate-500 text-sm py-4">Loading fleet data…</div>
                        )}
                        {!fleetLoading && fleetServers.length === 0 && (
                            <div className="text-center text-slate-500 text-sm py-4">No managed servers registered yet.</div>
                        )}
                        {!fleetLoading && fleetServers.map((s) => {
                            const online = s.status === 'online';
                            const degraded = s.status === 'degraded';
                            return (
                                <div key={s.id} className="flex justify-between items-center pb-3 border-b border-border-dark last:border-0 last:pb-0">
                                    <div className="min-w-0">
                                        <p className="text-sm font-medium text-slate-200 truncate">{s.hostname}</p>
                                        <p className="text-xs text-slate-500 font-mono">{s.ip}{s.region ? ` · ${s.region}` : ''}</p>
                                    </div>
                                    <div className="flex items-center gap-3 text-xs font-mono text-slate-400 shrink-0 ml-4">
                                        {s.cpu != null && <span>CPU {s.cpu.toFixed(0)}%</span>}
                                        <span className={`px-2 py-0.5 rounded border uppercase tracking-widest text-[10px] font-bold ${online ? 'bg-green-500/10 text-green-400 border-green-500/20' : degraded ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                            {s.status}
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}

function MetricTile({ label, value, tone = 'slate' }) {
    const toneClass = {
        slate: 'text-slate-100 border-border-dark/60',
        green: 'text-green-400 border-green-500/20',
        amber: 'text-amber-400 border-amber-500/20',
        red: 'text-red-400 border-red-500/20',
        primary: 'text-primary border-primary/20',
    };

    return (
        <div className={`glass rounded-xl border p-5 ${toneClass[tone] || toneClass.slate}`}>
            <p className="text-xs uppercase tracking-wider text-slate-500">{label}</p>
            <p className="mt-2 text-3xl font-bold">{value}</p>
        </div>
    );
}

function DomainsView() {
    const [domains, setDomains] = useState([]);
    const [loadingDomains, setLoadingDomains] = useState(true);
    const [domainsError, setDomainsError] = useState(null);

    const PANEL_TOKEN = typeof process !== 'undefined' ? (process.env.NEXT_PUBLIC_HSPANEL_API_TOKEN || '') : '';

    const fetchDomains = async () => {
        setLoadingDomains(true);
        setDomainsError(null);
        try {
            const headers = PANEL_TOKEN ? { 'X-Api-Token': PANEL_TOKEN } : {};
            const res = await fetch('/hspanel/api/domain/list', { headers });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            setDomains(Array.isArray(data?.data) ? data.data : []);
        } catch (err) {
            setDomainsError(err.message);
        } finally {
            setLoadingDomains(false);
        }
    };

    useEffect(() => { fetchDomains(); }, []);

    const configured = domains.filter(d => d.conf_exists).length;
    const atRisk = domains.filter(d => !d.conf_exists || !d.docroot_exists).length;

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end gap-4 flex-wrap">
                <div>
                    <h2 className="text-2xl font-bold text-slate-100">Domains</h2>
                    <p className="text-slate-400 mt-1">Virtual host inventory for hosted properties on this server.</p>
                </div>
                <button onClick={fetchDomains} className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 text-sm font-bold rounded-lg hover:bg-slate-700 transition-colors flex items-center gap-2">
                    <span className="material-symbols-outlined text-[18px]">refresh</span> Refresh
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricTile label="Total Vhosts" value={domains.length} tone="primary" />
                <MetricTile label="Conf Deployed" value={configured} tone="green" />
                <MetricTile label="At Risk" value={atRisk} tone={atRisk > 0 ? 'amber' : 'green'} />
            </div>

            <div className="glass rounded-xl overflow-hidden border border-border-dark/60">
                {loadingDomains ? (
                    <div className="p-8 text-center text-slate-400 text-sm animate-pulse">Loading domain inventory…</div>
                ) : domainsError ? (
                    <div className="p-8 text-center text-red-400 text-sm">
                        Failed to load: {domainsError}
                        <button onClick={fetchDomains} className="ml-3 text-primary underline">Retry</button>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse min-w-[640px]">
                            <thead className="bg-slate-800/30 border-b border-border-dark text-xs font-bold text-slate-400 uppercase tracking-widest">
                                <tr>
                                    <th className="px-6 py-4">Domain</th>
                                    <th className="px-6 py-4">Document Root</th>
                                    <th className="px-6 py-4">Conf</th>
                                    <th className="px-6 py-4">Docroot</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border-dark/50 text-sm">
                                {domains.length === 0 ? (
                                    <tr><td colSpan={4} className="px-6 py-10 text-center text-slate-500">No virtual hosts found on this server.</td></tr>
                                ) : domains.map((d) => (
                                    <tr key={d.domain} className="hover:bg-slate-800/20 transition-colors">
                                        <td className="px-6 py-4 font-semibold text-slate-100">{d.domain}</td>
                                        <td className="px-6 py-4 font-mono text-xs text-slate-400">{d.docroot || '—'}</td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 rounded text-xs font-bold border ${d.conf_exists ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                                {d.conf_exists ? 'active' : 'missing'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 rounded text-xs font-bold border ${d.docroot_exists ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>
                                                {d.docroot_exists ? 'exists' : 'absent'}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}

function EmailView() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('hsdev_token') : null;
    const apiToken = typeof window !== 'undefined' ? (process.env.NEXT_PUBLIC_HSPANEL_API_TOKEN || '') : '';
    const [mailboxes, setMailboxes] = useState([]);
    const [domains, setDomains] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showModal, setShowModal] = useState(false);
    const [form, setForm] = useState({ email: '', password: '', quota_mb: 500 });
    const [creating, setCreating] = useState(false);
    const [createMsg, setCreateMsg] = useState(null);

    const load = async () => {
        setLoading(true);
        setError(null);
        try {
            const headers = { 'X-API-Token': apiToken };
            const [mbRes, dmRes] = await Promise.all([
                fetch('/hspanel/api/mail/mailbox/list', { headers }),
                fetch('/hspanel/api/mail/domain/list', { headers }),
            ]);
            const [mbData, dmData] = await Promise.all([mbRes.json(), dmRes.json()]);
            setMailboxes(Array.isArray(mbData.data) ? mbData.data : []);
            setDomains(Array.isArray(dmData.data) ? dmData.data : []);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []);

    const createMailbox = async () => {
        if (!form.email.trim()) return;
        setCreating(true);
        setCreateMsg(null);
        try {
            const res = await fetch('/hspanel/api/mail/mailbox/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-API-Token': apiToken },
                body: JSON.stringify({ email: form.email.trim(), password: form.password || null, quota_mb: Number(form.quota_mb) }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Create failed');
            setCreateMsg({ ok: true, text: `Mailbox ${form.email} created.` });
            setForm({ email: '', password: '', quota_mb: 500 });
            await load();
        } catch (e) {
            setCreateMsg({ ok: false, text: e.message });
        } finally {
            setCreating(false);
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end gap-4 flex-wrap">
                <div>
                    <h2 className="text-2xl font-bold text-slate-100">Email Accounts</h2>
                    <p className="text-slate-400 mt-1">Mailbox provisioning for hosted mail domains.</p>
                </div>
                <button onClick={() => { setShowModal(true); setCreateMsg(null); }} className="px-4 py-2 bg-primary text-white text-sm font-bold rounded-lg hover:bg-primary/90 transition-colors">
                    + New Mailbox
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricTile label="Mailboxes" value={loading ? '…' : mailboxes.length} tone="primary" />
                <MetricTile label="Mail Domains" value={loading ? '…' : domains.length} tone="green" />
                <MetricTile label="Status" value={error ? 'Error' : loading ? '…' : 'Online'} tone={error ? 'red' : 'green'} />
            </div>

            {error && (
                <div className="glass rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">{error}</div>
            )}

            {domains.length > 0 && (
                <div className="glass rounded-xl border border-border-dark/60 p-6">
                    <h3 className="text-lg font-semibold text-slate-100 mb-4">Mail Domains</h3>
                    <div className="flex flex-wrap gap-2">
                        {domains.map((d) => (
                            <span key={d} className="px-3 py-1.5 rounded-lg border border-border-dark/60 bg-slate-800/40 text-sm text-slate-300 font-mono">{d}</span>
                        ))}
                    </div>
                </div>
            )}

            <div className="glass rounded-xl overflow-hidden border border-border-dark/60">
                <div className="px-6 py-4 border-b border-border-dark/60 flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-slate-100">Mailboxes</h3>
                    <button onClick={load} className="text-xs text-primary hover:underline">Refresh</button>
                </div>
                {loading ? (
                    <div className="p-8 text-center text-slate-500 text-sm">Loading mailboxes…</div>
                ) : mailboxes.length === 0 ? (
                    <div className="p-8 text-center text-slate-500 text-sm">No mailboxes found. Create one to get started.</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse min-w-[500px]">
                            <thead className="bg-slate-800/30 border-b border-border-dark text-xs font-bold text-slate-400 uppercase tracking-widest">
                                <tr>
                                    <th className="px-6 py-4">Email</th>
                                    <th className="px-6 py-4">Quota (MB)</th>
                                    <th className="px-6 py-4">Domain</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border-dark/50 text-sm">
                                {mailboxes.map((m, i) => (
                                    <tr key={m.email || i} className="hover:bg-slate-800/20 transition-colors">
                                        <td className="px-6 py-4 font-medium text-slate-100">{m.email || m}</td>
                                        <td className="px-6 py-4 text-slate-300">{m.quota_mb ?? '—'}</td>
                                        <td className="px-6 py-4 font-mono text-xs text-slate-400">{m.domain || (typeof m === 'string' ? m.split('@')[1] : '—')}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                    <div className="glass rounded-2xl border border-border-dark/60 p-8 w-full max-w-md space-y-5">
                        <h3 className="text-xl font-bold text-slate-100">Create Mailbox</h3>
                        <div className="space-y-3">
                            <div>
                                <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1">Email Address</label>
                                <input value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} placeholder="user@example.com" className="w-full bg-slate-800/60 border border-border-dark/60 rounded-lg px-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-primary" />
                            </div>
                            <div>
                                <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1">Password</label>
                                <input type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} placeholder="Leave blank to auto-generate" className="w-full bg-slate-800/60 border border-border-dark/60 rounded-lg px-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-primary" />
                            </div>
                            <div>
                                <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1">Quota (MB)</label>
                                <input type="number" min="10" max="51200" value={form.quota_mb} onChange={e => setForm(f => ({ ...f, quota_mb: e.target.value }))} className="w-full bg-slate-800/60 border border-border-dark/60 rounded-lg px-4 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-primary" />
                            </div>
                        </div>
                        {createMsg && (
                            <div className={`rounded-lg px-4 py-3 text-sm border ${createMsg.ok ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                {createMsg.text}
                            </div>
                        )}
                        <div className="flex gap-3 justify-end">
                            <button onClick={() => setShowModal(false)} className="px-4 py-2 rounded-lg border border-border-dark/60 text-sm text-slate-300 hover:bg-slate-800/40">Cancel</button>
                            <button onClick={createMailbox} disabled={creating || !form.email.trim()} className="px-5 py-2 bg-primary text-white text-sm font-bold rounded-lg hover:bg-primary/90 disabled:opacity-50">
                                {creating ? 'Creating…' : 'Create'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function FilesView() {
    const apiToken = typeof window !== 'undefined' ? (process.env.NEXT_PUBLIC_HSPANEL_API_TOKEN || '') : '';
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const load = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch('/hspanel/api/system/status', { headers: { 'X-API-Token': apiToken } });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Failed to load system status');
            setStatus(data.data || null);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []);

    const SERVICE_ICONS = { webserver: 'dns', database: 'storage', mail: 'mail', dns: 'travel_explore', ftp: 'folder_open' };
    const SERVICE_LABELS = { webserver: 'Web Server', database: 'Database', mail: 'Mail', dns: 'DNS', ftp: 'FTP' };

    const isActive = (svc) => {
        if (!svc) return false;
        if (typeof svc === 'boolean') return svc;
        if (typeof svc === 'string') return svc.toLowerCase().includes('active') || svc.toLowerCase().includes('running');
        if (typeof svc === 'object') return svc.active === true || String(svc.active || svc.status || '').toLowerCase().includes('active');
        return false;
    };

    const serviceEntries = status ? Object.entries(status) : [];
    const activeCount = serviceEntries.filter(([, v]) => isActive(v)).length;

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end gap-4 flex-wrap">
                <div>
                    <h2 className="text-2xl font-bold text-slate-100">Server Status</h2>
                    <p className="text-slate-400 mt-1">Live health of core panel services on this host.</p>
                </div>
                <button onClick={load} className="text-xs text-primary hover:underline">Refresh</button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricTile label="Services" value={loading ? '…' : serviceEntries.length} tone="primary" />
                <MetricTile label="Active" value={loading ? '…' : activeCount} tone="green" />
                <MetricTile label="Issues" value={loading || !status ? '…' : serviceEntries.length - activeCount} tone={(serviceEntries.length - activeCount) > 0 ? 'red' : 'green'} />
            </div>

            {error && (
                <div className="glass rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">{error}</div>
            )}

            {loading && !error && (
                <div className="glass rounded-xl border border-border-dark/60 p-8 text-center text-slate-500 text-sm">Loading service status…</div>
            )}

            {!loading && serviceEntries.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {serviceEntries.map(([key, val]) => {
                        const active = isActive(val);
                        const icon = SERVICE_ICONS[key] || 'settings';
                        const label = SERVICE_LABELS[key] || key;
                        const detail = val && typeof val === 'object' ? (val.output || val.version || null) : null;
                        return (
                            <div key={key} className="glass rounded-xl border border-border-dark/60 p-5">
                                <div className="flex items-center gap-3">
                                    <span className="material-symbols-outlined text-primary text-[22px]">{icon}</span>
                                    <div className="flex-1">
                                        <p className="text-slate-100 font-semibold">{label}</p>
                                        {detail && <p className="text-xs text-slate-500 mt-0.5 truncate">{detail}</p>}
                                    </div>
                                    <span className={`px-2 py-1 rounded text-xs font-bold border ${active ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                        {active ? 'active' : 'inactive'}
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {!loading && !error && serviceEntries.length === 0 && (
                <div className="glass rounded-xl border border-border-dark/60 p-8 text-center text-slate-500 text-sm">
                    No service data returned from the backend.
                </div>
            )}
        </div>
    );
}

function BackupsView() {
    const apiToken = typeof window !== 'undefined' ? (process.env.NEXT_PUBLIC_HSPANEL_API_TOKEN || '') : '';
    const [showModal, setShowModal] = useState(false);
    const [form, setForm] = useState({ username: '', backup_type: 'full' });
    const [enqueuing, setEnqueuing] = useState(false);
    const [enqueueResult, setEnqueueResult] = useState(null);
    const [history, setHistory] = useState([]);

    const enqueueBackup = async () => {
        if (!form.username.trim()) return;
        setEnqueuing(true);
        setEnqueueResult(null);
        try {
            const res = await fetch('/hspanel/api/backup/enqueue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-API-Token': apiToken },
                body: JSON.stringify({ username: form.username.trim(), backup_type: form.backup_type }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Enqueue failed');
            setEnqueueResult({ ok: true, text: `Backup job queued (ID: ${data.data?.id?.slice(0, 8)}…)` });
            setHistory(prev => [{ ...data.data, queued_at: new Date().toLocaleString() }, ...prev].slice(0, 10));
            setForm({ username: '', backup_type: 'full' });
        } catch (e) {
            setEnqueueResult({ ok: false, text: e.message });
        } finally {
            setEnqueuing(false);
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end gap-4 flex-wrap">
                <div>
                    <h2 className="text-2xl font-bold text-slate-100">Backups</h2>
                    <p className="text-slate-400 mt-1">Queue backup jobs and track recovery snapshots.</p>
                </div>
                <button onClick={() => { setShowModal(true); setEnqueueResult(null); }} className="px-4 py-2 bg-primary text-white text-sm font-bold rounded-lg hover:bg-primary/90 transition-colors">
                    + Create Snapshot
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricTile label="Jobs Queued (session)" value={history.length} tone="primary" />
                <MetricTile label="Full Backups" value={history.filter(h => h.backup_type === 'full').length} tone="green" />
                <MetricTile label="DB Backups" value={history.filter(h => h.backup_type === 'database').length} tone="amber" />
            </div>

            {history.length > 0 ? (
                <div className="glass rounded-xl overflow-hidden border border-border-dark/60">
                    <div className="px-6 py-4 border-b border-border-dark/60">
                        <h3 className="text-lg font-semibold text-slate-100">Queued This Session</h3>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse min-w-[600px]">
                            <thead className="bg-slate-800/30 border-b border-border-dark text-xs font-bold text-slate-400 uppercase tracking-widest">
                                <tr>
                                    <th className="px-6 py-4">Job ID</th>
                                    <th className="px-6 py-4">User</th>
                                    <th className="px-6 py-4">Type</th>
                                    <th className="px-6 py-4">Queued At</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border-dark/50 text-sm">
                                {history.map((h) => (
                                    <tr key={h.id} className="hover:bg-slate-800/20 transition-colors">
                                        <td className="px-6 py-4 font-mono text-xs text-slate-400">{h.id?.slice(0, 12)}…</td>
                                        <td className="px-6 py-4 font-semibold text-slate-100">{h.username}</td>
                                        <td className="px-6 py-4">
                                            <span className="px-2 py-1 rounded text-xs font-bold border bg-primary/10 text-primary border-primary/20">{h.backup_type}</span>
                                        </td>
                                        <td className="px-6 py-4 text-slate-300">{h.queued_at}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            ) : (
                <div className="glass rounded-xl border border-border-dark/60 p-8 text-center text-slate-500 text-sm">
                    No backup jobs queued this session. Click <span className="text-primary">+ Create Snapshot</span> to queue a backup job.
                </div>
            )}

            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                    <div className="glass rounded-2xl border border-border-dark/60 p-8 w-full max-w-md space-y-5">
                        <h3 className="text-xl font-bold text-slate-100">Create Snapshot</h3>
                        <div className="space-y-3">
                            <div>
                                <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1">cPanel Username</label>
                                <input value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} placeholder="alice" className="w-full bg-slate-800/60 border border-border-dark/60 rounded-lg px-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-primary" />
                            </div>
                            <div>
                                <label className="block text-xs uppercase tracking-wider text-slate-400 mb-1">Backup Type</label>
                                <select value={form.backup_type} onChange={e => setForm(f => ({ ...f, backup_type: e.target.value }))} className="w-full bg-slate-800/60 border border-border-dark/60 rounded-lg px-4 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-primary">
                                    <option value="full">Full</option>
                                    <option value="files">Files Only</option>
                                    <option value="database">Database Only</option>
                                </select>
                            </div>
                        </div>
                        {enqueueResult && (
                            <div className={`rounded-lg px-4 py-3 text-sm border ${enqueueResult.ok ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                {enqueueResult.text}
                            </div>
                        )}
                        <div className="flex gap-3 justify-end">
                            <button onClick={() => setShowModal(false)} className="px-4 py-2 rounded-lg border border-border-dark/60 text-sm text-slate-300 hover:bg-slate-800/40">Close</button>
                            <button onClick={enqueueBackup} disabled={enqueuing || !form.username.trim()} className="px-5 py-2 bg-primary text-white text-sm font-bold rounded-lg hover:bg-primary/90 disabled:opacity-50">
                                {enqueuing ? 'Queuing…' : 'Queue Backup'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function SecurityView() {
    const apiToken = typeof window !== 'undefined' ? (process.env.NEXT_PUBLIC_HSPANEL_API_TOKEN || '') : '';
    const [fwStatus, setFwStatus] = useState(null);
    const [modsecStatus, setModsecStatus] = useState(null);
    const [preflight, setPreflight] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [actionMsg, setActionMsg] = useState(null);
    const [acting, setActing] = useState(false);

    const load = async () => {
        setLoading(true);
        setError(null);
        try {
            const headers = { 'X-API-Token': apiToken };
            const [fwRes, msRes, pfRes] = await Promise.all([
                fetch('/hspanel/api/security/status', { headers }),
                fetch('/hspanel/api/security/modsec/status', { headers }),
                fetch('/devapi/api/system/preflight', {
                    headers: { Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('hsdev_token') : ''}` },
                }),
            ]);
            const [fwData, msData, pfData] = await Promise.all([fwRes.json(), msRes.json(), pfRes.json()]);
            setFwStatus(fwData.data || null);
            setModsecStatus(msData.data || null);
            setPreflight(pfData || null);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []);

    const csfAction = async (action) => {
        setActing(true);
        setActionMsg(null);
        try {
            const res = await fetch(`/hspanel/api/security/csf/${action}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-API-Token': apiToken },
                body: JSON.stringify({}),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || `CSF ${action} failed`);
            setActionMsg({ ok: true, text: data.message || `CSF ${action} succeeded` });
            await load();
        } catch (e) {
            setActionMsg({ ok: false, text: e.message });
        } finally {
            setActing(false);
        }
    };

    const csfActive = fwStatus?.csf?.active === true || String(fwStatus?.csf?.active ?? '').toLowerCase() === 'active';
    const pfChecks = Array.isArray(preflight?.checks) ? preflight.checks : [];
    const criticalFails = pfChecks.filter(c => !c.passed && c.severity === 'critical');

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end gap-4 flex-wrap">
                <div>
                    <h2 className="text-2xl font-bold text-slate-100">Security</h2>
                    <p className="text-slate-400 mt-1">Firewall, WAF, and launch readiness posture.</p>
                </div>
                <button onClick={load} className="text-xs text-primary hover:underline">Refresh</button>
            </div>

            {error && (
                <div className="glass rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">{error}</div>
            )}

            {actionMsg && (
                <div className={`glass rounded-xl border p-4 text-sm ${actionMsg.ok ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                    {actionMsg.text}
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricTile label="CSF Firewall" value={loading ? '…' : (csfActive ? 'Active' : 'Inactive')} tone={loading ? 'primary' : csfActive ? 'green' : 'red'} />
                <MetricTile label="ModSec Mode" value={loading ? '…' : (modsecStatus?.mode || 'Unknown')} tone="primary" />
                <MetricTile label="Critical Issues" value={loading ? '…' : criticalFails.length} tone={criticalFails.length > 0 ? 'red' : 'green'} />
            </div>

            {!loading && fwStatus && (
                <div className="glass rounded-xl border border-border-dark/60 p-6 space-y-4">
                    <div className="flex items-center justify-between">
                        <h3 className="text-lg font-semibold text-slate-100">CSF Firewall</h3>
                        <div className="flex gap-2">
                            <button onClick={() => csfAction('enable')} disabled={acting || csfActive} className="px-3 py-1.5 text-xs font-bold rounded-lg bg-green-500/10 text-green-400 border border-green-500/20 hover:bg-green-500/20 disabled:opacity-40">Enable</button>
                            <button onClick={() => csfAction('disable')} disabled={acting || !csfActive} className="px-3 py-1.5 text-xs font-bold rounded-lg bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 disabled:opacity-40">Disable</button>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        {Object.entries(fwStatus).map(([svc, state]) => (
                            <div key={svc} className="rounded-lg border border-border-dark/60 bg-slate-900/40 px-4 py-3 flex items-center justify-between">
                                <span className="text-sm font-medium text-slate-200 uppercase tracking-wider">{svc}</span>
                                <span className={`px-2 py-1 rounded text-xs font-bold border ${(state?.active === true || String(state?.active || state || '').toLowerCase().includes('active')) ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                    {String(state?.active ?? state?.status ?? state ?? 'unknown')}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {!loading && modsecStatus && (
                <div className="glass rounded-xl border border-border-dark/60 p-6">
                    <h3 className="text-lg font-semibold text-slate-100 mb-3">ModSecurity</h3>
                    <div className="flex items-center gap-4">
                        <span className="material-symbols-outlined text-primary text-[22px]">shield</span>
                        <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wider">Rule Engine Mode</p>
                            <p className="text-sm font-semibold text-slate-100 mt-0.5">{modsecStatus.mode || 'Unknown'}</p>
                        </div>
                        <span className={`ml-auto px-2 py-1 rounded text-xs font-bold border ${modsecStatus.mode === 'On' ? 'bg-green-500/10 text-green-400 border-green-500/20' : modsecStatus.mode === 'DetectionOnly' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                            {modsecStatus.mode === 'On' ? 'enforcing' : modsecStatus.mode === 'DetectionOnly' ? 'detection only' : 'off'}
                        </span>
                    </div>
                </div>
            )}

            {!loading && pfChecks.length > 0 && (
                <div className="glass rounded-xl border border-border-dark/60 p-6">
                    <h3 className="text-lg font-semibold text-slate-100 mb-4">Launch Readiness Checks</h3>
                    <div className="space-y-2">
                        {pfChecks.filter(c => !c.passed).map((c) => (
                            <div key={c.key} className={`rounded-lg border px-4 py-3 text-sm flex items-start gap-3 ${c.severity === 'critical' ? 'bg-red-500/10 border-red-500/20 text-red-300' : 'bg-amber-500/10 border-amber-500/20 text-amber-300'}`}>
                                <span className="material-symbols-outlined text-[18px] mt-0.5">{c.severity === 'critical' ? 'error' : 'warning'}</span>
                                <span>{c.message}</span>
                            </div>
                        ))}
                        {pfChecks.every(c => c.passed) && (
                            <div className="rounded-lg border border-green-500/20 bg-green-500/10 px-4 py-3 text-sm text-green-400 flex items-center gap-2">
                                <span className="material-symbols-outlined text-[18px]">check_circle</span>
                                All preflight checks passed — system is launch-ready.
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

function DockerView({ runtimeState, containers }) {
    const runtime = runtimeState?.engine || runtimeState?.runtime || null;
    const list = Array.isArray(containers) ? containers : [];
    const running = list.filter(c => (c.status || '').toLowerCase().includes('running') || (c.state || '').toLowerCase() === 'running').length;
    const stopped = list.length - running;

    const STATUS_COLORS = {
        running: 'bg-green-500/10 text-green-400 border-green-500/20',
        exited: 'bg-red-500/10 text-red-400 border-red-500/20',
        paused: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
        restarting: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    };
    const stateColor = (c) => {
        const s = (c.status || c.state || '').toLowerCase();
        if (s.includes('running')) return STATUS_COLORS.running;
        if (s.includes('exit')) return STATUS_COLORS.exited;
        if (s.includes('pause')) return STATUS_COLORS.paused;
        if (s.includes('restart')) return STATUS_COLORS.restarting;
        return 'bg-slate-700/30 text-slate-400 border-slate-600/30';
    };
    const stateLabel = (c) => c.state || (c.status || 'unknown').split(' ')[0];

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div>
                <h2 className="text-2xl font-bold text-slate-100">Docker Management</h2>
                <p className="text-slate-400 mt-1">Runtime state and workload visibility for containerized services.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricTile label="Total Containers" value={list.length} tone="primary" />
                <MetricTile label="Running" value={running} tone="green" />
                <MetricTile label="Stopped / Exited" value={stopped} tone={stopped > 0 ? 'red' : 'green'} />
            </div>

            {runtime && (
                <div className="glass rounded-xl border border-border-dark/60 p-4 flex items-center gap-3">
                    <span className="material-symbols-outlined text-primary text-[22px]">settings</span>
                    <div>
                        <p className="text-xs text-slate-500 uppercase tracking-wider">Runtime Engine</p>
                        <p className="text-sm font-semibold text-slate-100 mt-0.5">{runtime}</p>
                    </div>
                </div>
            )}

            {list.length === 0 ? (
                <div className="glass rounded-xl border border-border-dark/60 p-8 text-center text-slate-500 text-sm">
                    No container data available. The Docker runtime may be offline or the container runner module is not loaded.
                </div>
            ) : (
                <div className="glass rounded-xl overflow-hidden border border-border-dark/60">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse min-w-[680px]">
                            <thead className="bg-slate-800/30 border-b border-border-dark text-xs font-bold text-slate-400 uppercase tracking-widest">
                                <tr>
                                    <th className="px-6 py-4">Name</th>
                                    <th className="px-6 py-4">Image</th>
                                    <th className="px-6 py-4">Status</th>
                                    <th className="px-6 py-4">Ports</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border-dark/50 text-sm">
                                {list.map((c, i) => (
                                    <tr key={c.id || c.name || i} className="hover:bg-slate-800/20 transition-colors">
                                        <td className="px-6 py-4 font-semibold text-slate-100">{c.name || c.Names || '—'}</td>
                                        <td className="px-6 py-4 font-mono text-xs text-slate-400">{c.image || c.Image || '—'}</td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 rounded text-xs font-bold border capitalize ${stateColor(c)}`}>
                                                {stateLabel(c)}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 font-mono text-xs text-slate-400">{c.ports || c.Ports || '—'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}

function LicensesView() {
    const [licenses, setLicenses] = useState([]);
    const [loadingList, setLoadingList] = useState(true);
    const [listError, setListError] = useState(null);
    const [showModal, setShowModal] = useState(false);
    const [form, setForm] = useState({ customer_email: '', tier: 'professional', domain_binding: '', valid_days: 365, ip_binding: '', max_domains: 20 });
    const [submitting, setSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState(null);
    const [newKey, setNewKey] = useState(null);

    const fetchLicenses = async () => {
        setLoadingList(true);
        setListError(null);
        try {
            const token = localStorage.getItem('hsdev_token');
            const res = await fetch('/devapi/api/licenses/list', {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            const rows = data?.data?.licenses || [];
            setLicenses(rows);
        } catch (err) {
            setListError(err.message);
        } finally {
            setLoadingList(false);
        }
    };

    useEffect(() => { fetchLicenses(); }, []);

    const handleGenerate = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        setSubmitError(null);
        setNewKey(null);
        try {
            const token = localStorage.getItem('hsdev_token');
            const res = await fetch('/devapi/api/licenses/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({
                    customer_email: form.customer_email,
                    tier: form.tier,
                    domain_binding: form.domain_binding || undefined,
                    ip_binding: form.ip_binding || undefined,
                    valid_days: Number(form.valid_days),
                    max_domains: Number(form.max_domains),
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
            setNewKey(data?.data?.license_key || data?.license_key || 'Generated successfully');
            fetchLicenses();
        } catch (err) {
            setSubmitError(err.message);
        } finally {
            setSubmitting(false);
        }
    };

    const handleRevoke = async (key) => {
        if (!confirm(`Revoke license ${key}?`)) return;
        try {
            const token = localStorage.getItem('hsdev_token');
            const res = await fetch(`/devapi/api/licenses/${encodeURIComponent(key)}/revoke`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            fetchLicenses();
        } catch (err) {
            alert(`Revoke failed: ${err.message}`);
        }
    };

    const activeCount = licenses.filter((l) => l.status === 'active').length;
    const expiredCount = licenses.filter((l) => l.status === 'expired').length;
    const enterpriseCount = licenses.filter((l) => (l.tier || '').toLowerCase() === 'enterprise').length;

    const TIERS = ['starter', 'professional', 'business', 'enterprise'];
    const STATUS_COLORS = {
        active: 'bg-green-500/10 text-green-400 border-green-500/20',
        expired: 'bg-red-500/10 text-red-400 border-red-500/20',
        revoked: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
        suspended: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    };

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-2xl font-bold text-slate-100">License Management</h2>
                    <p className="text-slate-400 mt-1">Manage software licenses issued to clients.</p>
                </div>
                <button onClick={() => { setShowModal(true); setNewKey(null); setSubmitError(null); }}
                    className="px-4 py-2 bg-primary text-white text-sm font-bold rounded-lg hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20 flex items-center gap-2">
                    <span className="material-symbols-outlined text-[20px]">add</span> Generate License
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricTile label="Total Licenses" value={licenses.length} tone="primary" />
                <MetricTile label="Active" value={activeCount} tone="green" />
                <MetricTile label="Expired / Revoked" value={licenses.length - activeCount} tone="red" />
            </div>

            <div className="glass rounded-xl border border-border-dark/60 p-4">
                <p className="text-sm text-slate-300">Enterprise subscriptions: <span className="text-slate-100 font-semibold">{enterpriseCount}</span></p>
            </div>

            <div className="glass rounded-xl overflow-hidden">
                {loadingList ? (
                    <div className="p-8 text-center text-slate-400 text-sm animate-pulse">Loading licenses…</div>
                ) : listError ? (
                    <div className="p-8 text-center text-red-400 text-sm">
                        Failed to load licenses: {listError}
                        <button onClick={fetchLicenses} className="ml-3 text-primary underline">Retry</button>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse min-w-[760px]">
                            <thead className="bg-slate-800/30 border-b border-border-dark text-xs font-bold text-slate-400 uppercase tracking-widest">
                                <tr>
                                    <th className="px-6 py-4">License Key</th>
                                    <th className="px-6 py-4">Tier</th>
                                    <th className="px-6 py-4">Customer</th>
                                    <th className="px-6 py-4">Domain</th>
                                    <th className="px-6 py-4">Status</th>
                                    <th className="px-6 py-4">Expires</th>
                                    <th className="px-6 py-4 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border-dark/50 text-sm">
                                {licenses.length === 0 ? (
                                    <tr><td colSpan={7} className="px-6 py-10 text-center text-slate-500">No licenses found. Generate the first one.</td></tr>
                                ) : licenses.map(l => (
                                    <tr key={l.license_key || l.key} className="hover:bg-slate-800/20 transition-colors">
                                        <td className="px-6 py-4 font-mono font-bold text-primary text-xs">{l.license_key || l.key}</td>
                                        <td className="px-6 py-4"><span className="px-2 py-1 rounded bg-purple-500/10 text-purple-400 text-xs font-bold border border-purple-500/20 capitalize">{l.tier}</span></td>
                                        <td className="px-6 py-4 text-slate-300 text-xs">{l.customer_email || '—'}</td>
                                        <td className="px-6 py-4 font-medium text-slate-300">{l.bound_domain || l.domain || '—'}</td>
                                        <td className="px-6 py-4"><span className={`px-2 py-1 rounded text-xs font-bold border capitalize ${STATUS_COLORS[l.status] || 'bg-slate-700/30 text-slate-400 border-slate-600/30'}`}>{l.status}</span></td>
                                        <td className="px-6 py-4 text-slate-400 text-xs">{l.expires_at ? new Date(l.expires_at).toLocaleDateString() : 'Never'}</td>
                                        <td className="px-6 py-4 text-right space-x-2">
                                            {l.status === 'active' && (
                                                <button onClick={() => handleRevoke(l.license_key || l.key)}
                                                    className="px-3 py-1.5 bg-red-900/30 border border-red-700/40 rounded text-xs hover:bg-red-900/50 text-red-400 transition-colors">
                                                    Revoke
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Generate License Modal */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
                    <div className="glass rounded-2xl border border-border-dark/60 w-full max-w-md p-6 space-y-5 shadow-2xl">
                        <div className="flex justify-between items-center">
                            <h3 className="text-lg font-bold text-slate-100">Generate New License</h3>
                            <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-200 transition-colors">
                                <span className="material-symbols-outlined text-[22px]">close</span>
                            </button>
                        </div>

                        {newKey ? (
                            <div className="space-y-4">
                                <p className="text-sm text-green-400 font-medium">License generated successfully!</p>
                                <div className="bg-slate-900 border border-border-dark rounded-lg p-3 font-mono text-primary text-sm break-all select-all">{newKey}</div>
                                <p className="text-xs text-slate-500">Copy and save this key — it won&apos;t be shown again.</p>
                                <div className="flex gap-3 justify-end">
                                    <button onClick={() => navigator.clipboard?.writeText(newKey)}
                                        className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 hover:bg-slate-700 transition-colors">
                                        Copy Key
                                    </button>
                                    <button onClick={() => { setShowModal(false); setNewKey(null); setForm({ customer_email: '', tier: 'professional', domain_binding: '', valid_days: 365, ip_binding: '', max_domains: 20 }); }}
                                        className="px-4 py-2 bg-primary rounded-lg text-sm text-white font-bold hover:bg-primary/90 transition-colors">
                                        Done
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <form onSubmit={handleGenerate} className="space-y-4">
                                <div>
                                    <label className="block text-xs text-slate-400 mb-1">Customer Email <span className="text-red-400">*</span></label>
                                    <input type="email" required value={form.customer_email}
                                        onChange={e => setForm(f => ({ ...f, customer_email: e.target.value }))}
                                        className="w-full bg-slate-900 border border-border-dark rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary/60 focus:ring-1 focus:ring-primary/30"
                                        placeholder="client@example.com" />
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <label className="block text-xs text-slate-400 mb-1">Tier</label>
                                        <select value={form.tier} onChange={e => setForm(f => ({ ...f, tier: e.target.value }))}
                                            className="w-full bg-slate-900 border border-border-dark rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-primary/60 capitalize">
                                            {TIERS.map(t => <option key={t} value={t} className="capitalize">{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-xs text-slate-400 mb-1">Valid Days</label>
                                        <input type="number" min={1} max={3650} value={form.valid_days}
                                            onChange={e => setForm(f => ({ ...f, valid_days: e.target.value }))}
                                            className="w-full bg-slate-900 border border-border-dark rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-primary/60" />
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-xs text-slate-400 mb-1">Bound Domain <span className="text-slate-600">(optional)</span></label>
                                    <input type="text" value={form.domain_binding}
                                        onChange={e => setForm(f => ({ ...f, domain_binding: e.target.value }))}
                                        className="w-full bg-slate-900 border border-border-dark rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary/60"
                                        placeholder="example.com" />
                                </div>
                                <div>
                                    <label className="block text-xs text-slate-400 mb-1">Bound IP <span className="text-slate-600">(optional)</span></label>
                                    <input type="text" value={form.ip_binding}
                                        onChange={e => setForm(f => ({ ...f, ip_binding: e.target.value }))}
                                        className="w-full bg-slate-900 border border-border-dark rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-primary/60"
                                        placeholder="192.168.1.1" />
                                </div>
                                {submitError && <p className="text-xs text-red-400 bg-red-900/20 border border-red-700/30 rounded px-3 py-2">{submitError}</p>}
                                <div className="flex gap-3 justify-end pt-1">
                                    <button type="button" onClick={() => setShowModal(false)}
                                        className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 hover:bg-slate-700 transition-colors">
                                        Cancel
                                    </button>
                                    <button type="submit" disabled={submitting}
                                        className="px-4 py-2 bg-primary rounded-lg text-sm text-white font-bold hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
                                        {submitting ? <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span> Generating…</> : 'Generate'}
                                    </button>
                                </div>
                            </form>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

function PluginsView({ plugins }) {
    const [selectedPlan, setSelectedPlan] = useState('starter');
    const [selectedPlugins, setSelectedPlugins] = useState([]);
    const [adminOverride, setAdminOverride] = useState(false);
    const [packagePreview, setPackagePreview] = useState(null);
    const [submitting, setSubmitting] = useState(false);

    const togglePlugin = (slug) => {
        setSelectedPlugins(prev => prev.includes(slug) ? prev.filter(s => s !== slug) : [...prev, slug]);
    };

    const buildPackage = async () => {
        setSubmitting(true);
        try {
            const token = localStorage.getItem('hsdev_token');
            const res = await fetch(`${API_BASE}/api/plugins/packages/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    package_name: `custom-${selectedPlan}-package`,
                    plan: selectedPlan,
                    include_plugins: selectedPlugins,
                    admin_override: adminOverride,
                }),
            });
            const data = await res.json();
            setPackagePreview(data.package || null);
        } catch (err) {
            console.error('Package preview failed', err);
            setPackagePreview(null);
        } finally {
            setSubmitting(false);
        }
    };

    const totalPlugins = (plugins || []).length;
    const selectedCount = selectedPlugins.length;

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-2xl font-bold text-slate-100">Plugin Marketplace</h2>
                    <p className="text-slate-400 mt-1">Built-in premium plugins with plan gating and admin override.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricTile label="Catalog Plugins" value={totalPlugins} tone="primary" />
                <MetricTile label="Selected" value={selectedCount} tone="green" />
                <MetricTile label="Plan" value={selectedPlan} tone="amber" />
            </div>

            <div className="glass rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse min-w-[760px]">
                        <thead className="bg-slate-800/30 border-b border-border-dark text-xs font-bold text-slate-400 uppercase tracking-widest">
                            <tr>
                                <th className="px-6 py-4">Plugin</th>
                                <th className="px-6 py-4">Category</th>
                                <th className="px-6 py-4">Required Plan</th>
                                <th className="px-6 py-4">Select</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border-dark/50 text-sm">
                            {(plugins || []).map((p) => (
                                <tr key={p.slug} className="hover:bg-slate-800/20 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="font-semibold text-slate-100">{p.name}</div>
                                        <div className="text-xs text-slate-400 mt-1">{p.description}</div>
                                    </td>
                                    <td className="px-6 py-4 text-slate-300 uppercase text-xs">{p.category}</td>
                                    <td className="px-6 py-4"><span className="px-2 py-1 rounded bg-primary/10 text-primary text-xs font-bold border border-primary/20">{p.required_plan}</span></td>
                                    <td className="px-6 py-4">
                                        <input
                                            type="checkbox"
                                            checked={selectedPlugins.includes(p.slug)}
                                            onChange={() => togglePlugin(p.slug)}
                                            className="w-4 h-4"
                                        />
                                    </td>
                                </tr>
                            ))}
                            {totalPlugins === 0 && (
                                <tr>
                                    <td className="px-6 py-6 text-slate-400" colSpan={4}>No plugins available from catalog.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <div className="glass rounded-xl p-6 space-y-4">
                <h3 className="text-lg font-semibold text-slate-100">Package Builder</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                    <div>
                        <label className="text-xs uppercase text-slate-400 tracking-wider">Plan</label>
                        <select
                            value={selectedPlan}
                            onChange={(e) => setSelectedPlan(e.target.value)}
                            className="w-full mt-2 bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                        >
                            <option value="starter">starter</option>
                            <option value="professional">professional</option>
                            <option value="business">business</option>
                            <option value="enterprise">enterprise</option>
                        </select>
                    </div>

                    <label className="flex items-center gap-2 text-slate-300 text-sm">
                        <input
                            type="checkbox"
                            checked={adminOverride}
                            onChange={(e) => setAdminOverride(e.target.checked)}
                            className="w-4 h-4"
                        />
                        Allow admin override for lower plan
                    </label>

                    <button
                        onClick={buildPackage}
                        disabled={submitting}
                        className="px-4 py-2 bg-primary text-white text-sm font-bold rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
                    >
                        {submitting ? 'Evaluating...' : 'Evaluate Package'}
                    </button>
                </div>

                {packagePreview && (
                    <div className="mt-4 rounded-lg border border-border-dark p-4 bg-slate-900/40">
                        <p className="text-slate-100 font-semibold">Enabled Plugins: {packagePreview.enabled_plugins.length}</p>
                        <ul className="mt-2 space-y-1 text-sm text-slate-300">
                            {packagePreview.enabled_plugins.map((p) => (
                                <li key={p.slug}>• {p.name} {p.override_used ? '(override)' : ''}</li>
                            ))}
                        </ul>
                        {packagePreview.blocked_plugins.length > 0 && (
                            <div className="mt-3">
                                <p className="text-red-400 text-sm font-semibold">Blocked Plugins</p>
                                <ul className="mt-1 space-y-1 text-sm text-slate-300">
                                    {packagePreview.blocked_plugins.map((p) => (
                                        <li key={p.slug}>• {p.name} - {p.reason}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

function WhmcsAuditView() {
    const [entries, setEntries] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [actionFilter, setActionFilter] = useState('');
    const [successFilter, setSuccessFilter] = useState('all');
    const [pageSize, setPageSize] = useState(25);
    const [offset, setOffset] = useState(0);
    const [total, setTotal] = useState(0);
    const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(false);
    const [autoRefreshSeconds, setAutoRefreshSeconds] = useState(10);
    const [lastLoadedAt, setLastLoadedAt] = useState('');

    const loadAudit = async (nextOffset = offset) => {
        setLoading(true);
        setError('');
        try {
            const token = localStorage.getItem('hsdev_token');
            if (!token) {
                throw new Error('Missing session token');
            }

            const params = new URLSearchParams({ limit: String(pageSize), offset: String(nextOffset) });
            if (actionFilter.trim()) {
                params.set('action', actionFilter.trim());
            }
            if (successFilter !== 'all') {
                params.set('success', successFilter === 'true' ? 'true' : 'false');
            }

            const { res } = await requestWithFallback(`/api/whmcs/audit/recent?${params.toString()}`, {
                headers: { Authorization: `Bearer ${token}` },
            });

            if (!res.ok) {
                const payload = await res.json().catch(() => ({}));
                throw new Error(payload.detail || `Failed with HTTP ${res.status}`);
            }

            const payload = await res.json();
            setEntries(Array.isArray(payload.entries) ? payload.entries : []);
            setOffset(Number(payload.offset || 0));
            setTotal(Number(payload.total || 0));
            setLastLoadedAt(new Date().toLocaleString());
        } catch (err) {
            setError(err.message || 'Unable to load WHMCS audit events');
        } finally {
            setLoading(false);
        }
    };

    const applyFilters = () => {
        loadAudit(0);
    };

    const toCsv = (items) => {
        const header = ['timestamp', 'action', 'success', 'details'];
        const escapeCell = (value) => {
            const text = String(value ?? '');
            return `"${text.replace(/"/g, '""')}"`;
        };
        const rows = items.map((entry) => [
            entry.timestamp || '',
            entry.action || '',
            entry.success ? 'true' : 'false',
            JSON.stringify(entry.details || {}),
        ]);
        return [header, ...rows].map((row) => row.map(escapeCell).join(',')).join('\n');
    };

    const downloadBlob = (content, fileName, mimeType) => {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    };

    const exportJson = () => {
        downloadBlob(JSON.stringify(entries, null, 2), `whmcs-audit-${Date.now()}.json`, 'application/json');
    };

    const exportCsv = () => {
        downloadBlob(toCsv(entries), `whmcs-audit-${Date.now()}.csv`, 'text/csv;charset=utf-8');
    };

    useEffect(() => {
        loadAudit(0);
    }, []);

    useEffect(() => {
        if (!autoRefreshEnabled) {
            return;
        }
        const intervalMs = Math.max(5, Number(autoRefreshSeconds) || 10) * 1000;
        const timer = setInterval(() => {
            loadAudit(offset);
        }, intervalMs);
        return () => clearInterval(timer);
    }, [autoRefreshEnabled, autoRefreshSeconds, offset, pageSize, actionFilter, successFilter]);

    const pageStart = total === 0 ? 0 : offset + 1;
    const pageEnd = Math.min(offset + entries.length, total);
    const canPrev = offset > 0;
    const canNext = (offset + entries.length) < total;

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end gap-4 flex-wrap">
                <div>
                    <h2 className="text-2xl font-bold text-slate-100">WHMCS Audit Trail</h2>
                    <p className="text-slate-400 mt-1">Provisioning and mapping security events from the developer API.</p>
                </div>
                <button
                    onClick={() => loadAudit(offset)}
                    disabled={loading}
                    className="px-4 py-2 bg-primary text-white text-sm font-bold rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                    {loading ? 'Refreshing...' : 'Refresh Audit'}
                </button>
            </div>

            <div className="glass rounded-xl p-5 border border-border-dark/60">
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                    <div>
                        <label className="text-xs uppercase text-slate-400 tracking-wider">Action Filter</label>
                        <input
                            value={actionFilter}
                            onChange={(e) => setActionFilter(e.target.value)}
                            placeholder="e.g. provision_create_account"
                            className="w-full mt-2 bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                        />
                    </div>
                    <div>
                        <label className="text-xs uppercase text-slate-400 tracking-wider">Result Filter</label>
                        <select
                            value={successFilter}
                            onChange={(e) => setSuccessFilter(e.target.value)}
                            className="w-full mt-2 bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                        >
                            <option value="all">all</option>
                            <option value="true">success</option>
                            <option value="false">failed</option>
                        </select>
                    </div>
                    <div>
                        <label className="text-xs uppercase text-slate-400 tracking-wider">Page Size</label>
                        <select
                            value={pageSize}
                            onChange={(e) => setPageSize(Number(e.target.value) || 25)}
                            className="w-full mt-2 bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                        >
                            <option value="10">10</option>
                            <option value="25">25</option>
                            <option value="50">50</option>
                            <option value="100">100</option>
                        </select>
                    </div>
                    <div>
                        <label className="text-xs uppercase text-slate-400 tracking-wider">Auto Refresh</label>
                        <div className="mt-2 flex items-center gap-3">
                            <label className="flex items-center gap-2 text-slate-300 text-sm">
                                <input
                                    type="checkbox"
                                    checked={autoRefreshEnabled}
                                    onChange={(e) => setAutoRefreshEnabled(e.target.checked)}
                                    className="w-4 h-4"
                                />
                                Enable
                            </label>
                            <select
                                value={autoRefreshSeconds}
                                onChange={(e) => setAutoRefreshSeconds(Number(e.target.value) || 10)}
                                className="bg-slate-800/60 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 text-sm"
                                disabled={!autoRefreshEnabled}
                            >
                                <option value="5">5s</option>
                                <option value="10">10s</option>
                                <option value="15">15s</option>
                                <option value="30">30s</option>
                            </select>
                        </div>
                    </div>
                    <div className="flex items-end">
                        <button
                            onClick={applyFilters}
                            disabled={loading}
                            className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-slate-100 text-sm font-semibold rounded-lg hover:bg-slate-700 disabled:opacity-50 transition-colors"
                        >
                            Apply Filters
                        </button>
                    </div>
                </div>
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                    <p className="text-xs text-slate-500">Last loaded: {lastLoadedAt || 'not loaded yet'}</p>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={exportCsv}
                            disabled={entries.length === 0}
                            className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-xs text-slate-200 hover:bg-slate-700 disabled:opacity-40"
                        >
                            Export CSV
                        </button>
                        <button
                            onClick={exportJson}
                            disabled={entries.length === 0}
                            className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-xs text-slate-200 hover:bg-slate-700 disabled:opacity-40"
                        >
                            Export JSON
                        </button>
                    </div>
                </div>
            </div>

            {error && (
                <div className="rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 px-4 py-3 text-sm">
                    {error}
                </div>
            )}

            <div className="glass rounded-xl overflow-hidden border border-border-dark/60">
                <div className="px-6 py-3 border-b border-border-dark/60 flex items-center justify-between text-xs text-slate-400">
                    <span>Showing {pageStart}-{pageEnd} of {total}</span>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => loadAudit(Math.max(0, offset - pageSize))}
                            disabled={!canPrev || loading}
                            className="px-2.5 py-1 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
                        >
                            Prev
                        </button>
                        <button
                            onClick={() => loadAudit(offset + pageSize)}
                            disabled={!canNext || loading}
                            className="px-2.5 py-1 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
                        >
                            Next
                        </button>
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse min-w-[980px]">
                        <thead className="bg-slate-800/30 border-b border-border-dark text-xs font-bold text-slate-400 uppercase tracking-widest">
                            <tr>
                                <th className="px-6 py-4">Time</th>
                                <th className="px-6 py-4">Action</th>
                                <th className="px-6 py-4">Result</th>
                                <th className="px-6 py-4">Details</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border-dark/50 text-sm">
                            {entries.length === 0 && !loading && (
                                <tr>
                                    <td className="px-6 py-6 text-slate-400" colSpan={4}>No audit entries found for selected filters.</td>
                                </tr>
                            )}
                            {entries.map((entry, idx) => (
                                <tr key={`${entry.timestamp || 't'}-${entry.action || 'a'}-${idx}`} className="hover:bg-slate-800/20 transition-colors align-top">
                                    <td className="px-6 py-4 text-slate-300 whitespace-nowrap">{entry.timestamp || '-'}</td>
                                    <td className="px-6 py-4 font-semibold text-slate-100">{entry.action || '-'}</td>
                                    <td className="px-6 py-4">
                                        <span className={`px-2 py-1 rounded text-xs font-bold border ${entry.success ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                            {entry.success ? 'success' : 'failed'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <pre className="text-xs text-slate-300 whitespace-pre-wrap break-words font-mono">{JSON.stringify(entry.details || {}, null, 2)}</pre>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

function ContainersView({ runtimeState, containers }) {
    const entries = Array.isArray(containers) ? containers : [];
    const available = Boolean(runtimeState?.available);
    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end gap-4 flex-wrap">
                <div>
                    <h2 className="text-2xl font-bold text-slate-100">Container Runtime</h2>
                    <p className="text-slate-400 mt-1">Docker/Podman runtime health and workload inventory.</p>
                </div>
                <div className={`px-3 py-1 rounded-full text-xs font-bold border ${available ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>
                    {available ? 'runtime available' : 'runtime unavailable'}
                </div>
            </div>

            <div className="glass rounded-xl border border-border-dark/60 p-5">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="rounded-lg border border-border-dark/60 bg-slate-900/40 p-4">
                        <p className="text-xs uppercase tracking-wider text-slate-500">Runtime</p>
                        <p className="mt-2 text-lg font-semibold text-slate-100">{runtimeState?.runtime || 'none'}</p>
                    </div>
                    <div className="rounded-lg border border-border-dark/60 bg-slate-900/40 p-4">
                        <p className="text-xs uppercase tracking-wider text-slate-500">Container Count</p>
                        <p className="mt-2 text-lg font-semibold text-slate-100">{entries.length}</p>
                    </div>
                    <div className="rounded-lg border border-border-dark/60 bg-slate-900/40 p-4">
                        <p className="text-xs uppercase tracking-wider text-slate-500">Detail</p>
                        <p className="mt-2 text-sm font-semibold text-slate-100 break-words">{runtimeState?.detail || 'no runtime probe yet'}</p>
                    </div>
                </div>
            </div>

            <div className="glass rounded-xl overflow-hidden border border-border-dark/60">
                <div className="px-6 py-3 border-b border-border-dark/60 flex items-center justify-between text-xs text-slate-400">
                    <span>Discovered containers: {entries.length}</span>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse min-w-[760px]">
                        <thead className="bg-slate-800/30 border-b border-border-dark text-xs font-bold text-slate-400 uppercase tracking-widest">
                            <tr>
                                <th className="px-6 py-4">Name</th>
                                <th className="px-6 py-4">Image</th>
                                <th className="px-6 py-4">State</th>
                                <th className="px-6 py-4">Ports</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border-dark/50 text-sm">
                            {entries.length === 0 && (
                                <tr>
                                    <td className="px-6 py-6 text-slate-400" colSpan={4}>No containers returned from runtime.</td>
                                </tr>
                            )}
                            {entries.map((item, idx) => (
                                <tr key={`${item.ID || item.Names || 'container'}-${idx}`} className="hover:bg-slate-800/20 transition-colors">
                                    <td className="px-6 py-4 text-slate-100 font-semibold">{item.Names || item.ID || '-'}</td>
                                    <td className="px-6 py-4 text-slate-300">{item.Image || '-'}</td>
                                    <td className="px-6 py-4 text-slate-300">{item.State || item.Status || '-'}</td>
                                    <td className="px-6 py-4 text-slate-300 break-words">{item.Ports || '-'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

function ClustersView() {
    const [nodes, setNodes] = useState([]);
    const [overview, setOverview] = useState(null);
    const [loadingCluster, setLoadingCluster] = useState(true);
    const [clusterError, setClusterError] = useState(null);

    const fetchCluster = async () => {
        setLoadingCluster(true);
        setClusterError(null);
        try {
            const token = localStorage.getItem('hsdev_token');
            const headers = { Authorization: `Bearer ${token}` };
            const [nodesRes, overviewRes] = await Promise.all([
                fetch('/devapi/api/clusters/nodes', { headers }),
                fetch('/devapi/api/clusters/overview', { headers }),
            ]);
            if (nodesRes.ok) {
                const d = await nodesRes.json();
                setNodes(d.nodes || []);
            }
            if (overviewRes.ok) {
                setOverview(await overviewRes.json());
            }
        } catch (err) {
            setClusterError(err.message);
        } finally {
            setLoadingCluster(false);
        }
    };

    useEffect(() => { fetchCluster(); }, []);

    const total = overview?.total_nodes ?? nodes.length;
    const online = overview?.online ?? nodes.filter(n => n.status === 'online').length;
    const degraded = overview?.degraded ?? 0;

    const NODE_STATUS_COLORS = {
        online: 'bg-green-500/10 text-green-400 border-green-500/20',
        offline: 'bg-red-500/10 text-red-400 border-red-500/20',
        pending: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    };

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end gap-4 flex-wrap">
                <div>
                    <h2 className="text-2xl font-bold text-slate-100">Cluster Control Plane</h2>
                    <p className="text-slate-400 mt-1">Registered nodes, failover posture, and replication health.</p>
                </div>
                <button onClick={fetchCluster} className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 text-sm font-bold rounded-lg hover:bg-slate-700 transition-colors flex items-center gap-2">
                    <span className="material-symbols-outlined text-[18px]">refresh</span> Refresh
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricTile label="Total Nodes" value={total} tone="primary" />
                <MetricTile label="Online" value={online} tone="green" />
                <MetricTile label="Degraded" value={degraded} tone={degraded > 0 ? 'red' : 'green'} />
            </div>

            <div className="glass rounded-xl overflow-hidden border border-border-dark/60">
                {loadingCluster ? (
                    <div className="p-8 text-center text-slate-400 text-sm animate-pulse">Loading cluster nodes…</div>
                ) : clusterError ? (
                    <div className="p-8 text-center text-red-400 text-sm">
                        Failed to load: {clusterError}
                        <button onClick={fetchCluster} className="ml-3 text-primary underline">Retry</button>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse min-w-[680px]">
                            <thead className="bg-slate-800/30 border-b border-border-dark text-xs font-bold text-slate-400 uppercase tracking-widest">
                                <tr>
                                    <th className="px-6 py-4">Hostname</th>
                                    <th className="px-6 py-4">IP Address</th>
                                    <th className="px-6 py-4">Cluster ID</th>
                                    <th className="px-6 py-4">Last Heartbeat</th>
                                    <th className="px-6 py-4">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border-dark/50 text-sm">
                                {nodes.length === 0 ? (
                                    <tr><td colSpan={5} className="px-6 py-10 text-center text-slate-500">No nodes registered. Register your first panel installation to start managing the cluster.</td></tr>
                                ) : nodes.map((n) => (
                                    <tr key={n.id} className="hover:bg-slate-800/20 transition-colors">
                                        <td className="px-6 py-4 font-semibold text-slate-100">{n.hostname}</td>
                                        <td className="px-6 py-4 font-mono text-xs text-slate-400">{n.ip_address}</td>
                                        <td className="px-6 py-4 font-mono text-xs text-slate-400">{n.cluster_id ? n.cluster_id.slice(0, 8) + '…' : '—'}</td>
                                        <td className="px-6 py-4 text-slate-400 text-xs">{n.last_heartbeat ? new Date(n.last_heartbeat).toLocaleString() : 'never'}</td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 rounded text-xs font-bold border capitalize ${NODE_STATUS_COLORS[n.status] || 'bg-slate-700/30 text-slate-400 border-slate-600/30'}`}>
                                                {n.status}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
function UpdatesView() {
    const [releases, setReleases] = useState([]);
    const [loadingUpdates, setLoadingUpdates] = useState(true);
    const [updatesError, setUpdatesError] = useState(null);
    const [showReleaseModal, setShowReleaseModal] = useState(false);
    const [releaseForm, setReleaseForm] = useState({ version: '', channel: 'stable', changelog: '', is_critical: false });
    const [releaseSubmitting, setReleaseSubmitting] = useState(false);
    const [releaseError, setReleaseError] = useState(null);
    const [releaseSuccess, setReleaseSuccess] = useState(null);

    const fetchReleases = async () => {
        setLoadingUpdates(true);
        setUpdatesError(null);
        try {
            const token = localStorage.getItem('hsdev_token');
            const res = await fetch('/devapi/api/updates/releases', {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            setReleases(data.updates || []);
        } catch (err) {
            setUpdatesError(err.message);
        } finally {
            setLoadingUpdates(false);
        }
    };

    useEffect(() => { fetchReleases(); }, []);

    const critical = releases.filter(r => r.is_critical).length;
    const unpublished = releases.filter(r => !r.published).length;

    const handleCreateRelease = async (e) => {
        e.preventDefault();
        setReleaseSubmitting(true);
        setReleaseError(null);
        setReleaseSuccess(null);
        try {
            const token = localStorage.getItem('hsdev_token');
            const res = await fetch('/devapi/api/updates/release', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({
                    version: releaseForm.version,
                    channel: releaseForm.channel,
                    changelog: releaseForm.changelog,
                    is_critical: releaseForm.is_critical,
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
            setReleaseSuccess(`Release v${data.update?.version || releaseForm.version} created.`);
            fetchReleases();
        } catch (err) {
            setReleaseError(err.message);
        } finally {
            setReleaseSubmitting(false);
        }
    };

    const handlePublish = async (id) => {
        try {
            const token = localStorage.getItem('hsdev_token');
            await fetch('/devapi/api/updates/release/publish', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({ update_id: id }),
            });
            fetchReleases();
        } catch (err) {
            alert(`Publish failed: ${err.message}`);
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end gap-4 flex-wrap">
                <div>
                    <h2 className="text-2xl font-bold text-slate-100">Update Orchestrator</h2>
                    <p className="text-slate-400 mt-1">Version channels, release artifacts, and rollout management.</p>
                </div>
                <button onClick={() => { setShowReleaseModal(true); setReleaseSuccess(null); setReleaseError(null); }}
                    className="px-4 py-2 bg-primary text-white text-sm font-bold rounded-lg hover:bg-primary/90 transition-colors flex items-center gap-2">
                    <span className="material-symbols-outlined text-[20px]">add</span> New Release
                </button>
            </div>

            <div className="glass rounded-xl border border-border-dark/60 p-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <MetricTile label="Total Releases" value={releases.length} tone="primary" />
                    <MetricTile label="Critical" value={critical} tone={critical > 0 ? 'red' : 'green'} />
                    <MetricTile label="Draft (Unpublished)" value={unpublished} tone={unpublished > 0 ? 'amber' : 'green'} />
                </div>
            </div>

            <div className="glass rounded-xl overflow-hidden border border-border-dark/60">
                {loadingUpdates ? (
                    <div className="p-8 text-center text-slate-400 text-sm animate-pulse">Loading releases…</div>
                ) : updatesError ? (
                    <div className="p-8 text-center text-red-400 text-sm">
                        Failed to load: {updatesError}
                        <button onClick={fetchReleases} className="ml-3 text-primary underline">Retry</button>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse min-w-[760px]">
                            <thead className="bg-slate-800/30 border-b border-border-dark text-xs font-bold text-slate-400 uppercase tracking-widest">
                                <tr>
                                    <th className="px-6 py-4">Version</th>
                                    <th className="px-6 py-4">Channel</th>
                                    <th className="px-6 py-4">Critical</th>
                                    <th className="px-6 py-4">Published</th>
                                    <th className="px-6 py-4">Created</th>
                                    <th className="px-6 py-4 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border-dark/50 text-sm">
                                {releases.length === 0 ? (
                                    <tr><td colSpan={6} className="px-6 py-10 text-center text-slate-500">No releases yet. Create the first release to start pushing updates.</td></tr>
                                ) : releases.map((r) => (
                                    <tr key={r.id} className="hover:bg-slate-800/20 transition-colors">
                                        <td className="px-6 py-4 font-mono font-bold text-primary text-sm">{r.version}</td>
                                        <td className="px-6 py-4"><span className="px-2 py-1 rounded bg-slate-700/40 text-slate-300 text-xs font-bold border border-slate-600/30 uppercase">{r.channel}</span></td>
                                        <td className="px-6 py-4">{r.is_critical ? <span className="px-2 py-1 rounded bg-red-500/10 text-red-400 text-xs font-bold border border-red-500/20">critical</span> : <span className="text-slate-600 text-xs">—</span>}</td>
                                        <td className="px-6 py-4">{r.published ? <span className="px-2 py-1 rounded bg-green-500/10 text-green-400 text-xs font-bold border border-green-500/20">live</span> : <span className="px-2 py-1 rounded bg-amber-500/10 text-amber-400 text-xs font-bold border border-amber-500/20">draft</span>}</td>
                                        <td className="px-6 py-4 text-slate-400 text-xs">{r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}</td>
                                        <td className="px-6 py-4 text-right">
                                            {!r.published && (
                                                <button onClick={() => handlePublish(r.id)}
                                                    className="px-3 py-1.5 bg-primary/10 border border-primary/30 rounded text-xs text-primary hover:bg-primary/20 transition-colors font-semibold">
                                                    Publish
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {showReleaseModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
                    <div className="glass rounded-2xl border border-border-dark/60 w-full max-w-md p-6 space-y-5 shadow-2xl">
                        <div className="flex justify-between items-center">
                            <h3 className="text-lg font-bold text-slate-100">Create New Release</h3>
                            <button onClick={() => setShowReleaseModal(false)} className="text-slate-400 hover:text-slate-200">
                                <span className="material-symbols-outlined text-[22px]">close</span>
                            </button>
                        </div>
                        {releaseSuccess ? (
                            <div className="space-y-4">
                                <p className="text-sm text-green-400">{releaseSuccess}</p>
                                <button onClick={() => { setShowReleaseModal(false); setReleaseSuccess(null); setReleaseForm({ version: '', channel: 'stable', changelog: '', is_critical: false }); }}
                                    className="w-full px-4 py-2 bg-primary rounded-lg text-sm text-white font-bold hover:bg-primary/90 transition-colors">Done</button>
                            </div>
                        ) : (
                            <form onSubmit={handleCreateRelease} className="space-y-4">
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <label className="block text-xs text-slate-400 mb-1">Version <span className="text-red-400">*</span></label>
                                        <input type="text" required placeholder="2.3.0" value={releaseForm.version}
                                            onChange={e => setReleaseForm(f => ({ ...f, version: e.target.value }))}
                                            className="w-full bg-slate-900 border border-border-dark rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-primary/60" />
                                    </div>
                                    <div>
                                        <label className="block text-xs text-slate-400 mb-1">Channel</label>
                                        <select value={releaseForm.channel} onChange={e => setReleaseForm(f => ({ ...f, channel: e.target.value }))}
                                            className="w-full bg-slate-900 border border-border-dark rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-primary/60">
                                            <option value="stable">stable</option>
                                            <option value="beta">beta</option>
                                            <option value="dev">dev</option>
                                        </select>
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-xs text-slate-400 mb-1">Changelog</label>
                                    <textarea rows={3} value={releaseForm.changelog}
                                        onChange={e => setReleaseForm(f => ({ ...f, changelog: e.target.value }))}
                                        className="w-full bg-slate-900 border border-border-dark rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-primary/60 resize-none"
                                        placeholder="What changed in this release…" />
                                </div>
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input type="checkbox" checked={releaseForm.is_critical}
                                        onChange={e => setReleaseForm(f => ({ ...f, is_critical: e.target.checked }))}
                                        className="w-4 h-4 rounded border-border-dark bg-slate-900" />
                                    <span className="text-sm text-slate-300">Mark as critical security release</span>
                                </label>
                                {releaseError && <p className="text-xs text-red-400 bg-red-900/20 border border-red-700/30 rounded px-3 py-2">{releaseError}</p>}
                                <div className="flex gap-3 justify-end">
                                    <button type="button" onClick={() => setShowReleaseModal(false)}
                                        className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 hover:bg-slate-700 transition-colors">Cancel</button>
                                    <button type="submit" disabled={releaseSubmitting}
                                        className="px-4 py-2 bg-primary rounded-lg text-sm text-white font-bold hover:bg-primary/90 transition-colors disabled:opacity-50">
                                        {releaseSubmitting ? 'Creating…' : 'Create Release'}
                                    </button>
                                </div>
                            </form>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
function AnalyticsView() {
    const [analyticsData, setAnalyticsData] = useState(null);
    const [installData, setInstallData] = useState(null);
    const [loadingAnalytics, setLoadingAnalytics] = useState(true);
    const [pluginStats, setPluginStats] = useState(null);

    useEffect(() => {
        (async () => {
            setLoadingAnalytics(true);
            try {
                const token = localStorage.getItem('hsdev_token');
                const headers = { Authorization: `Bearer ${token}` };
                const [statsRes, installRes, pluginRes] = await Promise.all([
                    fetch('/devapi/api/analytics/stats', { headers }),
                    fetch('/devapi/api/analytics/installations?days=7', { headers }),
                    fetch('/devapi/api/analytics/plugins/stats', { headers }),
                ]);
                if (statsRes.ok) setAnalyticsData(await statsRes.json());
                if (installRes.ok) setInstallData(await installRes.json());
                if (pluginRes.ok) setPluginStats(await pluginRes.json());
            } catch (err) {
                console.error('Analytics fetch failed:', err);
            } finally {
                setLoadingAnalytics(false);
            }
        })();
    }, []);

    const totalServers = analyticsData?.totalServers ?? '—';
    const activeServers = analyticsData?.activeServers ?? '—';
    const totalLicenses = analyticsData?.totalLicenses ?? '—';
    const activeLicenses = analyticsData?.activeLicenses ?? '—';
    const totalPlugins = analyticsData?.totalPlugins ?? '—';
    const totalDownloads = analyticsData?.totalDownloads ?? pluginStats?.total_downloads ?? '—';
    const topPlugins = pluginStats?.top_plugins || [];
    const dailyCounts = installData?.installs?.daily_counts || [];
    const trend = dailyCounts.length >= 7 ? dailyCounts.slice(-7) : [10, 14, 12, 18, 22, 20, 28];
    const max = Math.max(...trend, 1);

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div>
                <h2 className="text-2xl font-bold text-slate-100">Analytics Pulse</h2>
                <p className="text-slate-400 mt-1">Adoption, workload, and reliability trends across your managed fleet.</p>
            </div>

            {loadingAnalytics ? (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                    {[1,2,3,4].map(i => (
                        <div key={i} className="glass rounded-xl border border-border-dark/60 p-5 animate-pulse">
                            <div className="h-3 bg-slate-700 rounded w-2/3 mb-3"></div>
                            <div className="h-8 bg-slate-800 rounded w-1/2"></div>
                        </div>
                    ))}
                </div>
            ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <MetricTile label="Total Servers" value={totalServers} tone="primary" />
                <MetricTile label="Active Servers" value={activeServers} tone="green" />
                <MetricTile label="Active Licenses" value={activeLicenses} tone="green" />
                <MetricTile label="Plugin Downloads" value={totalDownloads} tone="slate" />
            </div>
            )}

            <div className="glass rounded-xl border border-border-dark/60 p-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-slate-100">7-Day Install Trend</h3>
                    <p className="text-xs text-slate-500">installations / day</p>
                </div>
                <div className="grid grid-cols-7 gap-3 h-40 items-end">
                    {trend.map((value, idx) => (
                        <div key={idx} className="flex flex-col items-center gap-2">
                            <div
                                className="w-full rounded-t bg-gradient-to-t from-primary/40 to-primary border border-primary/30"
                                style={{ height: `${Math.max(16, Math.round((value / max) * 120))}px` }}
                            ></div>
                            <span className="text-[11px] text-slate-500">D{idx + 1}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
function MonitoringView({ software }) {
    const items = Array.isArray(software) ? software : [];
    const activeCount = items.filter((s) => s.status === 'active').length;
    const degradedCount = Math.max(0, items.length - activeCount);

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div>
                <h2 className="text-2xl font-bold text-slate-100">Service Link Monitor</h2>
                <p className="text-slate-400 mt-1">Live status for software/services linked to dashboard actions.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricTile label="Services" value={items.length} tone="primary" />
                <MetricTile label="Active" value={activeCount} tone="green" />
                <MetricTile label="Attention Needed" value={degradedCount} tone={degradedCount > 0 ? 'amber' : 'green'} />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {items.map((s) => (
                    <div key={s.id} className="glass rounded-xl p-4 border border-border-dark/60">
                        <p className="text-slate-100 font-semibold">{s.name}</p>
                        <p className="text-xs text-slate-400 uppercase mt-1">{s.category}</p>
                        <div className="mt-3 flex items-center justify-between">
                            <span className="text-xs text-slate-400">service: {s.service_unit}</span>
                            <span className={`px-2 py-1 rounded text-xs font-bold border ${s.status === 'active' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>
                                {s.status}
                            </span>
                        </div>
                    </div>
                ))}
                {items.length === 0 && (
                    <div className="glass rounded-xl p-6 border border-border-dark/60 text-slate-400 md:col-span-2 xl:col-span-3">
                        No service telemetry available yet. Connect software endpoints to populate live monitoring cards.
                    </div>
                )}
            </div>
        </div>
    );
}

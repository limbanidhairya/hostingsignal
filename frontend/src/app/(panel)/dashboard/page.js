'use client';
import { useState, useEffect } from 'react';

export default function DashboardPage() {
    const [stats, setStats] = useState(null);
    const [services, setServices] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const apiUrl = typeof window !== 'undefined'
            ? `${window.location.protocol}//${window.location.hostname}:8000`
            : 'http://localhost:8000';

        Promise.all([
            fetch(`${apiUrl}/api/monitoring/overview`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
                .then(r => r.json()).catch(() => null),
            fetch(`${apiUrl}/api/monitoring/services`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
                .then(r => r.json()).catch(() => null),
        ]).then(([statsData, servicesData]) => {
            setStats(statsData?.data || getMockStats());
            setServices(servicesData?.services || getMockServices());
            setLoading(false);
        });
    }, []);

    const getMockStats = () => ({
        cpu_percent: 23,
        memory_percent: 45,
        memory_used_gb: 3.6,
        memory_total_gb: 8,
        disk_percent: 34,
        disk_used_gb: 68,
        disk_total_gb: 200,
        load_avg_1: 0.45,
        load_avg_5: 0.52,
        load_avg_15: 0.48,
    });

    const getMockServices = () => ({
        'lsws': 'active', 'mariadb': 'active', 'redis-server': 'active',
        'postfix': 'active', 'hostingsignal-api': 'active', 'hostingsignal-web': 'active',
    });

    if (loading) {
        return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh', color: 'var(--hs-text-muted)' }}>Loading dashboard...</div>;
    }

    const s = stats || getMockStats();

    return (
        <div>
            {/* Stats Grid */}
            <div className="hs-stats-grid">
                <div className="hs-stat-card">
                    <div className="hs-stat-icon blue">💻</div>
                    <div className="hs-stat-info">
                        <div className="hs-stat-value">{s.cpu_percent}%</div>
                        <div className="hs-stat-label">CPU Usage</div>
                    </div>
                </div>
                <div className="hs-stat-card">
                    <div className="hs-stat-icon green">🧠</div>
                    <div className="hs-stat-info">
                        <div className="hs-stat-value">{s.memory_percent}%</div>
                        <div className="hs-stat-label">{s.memory_used_gb}GB / {s.memory_total_gb}GB RAM</div>
                    </div>
                </div>
                <div className="hs-stat-card">
                    <div className="hs-stat-icon orange">💾</div>
                    <div className="hs-stat-info">
                        <div className="hs-stat-value">{s.disk_percent}%</div>
                        <div className="hs-stat-label">{s.disk_used_gb}GB / {s.disk_total_gb}GB Disk</div>
                    </div>
                </div>
                <div className="hs-stat-card">
                    <div className="hs-stat-icon purple">⚡</div>
                    <div className="hs-stat-info">
                        <div className="hs-stat-value">{s.load_avg_1}</div>
                        <div className="hs-stat-label">Load Average (1m)</div>
                    </div>
                </div>
            </div>

            {/* Resource Usage Cards */}
            <div className="hs-grid-2" style={{ marginBottom: 24 }}>
                <div className="hs-card">
                    <div className="hs-card-header">
                        <h3 className="hs-card-title">Resource Usage</h3>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13, color: 'var(--hs-text-secondary)' }}>
                                <span>CPU</span><span>{s.cpu_percent}%</span>
                            </div>
                            <div className="hs-progress">
                                <div className="hs-progress-bar blue" style={{ width: `${s.cpu_percent}%` }}></div>
                            </div>
                        </div>
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13, color: 'var(--hs-text-secondary)' }}>
                                <span>Memory</span><span>{s.memory_percent}%</span>
                            </div>
                            <div className="hs-progress">
                                <div className="hs-progress-bar green" style={{ width: `${s.memory_percent}%` }}></div>
                            </div>
                        </div>
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13, color: 'var(--hs-text-secondary)' }}>
                                <span>Disk</span><span>{s.disk_percent}%</span>
                            </div>
                            <div className="hs-progress">
                                <div className={`hs-progress-bar ${s.disk_percent > 80 ? 'red' : 'orange'}`} style={{ width: `${s.disk_percent}%` }}></div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="hs-card">
                    <div className="hs-card-header">
                        <h3 className="hs-card-title">Service Health</h3>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {Object.entries(services).map(([name, status]) => (
                            <div key={name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--hs-border)' }}>
                                <span style={{ fontSize: 14, color: 'var(--hs-text-secondary)' }}>{name}</span>
                                <span className={`hs-badge ${status === 'active' ? 'success' : 'error'}`}>
                                    {status === 'active' ? '● Active' : '● Inactive'}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Quick Actions */}
            <div className="hs-card">
                <div className="hs-card-header">
                    <h3 className="hs-card-title">Quick Actions</h3>
                </div>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                    <a href="/websites" className="hs-btn hs-btn-primary">🌐 Create Website</a>
                    <a href="/databases" className="hs-btn hs-btn-secondary">🗄️ New Database</a>
                    <a href="/email" className="hs-btn hs-btn-secondary">📧 Add Email</a>
                    <a href="/backups" className="hs-btn hs-btn-secondary">💾 Create Backup</a>
                    <a href="/security" className="hs-btn hs-btn-secondary">🛡️ Firewall</a>
                    <a href="/dns" className="hs-btn hs-btn-secondary">🗂️ DNS Editor</a>
                </div>
            </div>
        </div>
    );
}

'use client';
import { useState, useEffect, useRef } from 'react';

export default function MonitoringPage() {
    const [stats, setStats] = useState(null);
    const [history, setHistory] = useState([]);
    const [processes, setProcesses] = useState([]);
    const wsRef = useRef(null);

    useEffect(() => {
        // Mock real-time data
        const generateStat = () => ({
            cpu_percent: Math.round(15 + Math.random() * 30),
            memory_percent: Math.round(40 + Math.random() * 20),
            memory_used_gb: (3 + Math.random() * 2).toFixed(1),
            memory_total_gb: 8,
            disk_percent: 34,
            disk_used_gb: 68,
            disk_total_gb: 200,
            net_bytes_sent: Math.round(Math.random() * 10000000),
            net_bytes_recv: Math.round(Math.random() * 50000000),
            load_avg_1: (0.3 + Math.random() * 0.5).toFixed(2),
            load_avg_5: (0.4 + Math.random() * 0.4).toFixed(2),
            load_avg_15: (0.35 + Math.random() * 0.3).toFixed(2),
            timestamp: new Date().toISOString(),
        });

        setStats(generateStat());
        setHistory(Array.from({ length: 20 }, () => generateStat()));

        // Mock processes
        setProcesses([
            { pid: 1234, name: 'lshttpd', cpu: 5.2, memory: 3.1, status: 'running' },
            { pid: 2345, name: 'mysqld', cpu: 2.8, memory: 12.4, status: 'running' },
            { pid: 3456, name: 'redis-server', cpu: 0.5, memory: 1.2, status: 'running' },
            { pid: 4567, name: 'node', cpu: 3.1, memory: 4.8, status: 'running' },
            { pid: 5678, name: 'python3', cpu: 1.9, memory: 2.3, status: 'running' },
            { pid: 6789, name: 'dovecot', cpu: 0.2, memory: 0.8, status: 'running' },
        ]);

        // Simulated live updates
        const interval = setInterval(() => {
            const newStat = generateStat();
            setStats(newStat);
            setHistory(prev => [...prev.slice(-29), newStat]);
        }, 3000);

        return () => {
            clearInterval(interval);
            if (wsRef.current) wsRef.current.close();
        };
    }, []);

    if (!stats) {
        return <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--hs-text-muted)' }}>Loading monitoring data...</div>;
    }

    const formatBytes = (bytes) => {
        if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(1) + ' GB';
        if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + ' MB';
        if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return bytes + ' B';
    };

    // Simple bar chart component
    const MiniChart = ({ data, color, height = 60 }) => {
        const max = Math.max(...data, 1);
        return (
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height }}>
                {data.slice(-30).map((val, i) => (
                    <div
                        key={i}
                        style={{
                            flex: 1,
                            height: `${(val / max) * 100}%`,
                            background: `linear-gradient(to top, ${color}88, ${color})`,
                            borderRadius: '2px 2px 0 0',
                            minHeight: 2,
                            transition: 'height 0.3s ease',
                        }}
                    />
                ))}
            </div>
        );
    };

    return (
        <div>
            {/* Live Indicator */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', animation: 'pulse 2s infinite' }} />
                <span style={{ fontSize: 13, color: 'var(--hs-text-muted)' }}>Live monitoring — updates every 3s</span>
            </div>

            {/* Stats Grid */}
            <div className="hs-stats-grid">
                <div className="hs-stat-card">
                    <div className="hs-stat-icon blue">💻</div>
                    <div className="hs-stat-info">
                        <div className="hs-stat-value">{stats.cpu_percent}%</div>
                        <div className="hs-stat-label">CPU Usage</div>
                    </div>
                </div>
                <div className="hs-stat-card">
                    <div className="hs-stat-icon green">🧠</div>
                    <div className="hs-stat-info">
                        <div className="hs-stat-value">{stats.memory_percent}%</div>
                        <div className="hs-stat-label">{stats.memory_used_gb} / {stats.memory_total_gb} GB</div>
                    </div>
                </div>
                <div className="hs-stat-card">
                    <div className="hs-stat-icon orange">💾</div>
                    <div className="hs-stat-info">
                        <div className="hs-stat-value">{stats.disk_percent}%</div>
                        <div className="hs-stat-label">{stats.disk_used_gb} / {stats.disk_total_gb} GB</div>
                    </div>
                </div>
                <div className="hs-stat-card">
                    <div className="hs-stat-icon purple">📡</div>
                    <div className="hs-stat-info">
                        <div className="hs-stat-value">{formatBytes(stats.net_bytes_recv)}</div>
                        <div className="hs-stat-label">Network In</div>
                    </div>
                </div>
            </div>

            {/* Charts */}
            <div className="hs-grid-2" style={{ marginBottom: 24 }}>
                <div className="hs-card">
                    <div className="hs-card-header">
                        <h3 className="hs-card-title">CPU History</h3>
                        <span style={{ fontSize: 12, color: 'var(--hs-text-muted)' }}>Last 30 samples</span>
                    </div>
                    <MiniChart data={history.map(h => h.cpu_percent)} color="#3b82f6" height={80} />
                </div>
                <div className="hs-card">
                    <div className="hs-card-header">
                        <h3 className="hs-card-title">Memory History</h3>
                        <span style={{ fontSize: 12, color: 'var(--hs-text-muted)' }}>Last 30 samples</span>
                    </div>
                    <MiniChart data={history.map(h => h.memory_percent)} color="#10b981" height={80} />
                </div>
            </div>

            {/* Load Average */}
            <div className="hs-card" style={{ marginBottom: 24 }}>
                <h3 className="hs-card-title" style={{ marginBottom: 16 }}>Load Average</h3>
                <div className="hs-grid-3">
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--hs-accent)' }}>{stats.load_avg_1}</div>
                        <div style={{ fontSize: 13, color: 'var(--hs-text-muted)' }}>1 minute</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--hs-primary)' }}>{stats.load_avg_5}</div>
                        <div style={{ fontSize: 13, color: 'var(--hs-text-muted)' }}>5 minutes</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '2rem', fontWeight: 700, color: '#10b981' }}>{stats.load_avg_15}</div>
                        <div style={{ fontSize: 13, color: 'var(--hs-text-muted)' }}>15 minutes</div>
                    </div>
                </div>
            </div>

            {/* Top Processes */}
            <div className="hs-card" style={{ padding: 0, overflow: 'hidden' }}>
                <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--hs-border)' }}>
                    <h3 className="hs-card-title">Top Processes</h3>
                </div>
                <table className="hs-table">
                    <thead>
                        <tr><th>PID</th><th>Process</th><th>CPU %</th><th>Memory %</th><th>Status</th></tr>
                    </thead>
                    <tbody>
                        {processes.map((p) => (
                            <tr key={p.pid}>
                                <td style={{ color: 'var(--hs-text-muted)', fontFamily: 'monospace' }}>{p.pid}</td>
                                <td style={{ fontWeight: 550 }}>{p.name}</td>
                                <td>{p.cpu}%</td>
                                <td>{p.memory}%</td>
                                <td><span className="hs-badge success">{p.status}</span></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <style jsx>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
        </div>
    );
}

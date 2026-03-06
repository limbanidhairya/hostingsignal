'use client';
import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

export default function DockerPage() {
    const { showToast, ToastContainer } = useToast();
    const [containers, setContainers] = useState([]);
    const [images, setImages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('containers');
    const [showLogs, setShowLogs] = useState(null);
    const [logs, setLogs] = useState('');

    useEffect(() => { loadAll(); }, []);

    async function loadAll() {
        try {
            const [c, img] = await Promise.all([api.getDockerContainers(), api.getDockerImages()]);
            setContainers(Array.isArray(c) ? c : []);
            setImages(Array.isArray(img) ? img : []);
        } catch { showToast('Failed to load Docker data', 'error'); }
        finally { setLoading(false); }
    }

    async function handleAction(id, action) {
        try {
            if (action === 'start') await api.startContainer(id);
            else if (action === 'stop') await api.stopContainer(id);
            else if (action === 'restart') await api.restartContainer(id);
            else if (action === 'remove') { if (!confirm('Remove this container?')) return; await api.removeContainer(id); }
            showToast(`Container ${action}ed`, 'success'); loadAll();
        } catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    async function viewLogs(id) {
        try { const data = await api.getContainerLogs(id); setLogs(data.logs || data); setShowLogs(id); }
        catch (e) { showToast('Failed to get logs', 'error'); }
    }

    if (loading) return <div className="animate-fade" style={{ padding: 60, textAlign: 'center' }}><div className="stat-value">⏳</div><p>Loading Docker...</p></div>;

    return (
        <div className="animate-fade">
            <ToastContainer />
            <div className="page-header"><div><h1 className="glow-text">Docker</h1><p>Manage Docker containers and images</p></div></div>

            <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                <div className="stat-card blue clay-card" style={{ background: 'transparent' }}><div className="stat-icon blue">📦</div><div className="stat-content"><div className="stat-value glow-text">{containers.length}</div><div className="stat-label">Containers</div></div></div>
                <div className="stat-card green clay-card" style={{ background: 'transparent' }}><div className="stat-icon green">▶️</div><div className="stat-content"><div className="stat-value glow-text">{containers.filter(c => c.status?.includes('running') || c.state === 'running').length}</div><div className="stat-label">Running</div></div></div>
                <div className="stat-card purple clay-card" style={{ background: 'transparent' }}><div className="stat-icon purple">🖼️</div><div className="stat-content"><div className="stat-value glow-text">{images.length}</div><div className="stat-label">Images</div></div></div>
            </div>

            <div className="tabs">
                {['containers', 'images'].map(t => (
                    <button key={t} className={`tab ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t)}>
                        {t === 'containers' ? '📦 Containers' : '🖼️ Images'}
                    </button>
                ))}
            </div>

            {activeTab === 'containers' && (
                <div className="table-container liquid-glass"><table><thead><tr><th>Name</th><th>Image</th><th>Status</th><th>Ports</th><th>Actions</th></tr></thead>
                    <tbody>{containers.map((c, i) => {
                        const isRunning = c.status?.includes('Up') || c.state === 'running';
                        return (
                            <tr key={i}>
                                <td style={{ fontWeight: 600 }}>{c.name || c.names}</td>
                                <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{c.image}</td>
                                <td><span className={`badge ${isRunning ? 'badge-success' : 'badge-warning'} badge-dot`}>{c.status || c.state}</span></td>
                                <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{c.ports || '-'}</td>
                                <td><div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                                    {!isRunning && <button className="btn btn-sm skeuo-btn" onClick={() => handleAction(c.id, 'start')}>▶ Start</button>}
                                    {isRunning && <button className="btn btn-sm skeuo-btn" onClick={() => handleAction(c.id, 'stop')}>⏹ Stop</button>}
                                    <button className="btn btn-sm skeuo-btn" onClick={() => handleAction(c.id, 'restart')}>🔄</button>
                                    <button className="btn btn-sm skeuo-btn" onClick={() => viewLogs(c.id)}>📋</button>
                                    <button className="btn btn-sm btn-danger skeuo-btn" style={{ background: 'var(--accent-red)' }} onClick={() => handleAction(c.id, 'remove')}>✕</button>
                                </div></td>
                            </tr>
                        );
                    })}</tbody></table></div>
            )}

            {activeTab === 'images' && (
                <div className="table-container liquid-glass"><table><thead><tr><th>Repository</th><th>Tag</th><th>Size</th><th>Created</th></tr></thead>
                    <tbody>{images.map((img, i) => (
                        <tr key={i}>
                            <td style={{ fontWeight: 600 }}>{img.repository || img.repo}</td>
                            <td><span className="badge badge-info">{img.tag || 'latest'}</span></td>
                            <td>{img.size}</td>
                            <td>{img.created}</td>
                        </tr>
                    ))}</tbody></table></div>
            )}

            {showLogs && (
                <div className="modal-overlay" onClick={() => setShowLogs(null)}><div className="modal liquid-glass" style={{ maxWidth: 800 }} onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h2 className="modal-title glow-text">Container Logs</h2><button className="modal-close" onClick={() => setShowLogs(null)}>✕</button></div>
                    <div className="modal-body"><pre style={{ background: 'rgba(0,0,0,0.5)', padding: 'var(--space-md)', borderRadius: 'var(--radius-md)', maxHeight: 400, overflow: 'auto', fontSize: 12, fontFamily: 'monospace', whiteSpace: 'pre-wrap', color: '#0f0' }}>{logs}</pre></div>
                </div></div>
            )}
        </div>
    );
}

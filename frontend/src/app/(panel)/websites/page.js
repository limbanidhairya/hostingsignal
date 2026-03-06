'use client';
import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

export default function WebsitesPage() {
    const { showToast, ToastContainer } = useToast();
    const [sites, setSites] = useState([]);
    const [loading, setLoading] = useState(true);
    const [view, setView] = useState('table');
    const [showCreate, setShowCreate] = useState(false);
    const [newDomain, setNewDomain] = useState('');
    const [newPHP, setNewPHP] = useState('8.2');
    const [creating, setCreating] = useState(false);

    useEffect(() => { loadSites(); }, []);

    async function loadSites() {
        try {
            const data = await api.getWebsites();
            setSites(Array.isArray(data) ? data : []);
        } catch { showToast('Failed to load websites', 'error'); }
        finally { setLoading(false); }
    }

    async function handleCreate() {
        if (!newDomain.trim()) { showToast('Enter a domain name', 'error'); return; }
        setCreating(true);
        try {
            await api.createWebsite(newDomain.trim(), newPHP);
            showToast(`Website ${newDomain} created!`, 'success');
            setShowCreate(false); setNewDomain('');
            loadSites();
        } catch (e) { showToast('Failed: ' + e.message, 'error'); }
        finally { setCreating(false); }
    }

    async function handleDelete(domain) {
        if (!confirm(`Delete ${domain}? This is irreversible.`)) return;
        try {
            await api.deleteWebsite(domain);
            showToast(`${domain} deleted`, 'success');
            loadSites();
        } catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    async function handleSSL(domain) {
        try {
            await api.issueSSL(domain);
            showToast(`SSL issued for ${domain}`, 'success');
            loadSites();
        } catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    if (loading) return <div className="animate-fade" style={{ padding: '60px', textAlign: 'center' }}><div className="stat-value">⏳</div><p>Loading websites...</p></div>;

    return (
        <div className="animate-fade">
            <ToastContainer />
            <div className="page-header">
                <div><h1 className="glow-text">Websites</h1><p>Manage all your websites and web applications</p></div>
                <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                    <div style={{ display: 'flex', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                        <button className={`btn btn-sm ${view === 'table' ? 'skeuo-btn-primary' : 'skeuo-btn'}`} style={{ borderRadius: 0, border: 'none' }} onClick={() => setView('table')}>☰ Table</button>
                        <button className={`btn btn-sm ${view === 'cards' ? 'skeuo-btn-primary' : 'skeuo-btn'}`} style={{ borderRadius: 0, border: 'none' }} onClick={() => setView('cards')}>▦ Cards</button>
                    </div>
                    <button className="btn skeuo-btn-primary" onClick={() => setShowCreate(true)}>+ Create Website</button>
                </div>
            </div>

            {sites.length === 0 ? (
                <div className="empty-state liquid-glass"><div className="empty-icon">🌐</div><h3 className="glow-text">No Websites Yet</h3><p>Create your first website to get started.</p>
                    <button className="btn skeuo-btn-primary" onClick={() => setShowCreate(true)}>+ Create Website</button></div>
            ) : view === 'table' ? (
                <div className="table-container liquid-glass">
                    <table><thead><tr><th>Website</th><th>Status</th><th>PHP</th><th>SSL</th><th>Doc Root</th><th>Actions</th></tr></thead>
                        <tbody>{sites.map((s, i) => (
                            <tr key={i}>
                                <td><div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-md)', background: 'var(--primary-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>🌐</div>
                                    <div><div style={{ fontWeight: 600 }}>{s.domain}</div></div>
                                </div></td>
                                <td><span className="badge badge-success badge-dot">{s.status}</span></td>
                                <td><span className="badge badge-purple">PHP {s.php}</span></td>
                                <td>{s.ssl ? <span className="badge badge-success">🔒 Active</span> : <button className="btn btn-sm btn-outline" onClick={() => handleSSL(s.domain)}>Issue SSL</button>}</td>
                                <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{s.doc_root}</td>
                                <td><div style={{ display: 'flex', gap: 6 }}>
                                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(s.domain)}>Delete</button>
                                </div></td>
                            </tr>
                        ))}</tbody></table>
                </div>
            ) : (
                <div className="grid-3">{sites.map((s, i) => (
                    <div key={i} className="card clay-card" style={{ background: 'transparent' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-md)' }}>
                            <div style={{ width: 48, height: 48, borderRadius: 'var(--radius-md)', background: 'var(--primary-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24 }}>🌐</div>
                            <span className="badge badge-success badge-dot">{s.status}</span>
                        </div>
                        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }} className="glow-text">{s.domain}</h3>
                        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 'var(--space-md)' }}>PHP {s.php} · {s.ssl ? '🔒 SSL' : 'No SSL'}</p>
                        <div style={{ marginTop: 'var(--space-md)', paddingTop: 'var(--space-md)', borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', gap: 8 }}>
                            {!s.ssl && <button className="btn btn-sm skeuo-btn" style={{ flex: 1 }} onClick={() => handleSSL(s.domain)}>Issue SSL</button>}
                            <button className="btn btn-sm btn-danger skeuo-btn" style={{ background: 'var(--accent-red)' }} onClick={() => handleDelete(s.domain)}>Delete</button>
                        </div>
                    </div>
                ))}</div>
            )}

            {showCreate && (
                <div className="modal-overlay" onClick={() => setShowCreate(false)}>
                    <div className="modal liquid-glass" onClick={e => e.stopPropagation()}>
                        <div className="modal-header"><h2 className="modal-title glow-text">Create New Website</h2><button className="modal-close" onClick={() => setShowCreate(false)}>✕</button></div>
                        <div className="modal-body">
                            <div className="form-group"><label className="form-label">Domain Name</label>
                                <input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="e.g., mywebsite.com" value={newDomain} onChange={e => setNewDomain(e.target.value)} /></div>
                            <div className="form-group"><label className="form-label">PHP Version</label>
                                <select className="form-input form-select" style={{ background: 'rgba(0,0,0,0.2)' }} value={newPHP} onChange={e => setNewPHP(e.target.value)}>
                                    <option value="8.2" style={{ background: 'black' }}>PHP 8.2 (Recommended)</option><option value="8.1" style={{ background: 'black' }}>PHP 8.1</option><option value="8.0" style={{ background: 'black' }}>PHP 8.0</option><option value="7.4" style={{ background: 'black' }}>PHP 7.4</option>
                                </select></div>
                        </div>
                        <div className="modal-footer"><button className="btn skeuo-btn" onClick={() => setShowCreate(false)}>Cancel</button>
                            <button className="btn skeuo-btn-primary" onClick={handleCreate} disabled={creating}>{creating ? '⏳ Creating...' : 'Create Website'}</button></div>
                    </div>
                </div>
            )}
        </div>
    );
}

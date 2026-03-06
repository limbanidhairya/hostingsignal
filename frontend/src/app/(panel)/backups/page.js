'use client';
import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

export default function BackupsPage() {
    const { showToast, ToastContainer } = useToast();
    const [backups, setBackups] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [domain, setDomain] = useState('');
    const [includeDb, setIncludeDb] = useState(true);
    const [includeEmail, setIncludeEmail] = useState(true);
    const [creating, setCreating] = useState(false);

    useEffect(() => { loadBackups(); }, []);

    async function loadBackups() {
        try { const data = await api.getBackups(); setBackups(Array.isArray(data) ? data : []); }
        catch { showToast('Failed to load backups', 'error'); }
        finally { setLoading(false); }
    }

    async function handleCreate() {
        if (!domain) { showToast('Enter a domain', 'error'); return; }
        setCreating(true);
        try { await api.createBackup(domain, includeDb, includeEmail); showToast('Backup created!', 'success'); setShowCreate(false); setDomain(''); loadBackups(); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
        finally { setCreating(false); }
    }

    async function handleRestore(id) {
        if (!confirm('Restore this backup? Current data will be overwritten.')) return;
        try { await api.restoreBackup(id); showToast('Backup restored!', 'success'); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    async function handleDelete(id) {
        if (!confirm('Delete this backup?')) return;
        try { await api.deleteBackup(id); showToast('Backup deleted', 'success'); loadBackups(); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    if (loading) return <div className="animate-fade" style={{ padding: 60, textAlign: 'center' }}><div className="stat-value">⏳</div><p>Loading backups...</p></div>;

    return (
        <div className="animate-fade">
            <ToastContainer />
            <div className="page-header"><div><h1 className="glow-text">Backups</h1><p>Create and restore full server backups</p></div>
                <button className="btn skeuo-btn-primary" onClick={() => setShowCreate(true)}>+ Create Backup</button></div>

            <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                <div className="stat-card blue clay-card" style={{ background: 'transparent' }}><div className="stat-icon blue">💾</div><div className="stat-content"><div className="stat-value glow-text">{backups.length}</div><div className="stat-label">Total Backups</div></div></div>
                <div className="stat-card green clay-card" style={{ background: 'transparent' }}><div className="stat-icon green">✅</div><div className="stat-content"><div className="stat-value glow-text">{backups.filter(b => b.status === 'complete').length}</div><div className="stat-label">Completed</div></div></div>
                <div className="stat-card purple clay-card" style={{ background: 'transparent' }}><div className="stat-icon purple">📦</div><div className="stat-content"><div className="stat-value glow-text">{backups.reduce((a, b) => a + parseFloat(b.size || '0'), 0).toFixed(1)} MB</div><div className="stat-label">Total Size</div></div></div>
            </div>

            {backups.length === 0 ? (
                <div className="empty-state liquid-glass"><div className="empty-icon">💾</div><h3 className="glow-text">No Backups Yet</h3><p>Create your first backup to protect your data.</p>
                    <button className="btn skeuo-btn-primary" onClick={() => setShowCreate(true)}>+ Create Backup</button></div>
            ) : (
                <div className="table-container liquid-glass"><table><thead><tr><th>Backup</th><th>Domain</th><th>Status</th><th>Size</th><th>Date</th><th>Actions</th></tr></thead>
                    <tbody>{backups.map((b, i) => (
                        <tr key={i}>
                            <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{b.id || b.file}</td>
                            <td style={{ fontWeight: 600 }}>{b.domain}</td>
                            <td><span className={`badge ${b.status === 'complete' ? 'badge-success' : 'badge-warning'}`}>{b.status}</span></td>
                            <td>{b.size}</td>
                            <td>{b.date || b.created}</td>
                            <td><div style={{ display: 'flex', gap: 6 }}>
                                <button className="btn btn-sm skeuo-btn" onClick={() => handleRestore(b.id)}>🔄 Restore</button>
                                <button className="btn btn-sm btn-danger skeuo-btn" style={{ background: 'var(--accent-red)' }} onClick={() => handleDelete(b.id)}>Delete</button>
                            </div></td>
                        </tr>
                    ))}</tbody></table></div>
            )}

            {showCreate && (
                <div className="modal-overlay" onClick={() => setShowCreate(false)}><div className="modal liquid-glass" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h2 className="modal-title glow-text">Create Backup</h2><button className="modal-close" onClick={() => setShowCreate(false)}>✕</button></div>
                    <div className="modal-body">
                        <div className="form-group"><label className="form-label">Domain</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="example.com" value={domain} onChange={e => setDomain(e.target.value)} /></div>
                        <div className="form-group"><label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                            <input type="checkbox" checked={includeDb} onChange={e => setIncludeDb(e.target.checked)} /><span className="form-label" style={{ marginBottom: 0 }}>Include Databases</span></label></div>
                        <div className="form-group"><label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                            <input type="checkbox" checked={includeEmail} onChange={e => setIncludeEmail(e.target.checked)} /><span className="form-label" style={{ marginBottom: 0 }}>Include Email Data</span></label></div>
                    </div>
                    <div className="modal-footer"><button className="btn skeuo-btn" onClick={() => setShowCreate(false)}>Cancel</button>
                        <button className="btn skeuo-btn-primary" onClick={handleCreate} disabled={creating}>{creating ? '⏳ Creating...' : 'Create Backup'}</button></div>
                </div></div>
            )}
        </div>
    );
}

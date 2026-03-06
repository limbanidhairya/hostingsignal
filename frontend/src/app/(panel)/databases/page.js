'use client';
import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

export default function DatabasesPage() {
    const { showToast, ToastContainer } = useToast();
    const [dbs, setDbs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [newName, setNewName] = useState('');
    const [newUser, setNewUser] = useState('');
    const [newPass, setNewPass] = useState('');
    const [creating, setCreating] = useState(false);

    useEffect(() => { loadDbs(); }, []);

    async function loadDbs() {
        try { const data = await api.getDatabases(); setDbs(Array.isArray(data) ? data : []); }
        catch { showToast('Failed to load databases', 'error'); }
        finally { setLoading(false); }
    }

    async function handleCreate() {
        if (!newName) { showToast('Enter a database name', 'error'); return; }
        setCreating(true);
        try {
            const result = await api.createDatabase(newName, newUser || undefined, newPass || undefined);
            showToast(`Database ${newName} created! User: ${result.user}, Pass: ${result.password}`, 'success');
            setShowCreate(false); setNewName(''); setNewUser(''); setNewPass('');
            loadDbs();
        } catch (e) { showToast('Failed: ' + e.message, 'error'); }
        finally { setCreating(false); }
    }

    async function handleDelete(name, user) {
        if (!confirm(`Delete database ${name}?`)) return;
        try { await api.deleteDatabase(name, user); showToast(`${name} deleted`, 'success'); loadDbs(); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    if (loading) return <div className="animate-fade" style={{ padding: 60, textAlign: 'center' }}><div className="stat-value">⏳</div><p>Loading databases...</p></div>;

    return (
        <div className="animate-fade">
            <ToastContainer />
            <div className="page-header">
                <div><h1 className="glow-text">Databases</h1><p>Manage MariaDB databases and users</p></div>
                <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                    <button className="btn skeuo-btn">🔧 phpMyAdmin</button>
                    <button className="btn skeuo-btn-primary" onClick={() => setShowCreate(true)}>+ Create Database</button>
                </div>
            </div>

            <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                <div className="stat-card blue clay-card" style={{ background: 'transparent' }}><div className="stat-icon blue">🗄️</div><div className="stat-content"><div className="stat-value glow-text">{dbs.length}</div><div className="stat-label">Databases</div></div></div>
                <div className="stat-card purple clay-card" style={{ background: 'transparent' }}><div className="stat-icon purple">👤</div><div className="stat-content"><div className="stat-value glow-text">{dbs.length}</div><div className="stat-label">Database Users</div></div></div>
                <div className="stat-card orange clay-card" style={{ background: 'transparent' }}><div className="stat-icon orange">💾</div><div className="stat-content"><div className="stat-value glow-text">{dbs.reduce((a, d) => a + parseFloat(d.size || '0'), 0).toFixed(1)} MB</div><div className="stat-label">Total Size</div></div></div>
            </div>

            <div className="table-container liquid-glass">
                <table><thead><tr><th>Database</th><th>Size</th><th>Tables</th><th>User</th><th>Actions</th></tr></thead>
                    <tbody>{dbs.map((db, i) => (
                        <tr key={i}>
                            <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-md)', background: 'var(--accent-blue-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>🗄️</div>
                                <div style={{ fontWeight: 600, fontFamily: 'monospace' }}>{db.name}</div>
                            </div></td>
                            <td style={{ fontWeight: 600 }}>{db.size}</td>
                            <td>{db.tables}</td>
                            <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{db.user || '-'}</td>
                            <td><div style={{ display: 'flex', gap: 6 }}>
                                <button className="btn btn-sm btn-secondary">phpMyAdmin</button>
                                <button className="btn btn-sm btn-danger" onClick={() => handleDelete(db.name, db.user)}>Delete</button>
                            </div></td>
                        </tr>
                    ))}</tbody></table>
            </div>

            {showCreate && (
                <div className="modal-overlay" onClick={() => setShowCreate(false)}><div className="modal liquid-glass" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h2 className="modal-title glow-text">Create Database</h2><button className="modal-close" onClick={() => setShowCreate(false)}>✕</button></div>
                    <div className="modal-body">
                        <div className="form-group"><label className="form-label">Database Name</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="my_database" value={newName} onChange={e => setNewName(e.target.value)} /></div>
                        <div className="alert alert-info">ℹ️ A database user will be auto-created. Password will be shown after creation.</div>
                        <div className="form-group"><label className="form-label">Username (optional)</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="Auto-generated if empty" value={newUser} onChange={e => setNewUser(e.target.value)} /></div>
                        <div className="form-group"><label className="form-label">Password (optional)</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} type="password" placeholder="Auto-generated if empty" value={newPass} onChange={e => setNewPass(e.target.value)} /></div>
                    </div>
                    <div className="modal-footer"><button className="btn skeuo-btn" onClick={() => setShowCreate(false)}>Cancel</button>
                        <button className="btn skeuo-btn-primary" onClick={handleCreate} disabled={creating}>{creating ? '⏳ Creating...' : 'Create Database'}</button></div>
                </div></div>
            )}
        </div>
    );
}

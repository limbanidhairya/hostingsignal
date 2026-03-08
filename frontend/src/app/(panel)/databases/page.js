'use client';
import { useState } from 'react';

export default function DatabasesPage() {
    const [databases, setDatabases] = useState([
        { name: 'wordpress_db', user: 'wp_user', size: '142 MB', engine: 'MariaDB', created: '2024-12-01' },
        { name: 'nextcloud_db', user: 'nc_user', size: '328 MB', engine: 'MariaDB', created: '2025-01-10' },
    ]);
    const [showModal, setShowModal] = useState(false);
    const [newDb, setNewDb] = useState({ name: '', username: '', password: '' });

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <div><h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Databases</h2><p style={{ fontSize: 14, color: 'var(--hs-text-muted)', marginTop: 4 }}>{databases.length} databases</p></div>
                <div style={{ display: 'flex', gap: 8 }}>
                    <button className="hs-btn hs-btn-secondary hs-btn-sm">phpMyAdmin</button>
                    <button className="hs-btn hs-btn-primary" onClick={() => setShowModal(true)}>+ Create Database</button>
                </div>
            </div>
            <div className="hs-card" style={{ padding: 0, overflow: 'hidden' }}>
                <table className="hs-table">
                    <thead><tr><th>Database</th><th>User</th><th>Size</th><th>Engine</th><th>Created</th><th>Actions</th></tr></thead>
                    <tbody>
                        {databases.map(db => (
                            <tr key={db.name}>
                                <td style={{ fontWeight: 550 }}>🗄️ {db.name}</td>
                                <td style={{ fontFamily: 'monospace', color: 'var(--hs-text-secondary)' }}>{db.user}</td>
                                <td style={{ color: 'var(--hs-text-muted)' }}>{db.size}</td>
                                <td><span className="hs-badge info">{db.engine}</span></td>
                                <td style={{ color: 'var(--hs-text-muted)' }}>{db.created}</td>
                                <td><div style={{ display: 'flex', gap: 6 }}><button className="hs-btn hs-btn-secondary hs-btn-sm">Manage</button><button className="hs-btn hs-btn-danger hs-btn-sm">Drop</button></div></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            {showModal && (
                <div className="hs-modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="hs-modal" onClick={e => e.stopPropagation()}>
                        <h3 className="hs-modal-title">Create Database</h3>
                        <div className="hs-input-group"><label>Database Name</label><input className="hs-input" placeholder="my_database" value={newDb.name} onChange={e => setNewDb({ ...newDb, name: e.target.value })} /></div>
                        <div className="hs-input-group"><label>Username</label><input className="hs-input" placeholder="db_user" value={newDb.username} onChange={e => setNewDb({ ...newDb, username: e.target.value })} /></div>
                        <div className="hs-input-group"><label>Password</label><input className="hs-input" type="password" placeholder="Strong password" value={newDb.password} onChange={e => setNewDb({ ...newDb, password: e.target.value })} /></div>
                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 24 }}>
                            <button className="hs-btn hs-btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                            <button className="hs-btn hs-btn-primary" onClick={() => { setDatabases(prev => [...prev, { name: newDb.name, user: newDb.username, size: '0 MB', engine: 'MariaDB', created: new Date().toISOString().split('T')[0] }]); setShowModal(false); }}>Create</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

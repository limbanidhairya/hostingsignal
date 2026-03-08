'use client';
import { useState, useEffect } from 'react';

export default function WebsitesPage() {
    const [websites, setWebsites] = useState([]);
    const [showModal, setShowModal] = useState(false);
    const [newSite, setNewSite] = useState({ domain: '', php_version: '8.2', enable_ssl: true });

    useEffect(() => {
        // Mock data for development
        setWebsites([
            { domain: 'example.com', status: 'active', ssl: true, php: '8.2', disk: '245 MB', created: '2024-12-01' },
            { domain: 'blog.example.com', status: 'active', ssl: true, php: '8.1', disk: '128 MB', created: '2024-12-15' },
            { domain: 'shop.mysite.io', status: 'suspended', ssl: false, php: '8.2', disk: '512 MB', created: '2025-01-10' },
        ]);
    }, []);

    const handleCreate = () => {
        if (!newSite.domain) return;
        setWebsites(prev => [...prev, { domain: newSite.domain, status: 'active', ssl: newSite.enable_ssl, php: newSite.php_version, disk: '0 MB', created: new Date().toISOString().split('T')[0] }]);
        setShowModal(false);
        setNewSite({ domain: '', php_version: '8.2', enable_ssl: true });
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <div>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Your Websites</h2>
                    <p style={{ fontSize: 14, color: 'var(--hs-text-muted)', marginTop: 4 }}>{websites.length} websites hosted</p>
                </div>
                <button className="hs-btn hs-btn-primary" onClick={() => setShowModal(true)}>+ Create Website</button>
            </div>

            <div className="hs-card" style={{ padding: 0, overflow: 'hidden' }}>
                <table className="hs-table">
                    <thead>
                        <tr>
                            <th>Domain</th>
                            <th>Status</th>
                            <th>SSL</th>
                            <th>PHP</th>
                            <th>Disk Usage</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {websites.map((site) => (
                            <tr key={site.domain}>
                                <td style={{ fontWeight: 550, color: 'var(--hs-text-primary)' }}>
                                    🌐 {site.domain}
                                </td>
                                <td>
                                    <span className={`hs-badge ${site.status === 'active' ? 'success' : 'warning'}`}>
                                        {site.status}
                                    </span>
                                </td>
                                <td>
                                    <span className={`hs-badge ${site.ssl ? 'success' : 'error'}`}>
                                        {site.ssl ? '🔒 Active' : '⚠️ None'}
                                    </span>
                                </td>
                                <td style={{ color: 'var(--hs-text-muted)' }}>{site.php}</td>
                                <td style={{ color: 'var(--hs-text-muted)' }}>{site.disk}</td>
                                <td style={{ color: 'var(--hs-text-muted)' }}>{site.created}</td>
                                <td>
                                    <div style={{ display: 'flex', gap: 6 }}>
                                        <button className="hs-btn hs-btn-secondary hs-btn-sm">Manage</button>
                                        <button className="hs-btn hs-btn-danger hs-btn-sm">Delete</button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Create Website Modal */}
            {showModal && (
                <div className="hs-modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="hs-modal" onClick={e => e.stopPropagation()}>
                        <h3 className="hs-modal-title">Create New Website</h3>
                        <div className="hs-input-group">
                            <label>Domain Name</label>
                            <input className="hs-input" type="text" placeholder="example.com" value={newSite.domain} onChange={e => setNewSite({ ...newSite, domain: e.target.value })} />
                        </div>
                        <div className="hs-input-group">
                            <label>PHP Version</label>
                            <select className="hs-input hs-select" value={newSite.php_version} onChange={e => setNewSite({ ...newSite, php_version: e.target.value })}>
                                <option value="8.2">PHP 8.2</option>
                                <option value="8.1">PHP 8.1</option>
                                <option value="8.0">PHP 8.0</option>
                            </select>
                        </div>
                        <div className="hs-input-group">
                            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                                <input type="checkbox" checked={newSite.enable_ssl} onChange={e => setNewSite({ ...newSite, enable_ssl: e.target.checked })} />
                                Enable SSL (Let&apos;s Encrypt)
                            </label>
                        </div>
                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 24 }}>
                            <button className="hs-btn hs-btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                            <button className="hs-btn hs-btn-primary" onClick={handleCreate}>Create Website</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

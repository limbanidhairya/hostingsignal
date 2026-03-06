'use client';
import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

export default function EmailPage() {
    const { showToast, ToastContainer } = useToast();
    const [accounts, setAccounts] = useState([]);
    const [aliases, setAliases] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('accounts');
    const [showCreate, setShowCreate] = useState(false);
    const [showAlias, setShowAlias] = useState(false);
    const [newEmail, setNewEmail] = useState('');
    const [newPass, setNewPass] = useState('');
    const [newQuota, setNewQuota] = useState(1024);
    const [aliasFrom, setAliasFrom] = useState('');
    const [aliasTo, setAliasTo] = useState('');
    const [creating, setCreating] = useState(false);

    useEffect(() => { loadData(); }, []);

    async function loadData() {
        try {
            const [accts, als] = await Promise.all([api.getEmailAccounts(), api.getEmailAliases()]);
            setAccounts(Array.isArray(accts) ? accts : []);
            setAliases(Array.isArray(als) ? als : []);
        } catch { showToast('Failed to load email data', 'error'); }
        finally { setLoading(false); }
    }

    async function handleCreate() {
        if (!newEmail || !newPass) { showToast('Fill all fields', 'error'); return; }
        setCreating(true);
        try {
            await api.createEmailAccount(newEmail, newPass, newQuota);
            showToast(`Email ${newEmail} created!`, 'success');
            setShowCreate(false); setNewEmail(''); setNewPass('');
            loadData();
        } catch (e) { showToast('Failed: ' + e.message, 'error'); }
        finally { setCreating(false); }
    }

    async function handleDelete(email) {
        if (!confirm(`Delete ${email}?`)) return;
        try { await api.deleteEmailAccount(email); showToast(`${email} deleted`, 'success'); loadData(); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    async function handleAddAlias() {
        if (!aliasFrom || !aliasTo) { showToast('Fill all fields', 'error'); return; }
        try { await api.createEmailAlias(aliasFrom, aliasTo); showToast('Alias created', 'success'); setShowAlias(false); setAliasFrom(''); setAliasTo(''); loadData(); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    async function handleDkim(domain) {
        try { const r = await api.setupDkim(domain); showToast('DKIM configured!', 'success'); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    if (loading) return <div className="animate-fade" style={{ padding: 60, textAlign: 'center' }}><div className="stat-value">⏳</div><p>Loading email...</p></div>;

    return (
        <div className="animate-fade">
            <ToastContainer />
            <div className="page-header">
                <div><h1 className="glow-text">Email</h1><p>Manage email accounts, forwarders, and DKIM</p></div>
                <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                    <button className="btn skeuo-btn">📬 Open Webmail</button>
                    <button className="btn skeuo-btn-primary" onClick={() => setShowCreate(true)}>+ Create Email</button>
                </div>
            </div>

            <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                <div className="stat-card purple clay-card" style={{ background: 'transparent' }}><div className="stat-icon purple">📧</div><div className="stat-content"><div className="stat-value glow-text">{accounts.length}</div><div className="stat-label">Email Accounts</div></div></div>
                <div className="stat-card green clay-card" style={{ background: 'transparent' }}><div className="stat-icon green">↗️</div><div className="stat-content"><div className="stat-value glow-text">{aliases.length}</div><div className="stat-label">Forwarders</div></div></div>
                <div className="stat-card blue clay-card" style={{ background: 'transparent' }}><div className="stat-icon blue">💾</div><div className="stat-content"><div className="stat-value glow-text">{accounts.reduce((a, c) => a + parseInt(c.used || '0'), 0)} MB</div><div className="stat-label">Total Used</div></div></div>
            </div>

            <div className="tabs">
                {['accounts', 'forwarders'].map(tab => (
                    <button key={tab} className={`tab ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)}>{tab.charAt(0).toUpperCase() + tab.slice(1)}</button>
                ))}
            </div>

            {activeTab === 'accounts' && (
                <div className="table-container liquid-glass"><table><thead><tr><th>Email Address</th><th>Status</th><th>Quota</th><th>Used</th><th>Actions</th></tr></thead>
                    <tbody>{accounts.map((a, i) => (
                        <tr key={i}>
                            <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'linear-gradient(135deg, var(--primary), var(--accent-cyan))', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 600, fontSize: 13 }}>{a.email[0].toUpperCase()}</div>
                                <div style={{ fontWeight: 600 }}>{a.email}</div>
                            </div></td>
                            <td><span className="badge badge-success badge-dot">{a.status}</span></td>
                            <td>{a.quota}</td>
                            <td>{a.used}</td>
                            <td><div style={{ display: 'flex', gap: 6 }}>
                                <button className="btn btn-sm skeuo-btn" onClick={() => handleDkim(a.email.split('@')[1])}>🔑 DKIM</button>
                                <button className="btn btn-sm btn-danger skeuo-btn" style={{ background: 'var(--accent-red)' }} onClick={() => handleDelete(a.email)}>Delete</button>
                            </div></td>
                        </tr>
                    ))}</tbody></table></div>
            )}

            {activeTab === 'forwarders' && (
                <div className="table-container liquid-glass">
                    <div className="table-header"><span className="table-title glow-text">Email Forwarders</span><button className="btn btn-sm skeuo-btn-primary" onClick={() => setShowAlias(true)}>+ Add Forwarder</button></div>
                    <table><thead><tr><th>From</th><th>To</th><th>Actions</th></tr></thead>
                        <tbody>{aliases.map((f, i) => (
                            <tr key={i}><td style={{ fontWeight: 600 }}>{f.source}</td><td>{f.destination}</td>
                                <td><button className="btn btn-sm btn-danger skeuo-btn" style={{ background: 'var(--accent-red)' }}>Delete</button></td></tr>
                        ))}</tbody></table></div>
            )}

            {showCreate && (
                <div className="modal-overlay" onClick={() => setShowCreate(false)}><div className="modal liquid-glass" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h2 className="modal-title glow-text">Create Email Account</h2><button className="modal-close" onClick={() => setShowCreate(false)}>✕</button></div>
                    <div className="modal-body">
                        <div className="form-group"><label className="form-label">Email Address</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="user@domain.com" value={newEmail} onChange={e => setNewEmail(e.target.value)} /></div>
                        <div className="form-group"><label className="form-label">Password</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} type="password" placeholder="Strong password" value={newPass} onChange={e => setNewPass(e.target.value)} /></div>
                        <div className="form-group"><label className="form-label">Quota (MB)</label>
                            <select className="form-input form-select" style={{ background: 'rgba(0,0,0,0.2)' }} value={newQuota} onChange={e => setNewQuota(Number(e.target.value))}><option value={256} style={{ background: 'black' }}>256 MB</option><option value={512} style={{ background: 'black' }}>512 MB</option><option value={1024} style={{ background: 'black' }}>1 GB</option><option value={2048} style={{ background: 'black' }}>2 GB</option><option value={5120} style={{ background: 'black' }}>5 GB</option></select></div>
                    </div>
                    <div className="modal-footer"><button className="btn skeuo-btn" onClick={() => setShowCreate(false)}>Cancel</button><button className="btn skeuo-btn-primary" onClick={handleCreate} disabled={creating}>{creating ? '⏳ Creating...' : 'Create Email'}</button></div>
                </div></div>
            )}

            {showAlias && (
                <div className="modal-overlay" onClick={() => setShowAlias(false)}><div className="modal liquid-glass" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h2 className="modal-title glow-text">Add Forwarder</h2><button className="modal-close" onClick={() => setShowAlias(false)}>✕</button></div>
                    <div className="modal-body">
                        <div className="form-group"><label className="form-label">Forward From</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="alias@domain.com" value={aliasFrom} onChange={e => setAliasFrom(e.target.value)} /></div>
                        <div className="form-group"><label className="form-label">Forward To</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="destination@domain.com" value={aliasTo} onChange={e => setAliasTo(e.target.value)} /></div>
                    </div>
                    <div className="modal-footer"><button className="btn skeuo-btn" onClick={() => setShowAlias(false)}>Cancel</button><button className="btn skeuo-btn-primary" onClick={handleAddAlias}>Create Forwarder</button></div>
                </div></div>
            )}
        </div>
    );
}

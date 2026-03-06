'use client';
import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

export default function DomainsPage() {
    const { showToast, ToastContainer } = useToast();
    const [zones, setZones] = useState([]);
    const [sites, setSites] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showAdd, setShowAdd] = useState(false);
    const [newDomain, setNewDomain] = useState('');

    useEffect(() => { loadData(); }, []);

    async function loadData() {
        try {
            const [z, s] = await Promise.all([api.getDnsZones(), api.getWebsites()]);
            setZones(Array.isArray(z) ? z : []);
            setSites(Array.isArray(s) ? s : []);
        } catch { showToast('Failed to load domains', 'error'); }
        finally { setLoading(false); }
    }

    async function handleAdd() {
        if (!newDomain) { showToast('Enter a domain', 'error'); return; }
        try {
            // Create website + DNS zone
            await Promise.all([api.createWebsite(newDomain), api.createDnsZone(newDomain)]);
            showToast(`${newDomain} added with DNS zone`, 'success');
            setShowAdd(false); setNewDomain('');
            loadData();
        } catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    async function handleSSL(domain) {
        try { await api.issueSSL(domain); showToast(`SSL issued for ${domain}`, 'success'); loadData(); }
        catch (e) { showToast(e.message, 'error'); }
    }

    async function handleDelete(domain) {
        if (!confirm(`Delete ${domain} and its DNS zone?`)) return;
        try { await Promise.all([api.deleteWebsite(domain).catch(() => { }), api.deleteDnsZone(domain).catch(() => { })]); showToast(`${domain} removed`, 'success'); loadData(); }
        catch (e) { showToast(e.message, 'error'); }
    }

    if (loading) return <div className="animate-fade" style={{ padding: 60, textAlign: 'center' }}><div className="stat-value">⏳</div><p>Loading domains...</p></div>;

    // Merge sites and zones into unified domain list
    const allDomains = new Map();
    sites.forEach(s => allDomains.set(s.domain, { domain: s.domain, website: true, dns: false, ssl: s.ssl, php: s.php, status: s.status }));
    zones.forEach(z => { const d = z.domain || z; if (allDomains.has(d)) allDomains.get(d).dns = true; else allDomains.set(d, { domain: d, website: false, dns: true, ssl: false, status: 'dns-only' }); });
    const domainList = Array.from(allDomains.values());

    return (
        <div className="animate-fade">
            <ToastContainer />
            <div className="page-header"><div><h1 className="glow-text">Domains</h1><p>Manage all domains, DNS zones, and SSL</p></div>
                <button className="btn skeuo-btn-primary" onClick={() => setShowAdd(true)}>+ Add Domain</button></div>

            <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
                <div className="stat-card blue clay-card" style={{ background: 'transparent' }}><div className="stat-icon blue">🌐</div><div className="stat-content"><div className="stat-value glow-text">{domainList.length}</div><div className="stat-label">Total Domains</div></div></div>
                <div className="stat-card green clay-card" style={{ background: 'transparent' }}><div className="stat-icon green">✅</div><div className="stat-content"><div className="stat-value glow-text">{domainList.filter(d => d.website).length}</div><div className="stat-label">With Websites</div></div></div>
                <div className="stat-card purple clay-card" style={{ background: 'transparent' }}><div className="stat-icon purple">🌍</div><div className="stat-content"><div className="stat-value glow-text">{domainList.filter(d => d.dns).length}</div><div className="stat-label">DNS Zones</div></div></div>
                <div className="stat-card orange clay-card" style={{ background: 'transparent' }}><div className="stat-icon orange">🔒</div><div className="stat-content"><div className="stat-value glow-text">{domainList.filter(d => d.ssl).length}</div><div className="stat-label">SSL Active</div></div></div>
            </div>

            <div className="table-container liquid-glass"><table><thead><tr><th>Domain</th><th>Website</th><th>DNS Zone</th><th>SSL</th><th>Status</th><th>Actions</th></tr></thead>
                <tbody>{domainList.map((d, i) => (
                    <tr key={i}>
                        <td><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-md)', background: 'var(--primary-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>🌐</div>
                            <div style={{ fontWeight: 600 }}>{d.domain}</div>
                        </div></td>
                        <td>{d.website ? <span className="badge badge-success">✓</span> : <span className="badge badge-muted">—</span>}</td>
                        <td>{d.dns ? <span className="badge badge-success">✓</span> : <span className="badge badge-muted">—</span>}</td>
                        <td>{d.ssl ? <span className="badge badge-success">🔒</span> : <button className="btn btn-sm skeuo-btn" onClick={() => handleSSL(d.domain)}>Issue</button>}</td>
                        <td><span className={`badge ${d.status === 'online' ? 'badge-success' : d.status === 'dns-only' ? 'badge-info' : 'badge-warning'} badge-dot`}>{d.status}</span></td>
                        <td><button className="btn btn-sm btn-danger skeuo-btn" style={{ background: 'var(--accent-red)' }} onClick={() => handleDelete(d.domain)}>Delete</button></td>
                    </tr>
                ))}</tbody></table></div>

            {showAdd && (
                <div className="modal-overlay" onClick={() => setShowAdd(false)}><div className="modal liquid-glass" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h2 className="modal-title glow-text">Add Domain</h2><button className="modal-close" onClick={() => setShowAdd(false)}>✕</button></div>
                    <div className="modal-body">
                        <div className="form-group"><label className="form-label">Domain Name</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="example.com" value={newDomain} onChange={e => setNewDomain(e.target.value)} /></div>
                        <div className="alert alert-info">ℹ️ This will create both a website and a DNS zone for the domain.</div>
                    </div>
                    <div className="modal-footer"><button className="btn skeuo-btn" onClick={() => setShowAdd(false)}>Cancel</button><button className="btn skeuo-btn-primary" onClick={handleAdd}>Add Domain</button></div>
                </div></div>
            )}
        </div>
    );
}

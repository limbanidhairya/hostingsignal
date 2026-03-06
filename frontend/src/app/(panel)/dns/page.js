'use client';
import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

export default function DNSPage() {
    const { showToast, ToastContainer } = useToast();
    const [zones, setZones] = useState([]);
    const [selectedZone, setSelectedZone] = useState(null);
    const [records, setRecords] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showAddZone, setShowAddZone] = useState(false);
    const [showAddRecord, setShowAddRecord] = useState(false);
    const [newZone, setNewZone] = useState('');
    const [recName, setRecName] = useState('');
    const [recType, setRecType] = useState('A');
    const [recContent, setRecContent] = useState('');
    const [recTTL, setRecTTL] = useState(3600);

    useEffect(() => { loadZones(); }, []);

    async function loadZones() {
        try { const data = await api.getDnsZones(); setZones(Array.isArray(data) ? data : []); }
        catch { showToast('Failed to load DNS zones', 'error'); }
        finally { setLoading(false); }
    }

    async function selectZone(domain) {
        setSelectedZone(domain);
        try { const z = await api.getDnsZone(domain); setRecords(z.records || []); }
        catch { showToast('Failed to load records', 'error'); }
    }

    async function handleAddZone() {
        if (!newZone) return;
        try { await api.createDnsZone(newZone); showToast(`Zone ${newZone} created`, 'success'); setShowAddZone(false); setNewZone(''); loadZones(); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    async function handleAddRecord() {
        if (!recName || !recContent) { showToast('Fill all fields', 'error'); return; }
        try { await api.addDnsRecord(selectedZone, recName, recType, recContent, recTTL); showToast('Record added', 'success'); setShowAddRecord(false); selectZone(selectedZone); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    async function handleDeleteRecord(name, type) {
        try { await api.deleteDnsRecord(selectedZone, name, type); showToast('Record deleted', 'success'); selectZone(selectedZone); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    async function handleDeleteZone(domain) {
        if (!confirm(`Delete zone ${domain}?`)) return;
        try { await api.deleteDnsZone(domain); showToast(`Zone ${domain} deleted`, 'success'); setSelectedZone(null); setRecords([]); loadZones(); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    if (loading) return <div className="animate-fade" style={{ padding: 60, textAlign: 'center' }}><div className="stat-value">⏳</div><p>Loading DNS zones...</p></div>;

    return (
        <div className="animate-fade">
            <ToastContainer />
            <div className="page-header">
                <div><h1 className="glow-text">DNS Management</h1><p>Manage DNS zones and records (PowerDNS)</p></div>
                <button className="btn skeuo-btn-primary" onClick={() => setShowAddZone(true)}>+ Add Zone</button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 'var(--space-lg)' }}>
                {/* Zone List */}
                <div className="card liquid-glass" style={{ padding: 0 }}>
                    <div style={{ padding: 'var(--space-md) var(--space-lg)', borderBottom: '1px solid rgba(255,255,255,0.05)', fontWeight: 600 }}>DNS Zones ({zones.length})</div>
                    {zones.map((z, i) => (
                        <div key={i} onClick={() => selectZone(z.domain || z)} style={{
                            padding: 'var(--space-sm) var(--space-lg)', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            background: selectedZone === (z.domain || z) ? 'rgba(0, 195, 255, 0.1)' : 'transparent', borderBottom: '1px solid rgba(255,255,255,0.05)',
                        }}>
                            <span style={{ fontWeight: 500 }} className={selectedZone === (z.domain || z) ? 'glow-text' : ''}>{z.domain || z}</span>
                            <button className="btn btn-sm btn-danger skeuo-btn" onClick={e => { e.stopPropagation(); handleDeleteZone(z.domain || z); }} style={{ padding: '2px 8px', fontSize: 11, background: 'var(--accent-red)' }}>✕</button>
                        </div>
                    ))}
                    {zones.length === 0 && <div style={{ padding: 'var(--space-lg)', textAlign: 'center', color: 'var(--text-muted)' }}>No zones</div>}
                </div>

                {/* Records */}
                <div>
                    {selectedZone ? (
                        <div className="liquid-glass" style={{ padding: 'var(--space-lg)', borderRadius: 'var(--radius-lg)' }}>
                            <div style={{ marginBottom: 'var(--space-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h3 className="glow-text">Records for {selectedZone}</h3>
                                <button className="btn btn-sm skeuo-btn-primary" onClick={() => setShowAddRecord(true)}>+ Add Record</button>
                            </div>
                            <div className="table-container" style={{ background: 'transparent' }}><table><thead><tr><th>Name</th><th>Type</th><th>Content</th><th>TTL</th><th>Actions</th></tr></thead>
                                <tbody>{records.map((r, i) => (
                                    <tr key={i}>
                                        <td style={{ fontWeight: 600 }}>{r.name}</td>
                                        <td><span className={`badge ${r.type === 'A' ? 'badge-success' : r.type === 'MX' ? 'badge-warning' : r.type === 'CNAME' ? 'badge-info' : 'badge-purple'}`}>{r.type}</span></td>
                                        <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{r.content}</td>
                                        <td>{r.ttl}</td>
                                        <td><button className="btn btn-sm btn-danger skeuo-btn" style={{ background: 'var(--accent-red)' }} onClick={() => handleDeleteRecord(r.name, r.type)}>Delete</button></td>
                                    </tr>
                                ))}</tbody></table></div>
                        </div>
                    ) : (
                        <div className="card liquid-glass" style={{ textAlign: 'center', padding: 'var(--space-xxl)' }}>
                            <div style={{ fontSize: 48, marginBottom: 'var(--space-md)' }}>🌍</div>
                            <h3 className="glow-text">Select a DNS Zone</h3><p style={{ color: 'var(--text-muted)' }}>Click a zone to view and manage its records.</p>
                        </div>
                    )}
                </div>
            </div>

            {showAddZone && (
                <div className="modal-overlay" onClick={() => setShowAddZone(false)}><div className="modal liquid-glass" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h2 className="modal-title glow-text">Add DNS Zone</h2><button className="modal-close" onClick={() => setShowAddZone(false)}>✕</button></div>
                    <div className="modal-body"><div className="form-group"><label className="form-label">Domain</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="example.com" value={newZone} onChange={e => setNewZone(e.target.value)} /></div></div>
                    <div className="modal-footer"><button className="btn skeuo-btn" onClick={() => setShowAddZone(false)}>Cancel</button><button className="btn skeuo-btn-primary" onClick={handleAddZone}>Create Zone</button></div>
                </div></div>
            )}

            {showAddRecord && (
                <div className="modal-overlay" onClick={() => setShowAddRecord(false)}><div className="modal liquid-glass" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h2 className="modal-title glow-text">Add DNS Record</h2><button className="modal-close" onClick={() => setShowAddRecord(false)}>✕</button></div>
                    <div className="modal-body">
                        <div className="form-group"><label className="form-label">Name</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="subdomain" value={recName} onChange={e => setRecName(e.target.value)} /></div>
                        <div className="form-group"><label className="form-label">Type</label><select className="form-input form-select" style={{ background: 'rgba(0,0,0,0.2)' }} value={recType} onChange={e => setRecType(e.target.value)}>
                            {['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'SRV', 'CAA'].map(t => <option key={t} style={{ background: 'black' }}>{t}</option>)}</select></div>
                        <div className="form-group"><label className="form-label">Content</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="IP or value" value={recContent} onChange={e => setRecContent(e.target.value)} /></div>
                        <div className="form-group"><label className="form-label">TTL</label><select className="form-input form-select" style={{ background: 'rgba(0,0,0,0.2)' }} value={recTTL} onChange={e => setRecTTL(Number(e.target.value))}>
                            <option value={300} style={{ background: 'black' }}>5 min</option><option value={3600} style={{ background: 'black' }}>1 hour</option><option value={86400} style={{ background: 'black' }}>1 day</option></select></div>
                    </div>
                    <div className="modal-footer"><button className="btn skeuo-btn" onClick={() => setShowAddRecord(false)}>Cancel</button><button className="btn skeuo-btn-primary" onClick={handleAddRecord}>Add Record</button></div>
                </div></div>
            )}
        </div>
    );
}

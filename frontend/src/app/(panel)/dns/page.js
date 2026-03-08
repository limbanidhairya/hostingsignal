'use client';
import { useState } from 'react';

const RECORD_TYPES = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'SRV', 'CAA'];

export default function DNSPage() {
    const [zone, setZone] = useState('example.com');
    const [records, setRecords] = useState([
        { id: 1, type: 'A', name: '@', value: '203.0.113.10', ttl: 3600 },
        { id: 2, type: 'CNAME', name: 'www', value: 'example.com', ttl: 3600 },
        { id: 3, type: 'MX', name: '@', value: 'mail.example.com', ttl: 3600, priority: 10 },
        { id: 4, type: 'TXT', name: '@', value: 'v=spf1 include:_spf.google.com ~all', ttl: 3600 },
        { id: 5, type: 'NS', name: '@', value: 'ns1.hostingsignal.com', ttl: 86400 },
        { id: 6, type: 'NS', name: '@', value: 'ns2.hostingsignal.com', ttl: 86400 },
    ]);
    const [showAdd, setShowAdd] = useState(false);
    const [newRec, setNewRec] = useState({ type: 'A', name: '', value: '', ttl: 3600 });

    const addRecord = () => {
        setRecords(prev => [...prev, { ...newRec, id: Date.now() }]);
        setShowAdd(false);
        setNewRec({ type: 'A', name: '', value: '', ttl: 3600 });
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <div><h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>DNS Zone Editor</h2><p style={{ fontSize: 14, color: 'var(--hs-text-muted)', marginTop: 4 }}>Zone: {zone} — {records.length} records</p></div>
                <div style={{ display: 'flex', gap: 8 }}>
                    <button className="hs-btn hs-btn-secondary hs-btn-sm">Import</button>
                    <button className="hs-btn hs-btn-secondary hs-btn-sm">Export</button>
                    <button className="hs-btn hs-btn-primary hs-btn-sm" onClick={() => setShowAdd(!showAdd)}>+ Add Record</button>
                </div>
            </div>
            {showAdd && (
                <div className="hs-card" style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        <select className="hs-input hs-select" style={{ width: 100 }} value={newRec.type} onChange={e => setNewRec({ ...newRec, type: e.target.value })}>
                            {RECORD_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                        </select>
                        <input className="hs-input" style={{ width: 150 }} placeholder="Name" value={newRec.name} onChange={e => setNewRec({ ...newRec, name: e.target.value })} />
                        <input className="hs-input" style={{ flex: 1, minWidth: 200 }} placeholder="Value" value={newRec.value} onChange={e => setNewRec({ ...newRec, value: e.target.value })} />
                        <input className="hs-input" style={{ width: 80 }} type="number" placeholder="TTL" value={newRec.ttl} onChange={e => setNewRec({ ...newRec, ttl: parseInt(e.target.value) })} />
                        <button className="hs-btn hs-btn-primary hs-btn-sm" onClick={addRecord}>Add</button>
                    </div>
                </div>
            )}
            <div className="hs-card" style={{ padding: 0, overflow: 'hidden' }}>
                <table className="hs-table">
                    <thead><tr><th>Type</th><th>Name</th><th>Value</th><th>TTL</th><th>Actions</th></tr></thead>
                    <tbody>
                        {records.map(r => (
                            <tr key={r.id}>
                                <td><span className="hs-badge info">{r.type}</span></td>
                                <td style={{ fontFamily: 'monospace', fontWeight: 550 }}>{r.name}</td>
                                <td style={{ fontFamily: 'monospace', color: 'var(--hs-text-secondary)' }}>{r.value}</td>
                                <td style={{ color: 'var(--hs-text-muted)' }}>{r.ttl}s</td>
                                <td><div style={{ display: 'flex', gap: 6 }}><button className="hs-btn hs-btn-secondary hs-btn-sm">Edit</button><button className="hs-btn hs-btn-danger hs-btn-sm" onClick={() => setRecords(prev => prev.filter(x => x.id !== r.id))}>Delete</button></div></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

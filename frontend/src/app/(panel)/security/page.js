'use client';
import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

export default function SecurityPage() {
    const { showToast, ToastContainer } = useToast();
    const [certs, setCerts] = useState([]);
    const [rules, setRules] = useState([]);
    const [blocked, setBlocked] = useState([]);
    const [fwStatus, setFwStatus] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('ssl');
    const [showIssueSSL, setShowIssueSSL] = useState(false);
    const [showPortModal, setShowPortModal] = useState(false);
    const [showBlockModal, setShowBlockModal] = useState(false);
    const [sslDomain, setSSLDomain] = useState('');
    const [sslWildcard, setSSLWildcard] = useState(false);
    const [portNum, setPortNum] = useState('');
    const [portProto, setPortProto] = useState('tcp');
    const [blockIP, setBlockIP] = useState('');
    const [blockReason, setBlockReason] = useState('');

    useEffect(() => { loadAll(); }, []);

    async function loadAll() {
        try {
            const [c, r, b, s] = await Promise.all([api.getSSLCertificates(), api.getFirewallRules(), api.getBlockedIPs(), api.getFirewallStatus()]);
            setCerts(Array.isArray(c) ? c : []);
            setRules(Array.isArray(r) ? r : []);
            setBlocked(Array.isArray(b) ? b : []);
            setFwStatus(s);
        } catch { showToast('Failed to load security data', 'error'); }
        finally { setLoading(false); }
    }

    async function handleIssueSSL() {
        if (!sslDomain) return;
        try { await api.issueSSL(sslDomain, 'admin@hostingsignal.com', sslWildcard); showToast(`SSL issued for ${sslDomain}`, 'success'); setShowIssueSSL(false); loadAll(); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    async function handleRenew(d) { try { await api.renewSSL(d); showToast(`SSL renewed for ${d}`, 'success'); loadAll(); } catch (e) { showToast(e.message, 'error'); } }
    async function handleRevoke(d) { if (!confirm(`Revoke SSL for ${d}?`)) return; try { await api.revokeSSL(d); showToast(`SSL revoked for ${d}`, 'success'); loadAll(); } catch (e) { showToast(e.message, 'error'); } }

    async function handleOpenPort() {
        if (!portNum) return;
        try { await api.openPort(Number(portNum), portProto); showToast(`Port ${portNum}/${portProto} opened`, 'success'); setShowPortModal(false); setPortNum(''); loadAll(); }
        catch (e) { showToast(e.message, 'error'); }
    }

    async function handleClosePort(port, proto) { try { await api.closePort(port, proto); showToast(`Port ${port} closed`, 'success'); loadAll(); } catch (e) { showToast(e.message, 'error'); } }

    async function handleBlockIP() {
        if (!blockIP) return;
        try { await api.blockIP(blockIP, blockReason); showToast(`${blockIP} blocked`, 'success'); setShowBlockModal(false); setBlockIP(''); setBlockReason(''); loadAll(); }
        catch (e) { showToast(e.message, 'error'); }
    }

    async function handleUnblock(ip) { try { await api.unblockIP(ip); showToast(`${ip} unblocked`, 'success'); loadAll(); } catch (e) { showToast(e.message, 'error'); } }

    if (loading) return <div className="animate-fade" style={{ padding: 60, textAlign: 'center' }}><div className="stat-value">⏳</div><p>Loading security...</p></div>;

    return (
        <div className="animate-fade">
            <ToastContainer />
            <div className="page-header"><div><h1 className="glow-text">Security</h1><p>SSL certificates, firewall rules, and IP management</p></div></div>

            <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
                <div className="stat-card green clay-card" style={{ background: 'transparent' }}><div className="stat-icon green">🔒</div><div className="stat-content"><div className="stat-value glow-text">{certs.length}</div><div className="stat-label">SSL Certificates</div></div></div>
                <div className="stat-card blue clay-card" style={{ background: 'transparent' }}><div className="stat-icon blue">🛡️</div><div className="stat-content"><div className="stat-value glow-text">{fwStatus?.status || 'Unknown'}</div><div className="stat-label">Firewall</div></div></div>
                <div className="stat-card purple clay-card" style={{ background: 'transparent' }}><div className="stat-icon purple">🚪</div><div className="stat-content"><div className="stat-value glow-text">{rules.length}</div><div className="stat-label">Open Ports</div></div></div>
                <div className="stat-card orange clay-card" style={{ background: 'transparent' }}><div className="stat-icon orange">🚫</div><div className="stat-content"><div className="stat-value glow-text">{blocked.length}</div><div className="stat-label">Blocked IPs</div></div></div>
            </div>

            <div className="tabs">
                {['ssl', 'firewall', 'blocked'].map(t => (
                    <button key={t} className={`tab ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t)}>
                        {t === 'ssl' ? '🔒 SSL Certificates' : t === 'firewall' ? '🛡️ Firewall Rules' : '🚫 Blocked IPs'}
                    </button>
                ))}
            </div>

            {activeTab === 'ssl' && (
                <>
                    <div style={{ marginBottom: 'var(--space-md)', display: 'flex', justifyContent: 'flex-end' }}>
                        <button className="btn skeuo-btn-primary" onClick={() => setShowIssueSSL(true)}>+ Issue SSL Certificate</button>
                    </div>
                    <div className="table-container liquid-glass"><table><thead><tr><th>Domain</th><th>Status</th><th>Issuer</th><th>Expires</th><th>Actions</th></tr></thead>
                        <tbody>{certs.map((c, i) => (
                            <tr key={i}>
                                <td style={{ fontWeight: 600 }}>{c.domain}</td>
                                <td><span className={`badge ${c.status === 'valid' ? 'badge-success' : 'badge-warning'}`}>{c.status}</span></td>
                                <td>{c.issuer || "Let's Encrypt"}</td>
                                <td>{c.expiry || '-'}</td>
                                <td><div style={{ display: 'flex', gap: 6 }}>
                                    <button className="btn btn-sm skeuo-btn" onClick={() => handleRenew(c.domain)}>🔄 Renew</button>
                                    <button className="btn btn-sm btn-danger skeuo-btn" onClick={() => handleRevoke(c.domain)} style={{ background: 'var(--accent-red)' }}>Revoke</button>
                                </div></td>
                            </tr>
                        ))}</tbody></table></div>
                </>
            )}

            {activeTab === 'firewall' && (
                <>
                    <div style={{ marginBottom: 'var(--space-md)', display: 'flex', justifyContent: 'flex-end' }}>
                        <button className="btn skeuo-btn-primary" onClick={() => setShowPortModal(true)}>+ Open Port</button>
                    </div>
                    <div className="table-container liquid-glass"><table><thead><tr><th>Port</th><th>Protocol</th><th>Service</th><th>Actions</th></tr></thead>
                        <tbody>{rules.map((r, i) => (
                            <tr key={i}>
                                <td style={{ fontWeight: 600, fontFamily: 'monospace' }}>{r.port}</td>
                                <td><span className="badge badge-info">{r.protocol || 'tcp'}</span></td>
                                <td>{r.service || '-'}</td>
                                <td><button className="btn btn-sm btn-danger skeuo-btn" style={{ background: 'var(--accent-red)' }} onClick={() => handleClosePort(r.port, r.protocol || 'tcp')}>Close</button></td>
                            </tr>
                        ))}</tbody></table></div>
                </>
            )}

            {activeTab === 'blocked' && (
                <>
                    <div style={{ marginBottom: 'var(--space-md)', display: 'flex', justifyContent: 'flex-end' }}>
                        <button className="btn skeuo-btn-primary" onClick={() => setShowBlockModal(true)}>+ Block IP</button>
                    </div>
                    <div className="table-container liquid-glass"><table><thead><tr><th>IP Address</th><th>Reason</th><th>Blocked At</th><th>Actions</th></tr></thead>
                        <tbody>{blocked.map((b, i) => (
                            <tr key={i}>
                                <td style={{ fontWeight: 600, fontFamily: 'monospace' }}>{b.ip}</td>
                                <td>{b.reason || '-'}</td>
                                <td>{b.blocked_at || '-'}</td>
                                <td><button className="btn btn-sm skeuo-btn" onClick={() => handleUnblock(b.ip)}>Unblock</button></td>
                            </tr>
                        ))}</tbody></table></div>
                </>
            )}

            {showIssueSSL && (
                <div className="modal-overlay" onClick={() => setShowIssueSSL(false)}><div className="modal liquid-glass" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h2 className="modal-title glow-text">Issue SSL Certificate</h2><button className="modal-close" onClick={() => setShowIssueSSL(false)}>✕</button></div>
                    <div className="modal-body">
                        <div className="form-group"><label className="form-label">Domain</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="example.com" value={sslDomain} onChange={e => setSSLDomain(e.target.value)} /></div>
                        <div className="form-group"><label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                            <input type="checkbox" checked={sslWildcard} onChange={e => setSSLWildcard(e.target.checked)} /><span>Wildcard certificate (*.domain.com)</span></label></div>
                    </div>
                    <div className="modal-footer"><button className="btn skeuo-btn" onClick={() => setShowIssueSSL(false)}>Cancel</button><button className="btn skeuo-btn-primary" onClick={handleIssueSSL}>Issue Certificate</button></div>
                </div></div>
            )}

            {showPortModal && (
                <div className="modal-overlay" onClick={() => setShowPortModal(false)}><div className="modal liquid-glass" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h2 className="modal-title glow-text">Open Port</h2><button className="modal-close" onClick={() => setShowPortModal(false)}>✕</button></div>
                    <div className="modal-body">
                        <div className="form-group"><label className="form-label">Port Number</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} type="number" placeholder="8080" value={portNum} onChange={e => setPortNum(e.target.value)} /></div>
                        <div className="form-group"><label className="form-label">Protocol</label><select className="form-input form-select" style={{ background: 'rgba(0,0,0,0.2)' }} value={portProto} onChange={e => setPortProto(e.target.value)}><option style={{ background: 'black' }}>tcp</option><option style={{ background: 'black' }}>udp</option></select></div>
                    </div>
                    <div className="modal-footer"><button className="btn skeuo-btn" onClick={() => setShowPortModal(false)}>Cancel</button><button className="btn skeuo-btn-primary" onClick={handleOpenPort}>Open Port</button></div>
                </div></div>
            )}

            {showBlockModal && (
                <div className="modal-overlay" onClick={() => setShowBlockModal(false)}><div className="modal liquid-glass" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h2 className="modal-title glow-text">Block IP Address</h2><button className="modal-close" onClick={() => setShowBlockModal(false)}>✕</button></div>
                    <div className="modal-body">
                        <div className="form-group"><label className="form-label">IP Address</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="192.168.1.100" value={blockIP} onChange={e => setBlockIP(e.target.value)} /></div>
                        <div className="form-group"><label className="form-label">Reason (optional)</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="Brute force attempt" value={blockReason} onChange={e => setBlockReason(e.target.value)} /></div>
                    </div>
                    <div className="modal-footer"><button className="btn skeuo-btn" onClick={() => setShowBlockModal(false)}>Cancel</button><button className="btn skeuo-btn-primary" onClick={handleBlockIP}>Block IP</button></div>
                </div></div>
            )}
        </div>
    );
}

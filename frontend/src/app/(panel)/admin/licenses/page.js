'use client';
import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

const tierColors = { free: 'badge-info', pro: 'badge-purple', business: 'badge-warning', enterprise: 'badge-success' };

export default function LicensesPage() {
    const { showToast, ToastContainer } = useToast();
    const [licenses, setLicenses] = useState([]);
    const [stats, setStats] = useState(null);
    const [tiers, setTiers] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showIssue, setShowIssue] = useState(false);
    const [activeTab, setActiveTab] = useState('licenses');
    const [filterTier, setFilterTier] = useState('');
    const [search, setSearch] = useState('');

    // Form state
    const [formName, setFormName] = useState('');
    const [formEmail, setFormEmail] = useState('');
    const [formTier, setFormTier] = useState('pro');
    const [formIP, setFormIP] = useState('');
    const [formValidity, setFormValidity] = useState(12);
    const [formNotes, setFormNotes] = useState('');
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        loadAll();
    }, []);

    async function loadAll() {
        setLoading(true);
        try {
            const [lics, st, ti] = await Promise.all([
                api.getLicenses(),
                api.getLicenseStats(),
                api.getTiers(),
            ]);
            setLicenses(lics);
            setStats(st);
            setTiers(ti);
        } catch (err) {
            showToast('Failed to load licenses: ' + err.message, 'error');
        } finally {
            setLoading(false);
        }
    }

    async function handleIssue(e) {
        e.preventDefault();
        setSubmitting(true);
        try {
            const lic = await api.issueLicense({
                customer_name: formName,
                customer_email: formEmail,
                tier: formTier,
                server_ip: formIP || null,
                validity_months: formValidity,
                notes: formNotes || null,
            });
            showToast(`License ${lic.license_key} issued successfully!`, 'success');
            setShowIssue(false);
            setFormName(''); setFormEmail(''); setFormTier('pro'); setFormIP(''); setFormValidity(12); setFormNotes('');
            loadAll();
        } catch (err) {
            showToast('Failed to issue license: ' + err.message, 'error');
        } finally {
            setSubmitting(false);
        }
    }

    async function handleRevoke(lic) {
        if (!confirm(`Revoke license ${lic.license_key}? This cannot be undone.`)) return;
        try {
            await api.revokeLicense(lic.id);
            showToast(`License ${lic.license_key} revoked`, 'success');
            loadAll();
        } catch (err) {
            showToast('Failed to revoke: ' + err.message, 'error');
        }
    }

    async function handleRenew(lic) {
        try {
            await api.updateLicense(lic.id, { status: 'active', validity_months: 12 });
            showToast(`License ${lic.license_key} renewed for 12 months`, 'success');
            loadAll();
        } catch (err) {
            showToast('Failed to renew: ' + err.message, 'error');
        }
    }

    async function handleReactivate(lic) {
        try {
            await api.updateLicense(lic.id, { status: 'active' });
            showToast(`License ${lic.license_key} reactivated`, 'success');
            loadAll();
        } catch (err) {
            showToast('Failed to reactivate: ' + err.message, 'error');
        }
    }

    const filteredLicenses = licenses.filter(l => {
        if (filterTier && l.tier !== filterTier) return false;
        if (search) {
            const s = search.toLowerCase();
            return l.license_key.toLowerCase().includes(s) ||
                l.customer_name.toLowerCase().includes(s) ||
                l.customer_email.toLowerCase().includes(s);
        }
        return true;
    });

    if (loading) {
        return <div className="animate-fade" style={{ padding: 'var(--space-xl)', textAlign: 'center', color: 'var(--text-muted)' }}>Loading license data...</div>;
    }

    return (
        <div className="animate-fade">
            <ToastContainer />
            <div className="page-header">
                <div>
                    <h1>License Management</h1>
                    <p>Manage license distribution, customers, and revenue</p>
                </div>
                <button className="btn btn-primary" onClick={() => setShowIssue(true)}>+ Issue License</button>
            </div>

            {/* Revenue Stats */}
            {stats && (
                <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
                    <div className="stat-card green">
                        <div className="stat-icon green">💰</div>
                        <div className="stat-content">
                            <div className="stat-value">${stats.monthly_revenue}</div>
                            <div className="stat-label">Monthly Revenue</div>
                        </div>
                    </div>
                    <div className="stat-card purple">
                        <div className="stat-icon purple">🔑</div>
                        <div className="stat-content">
                            <div className="stat-value">{stats.total}</div>
                            <div className="stat-label">Total Licenses</div>
                        </div>
                    </div>
                    <div className="stat-card blue">
                        <div className="stat-icon blue">✅</div>
                        <div className="stat-content">
                            <div className="stat-value">{stats.active}</div>
                            <div className="stat-label">Active</div>
                        </div>
                    </div>
                    <div className="stat-card orange">
                        <div className="stat-icon orange">⚠️</div>
                        <div className="stat-content">
                            <div className="stat-value">{stats.expired + stats.suspended}</div>
                            <div className="stat-label">Expired / Suspended</div>
                        </div>
                    </div>
                </div>
            )}

            {/* Tier Cards */}
            {tiers && (
                <div style={{ marginBottom: 'var(--space-lg)' }}>
                    <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: 'var(--space-md)' }}>License Tiers</h2>
                    <div className="license-tier-grid">
                        {Object.entries(tiers).map(([key, tier]) => {
                            const tierCount = stats?.tier_breakdown?.[key] || 0;
                            return (
                                <div key={key} className={`license-tier-card ${key === 'business' ? 'popular' : ''}`}>
                                    <div className="tier-name">{tier.name}</div>
                                    <div className="tier-price">${tier.price_monthly}<span>/mo</span></div>
                                    <ul className="tier-features">
                                        <li><span className="check">✓</span> {tier.max_domains === -1 ? 'Unlimited' : tier.max_domains} Domain{tier.max_domains !== 1 ? 's' : ''}</li>
                                        {tier.features.slice(0, 5).map((f, i) => (
                                            <li key={i}><span className="check">✓</span> {f.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</li>
                                        ))}
                                    </ul>
                                    <button className={`btn ${key === 'business' ? 'btn-primary' : 'btn-outline'}`}
                                        style={{ width: '100%', justifyContent: 'center' }}>
                                        {tierCount} Active
                                    </button>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Tabs */}
            <div className="tabs">
                {['licenses', 'analytics'].map(tab => (
                    <button key={tab} className={`tab ${activeTab === tab ? 'active' : ''}`}
                        onClick={() => setActiveTab(tab)}>
                        {tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                ))}
            </div>

            {activeTab === 'licenses' && (
                <div className="table-container">
                    <div className="table-header">
                        <span className="table-title">All Licenses ({filteredLicenses.length})</span>
                        <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                            <select className="form-input form-select" style={{ width: '140px' }}
                                value={filterTier} onChange={e => setFilterTier(e.target.value)}>
                                <option value="">All Tiers</option>
                                <option value="free">Free</option>
                                <option value="pro">Pro</option>
                                <option value="business">Business</option>
                                <option value="enterprise">Enterprise</option>
                            </select>
                            <input className="form-input" placeholder="Search..." style={{ width: '200px' }}
                                value={search} onChange={e => setSearch(e.target.value)} />
                        </div>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>License Key</th>
                                <th>Customer</th>
                                <th>Tier</th>
                                <th>Status</th>
                                <th>Server IP</th>
                                <th>Revenue</th>
                                <th>Expires</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredLicenses.length === 0 ? (
                                <tr><td colSpan={8} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                                    {licenses.length === 0 ? 'No licenses issued yet. Click "Issue License" to get started.' : 'No licenses match your filters.'}
                                </td></tr>
                            ) : filteredLicenses.map(lic => (
                                <tr key={lic.id}>
                                    <td>
                                        <code style={{ fontSize: '11px', background: 'var(--bg-tertiary)', padding: '4px 8px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}
                                            onClick={() => { navigator.clipboard.writeText(lic.license_key); showToast('Key copied!', 'success'); }}>
                                            {lic.license_key}
                                        </code>
                                    </td>
                                    <td>
                                        <div>
                                            <div style={{ fontWeight: 600 }}>{lic.customer_name}</div>
                                            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{lic.customer_email}</div>
                                        </div>
                                    </td>
                                    <td><span className={`badge ${tierColors[lic.tier]}`}>{lic.tier}</span></td>
                                    <td>
                                        <span className={`badge badge-dot ${lic.status === 'active' ? 'badge-success' : lic.status === 'expired' ? 'badge-danger' : 'badge-warning'}`}>
                                            {lic.status}
                                        </span>
                                    </td>
                                    <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>{lic.server_ip || '—'}</td>
                                    <td style={{ fontWeight: 600, color: lic.monthly_revenue > 0 ? 'var(--accent-green)' : 'var(--text-muted)' }}>
                                        ${lic.monthly_revenue}/mo
                                    </td>
                                    <td style={{ fontSize: '12px' }}>{lic.expires_at ? new Date(lic.expires_at).toLocaleDateString() : 'Never'}</td>
                                    <td>
                                        <div style={{ display: 'flex', gap: '4px' }}>
                                            {lic.status === 'active' && (
                                                <button className="btn btn-sm btn-outline" style={{ color: 'var(--accent-red)' }} onClick={() => handleRevoke(lic)}>Revoke</button>
                                            )}
                                            {lic.status === 'expired' && (
                                                <button className="btn btn-sm btn-success" onClick={() => handleRenew(lic)}>Renew</button>
                                            )}
                                            {lic.status === 'suspended' && (
                                                <button className="btn btn-sm btn-success" onClick={() => handleReactivate(lic)}>Reactivate</button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {activeTab === 'analytics' && stats && (
                <div className="grid-2">
                    <div className="card">
                        <div className="card-header">
                            <span className="card-title">Tier Distribution</span>
                        </div>
                        <div style={{ padding: 'var(--space-md) 0' }}>
                            {Object.entries(stats.tier_breakdown).map(([tier, count], i) => {
                                const pct = stats.total > 0 ? Math.round((count / stats.total) * 100) : 0;
                                const colors = { free: 'blue', pro: 'purple', business: 'orange', enterprise: 'green' };
                                return (
                                    <div key={tier} style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
                                        <span style={{ width: '80px', fontSize: '13px', fontWeight: 600, textTransform: 'capitalize' }}>{tier}</span>
                                        <div className="progress-bar" style={{ flex: 1 }}>
                                            <div className={`progress-fill ${colors[tier]}`} style={{ width: `${pct}%` }} />
                                        </div>
                                        <span style={{ fontSize: '13px', fontWeight: 600, width: '40px', textAlign: 'right' }}>{count}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                    <div className="card">
                        <div className="card-header"><span className="card-title">Revenue Summary</span></div>
                        <div style={{ padding: 'var(--space-lg)', textAlign: 'center' }}>
                            <div style={{ fontSize: '48px', fontWeight: 800, color: 'var(--accent-green)' }}>${stats.monthly_revenue}</div>
                            <div style={{ color: 'var(--text-muted)', marginTop: '4px' }}>Monthly Recurring Revenue</div>
                            <div style={{ marginTop: 'var(--space-lg)', display: 'flex', justifyContent: 'center', gap: 'var(--space-xl)' }}>
                                <div>
                                    <div style={{ fontSize: '20px', fontWeight: 700 }}>{stats.active}</div>
                                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Active</div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '20px', fontWeight: 700 }}>{stats.expired}</div>
                                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Expired</div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '20px', fontWeight: 700 }}>{stats.suspended}</div>
                                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Suspended</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Issue License Modal */}
            {showIssue && (
                <div className="modal-overlay" onClick={() => setShowIssue(false)}>
                    <div className="modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2 className="modal-title">Issue New License</h2>
                            <button className="modal-close" onClick={() => setShowIssue(false)}>✕</button>
                        </div>
                        <form onSubmit={handleIssue}>
                            <div className="modal-body">
                                <div className="alert alert-info">🔑 A unique license key will be generated automatically.</div>
                                <div className="form-group">
                                    <label className="form-label">Customer Name *</label>
                                    <input className="form-input" placeholder="Company or individual name" value={formName}
                                        onChange={e => setFormName(e.target.value)} required />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Customer Email *</label>
                                    <input className="form-input" type="email" placeholder="customer@email.com" value={formEmail}
                                        onChange={e => setFormEmail(e.target.value)} required />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">License Tier</label>
                                    <select className="form-input form-select" value={formTier} onChange={e => setFormTier(e.target.value)}>
                                        <option value="free">Free ($0/mo)</option>
                                        <option value="pro">Pro ($28/mo)</option>
                                        <option value="business">Business ($48/mo)</option>
                                        <option value="enterprise">Enterprise ($97/mo)</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Server IP (Optional)</label>
                                    <input className="form-input" placeholder="Will be set on first activation" value={formIP}
                                        onChange={e => setFormIP(e.target.value)} />
                                    <p className="form-help">Leave empty to allow activation on any server</p>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Validity</label>
                                    <select className="form-input form-select" value={formValidity} onChange={e => setFormValidity(+e.target.value)}>
                                        <option value={1}>1 Month</option>
                                        <option value={3}>3 Months</option>
                                        <option value={6}>6 Months</option>
                                        <option value={12}>1 Year</option>
                                        <option value={0}>Lifetime</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Notes</label>
                                    <textarea className="form-input" rows="2" placeholder="Internal notes..." value={formNotes}
                                        onChange={e => setFormNotes(e.target.value)} />
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowIssue(false)}>Cancel</button>
                                <button type="submit" className="btn btn-primary" disabled={submitting}>
                                    {submitting ? '⏳ Issuing...' : '🔑 Issue License'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

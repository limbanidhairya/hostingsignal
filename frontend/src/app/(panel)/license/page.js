'use client';
import { useState } from 'react';

export default function LicensePage() {
    const [licenseKey, setLicenseKey] = useState('');
    const [licenseInfo, setLicenseInfo] = useState({
        key: 'HS-DEMO-XXXX-XXXX-XXXX',
        tier: 'professional',
        status: 'active',
        expires: '2026-03-08',
        features: ['ssl', 'dns', 'monitoring', 'backups', 'firewall'],
        max_domains: 20,
        used_domains: 3,
    });

    const handleActivate = () => {
        if (!licenseKey.startsWith('HS-')) {
            alert('Invalid license key format. Expected: HS-XXXX-XXXX-XXXX-XXXX');
            return;
        }
        setLicenseInfo(prev => ({ ...prev, key: licenseKey, status: 'active' }));
        setLicenseKey('');
    };

    const tierColors = {
        starter: '#6b7280',
        professional: '#3b82f6',
        business: '#f6821f',
        enterprise: '#8b5cf6',
    };

    return (
        <div>
            {/* License Status Card */}
            <div className="hs-card" style={{ marginBottom: 24, borderLeft: `4px solid ${tierColors[licenseInfo.tier] || '#3b82f6'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                        <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: 8 }}>License Status</h3>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                            <span className={`hs-badge ${licenseInfo.status === 'active' ? 'success' : 'error'}`} style={{ fontSize: 14, padding: '6px 14px' }}>
                                {licenseInfo.status === 'active' ? '● Active' : '● Inactive'}
                            </span>
                            <span className="hs-badge info" style={{ fontSize: 14, padding: '6px 14px', background: `${tierColors[licenseInfo.tier]}22`, color: tierColors[licenseInfo.tier] }}>
                                {licenseInfo.tier.charAt(0).toUpperCase() + licenseInfo.tier.slice(1)}
                            </span>
                        </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 13, color: 'var(--hs-text-muted)' }}>Expires</div>
                        <div style={{ fontSize: 16, fontWeight: 600 }}>{licenseInfo.expires}</div>
                    </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, padding: '16px 0', borderTop: '1px solid var(--hs-border)' }}>
                    <div>
                        <div style={{ fontSize: 12, color: 'var(--hs-text-muted)', marginBottom: 4 }}>License Key</div>
                        <div style={{ fontFamily: 'monospace', fontSize: 14, fontWeight: 600 }}>{licenseInfo.key}</div>
                    </div>
                    <div>
                        <div style={{ fontSize: 12, color: 'var(--hs-text-muted)', marginBottom: 4 }}>Domains Used</div>
                        <div style={{ fontSize: 14, fontWeight: 600 }}>{licenseInfo.used_domains} / {licenseInfo.max_domains}</div>
                    </div>
                    <div>
                        <div style={{ fontSize: 12, color: 'var(--hs-text-muted)', marginBottom: 4 }}>Features</div>
                        <div style={{ fontSize: 14, fontWeight: 600 }}>{licenseInfo.features.length} active</div>
                    </div>
                </div>
            </div>

            {/* Features */}
            <div className="hs-card" style={{ marginBottom: 24 }}>
                <h3 className="hs-card-title" style={{ marginBottom: 16 }}>Licensed Features</h3>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {licenseInfo.features.map((f) => (
                        <span key={f} className="hs-badge success" style={{ padding: '6px 14px' }}>
                            ✓ {f.replace('_', ' ').toUpperCase()}
                        </span>
                    ))}
                </div>
            </div>

            {/* Domain Usage */}
            <div className="hs-card" style={{ marginBottom: 24 }}>
                <h3 className="hs-card-title" style={{ marginBottom: 12 }}>Domain Usage</h3>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: 13, color: 'var(--hs-text-secondary)' }}>
                    <span>{licenseInfo.used_domains} domains used</span>
                    <span>{licenseInfo.max_domains - licenseInfo.used_domains} remaining</span>
                </div>
                <div className="hs-progress" style={{ height: 10 }}>
                    <div className="hs-progress-bar blue" style={{ width: `${(licenseInfo.used_domains / licenseInfo.max_domains) * 100}%` }} />
                </div>
            </div>

            {/* Activate License */}
            <div className="hs-card">
                <h3 className="hs-card-title" style={{ marginBottom: 16 }}>Activate / Change License</h3>
                <div style={{ display: 'flex', gap: 12 }}>
                    <input
                        className="hs-input"
                        type="text"
                        placeholder="HS-XXXX-XXXX-XXXX-XXXX"
                        value={licenseKey}
                        onChange={(e) => setLicenseKey(e.target.value.toUpperCase())}
                        style={{ fontFamily: 'monospace', flex: 1 }}
                    />
                    <button className="hs-btn hs-btn-primary" onClick={handleActivate}>Activate</button>
                </div>
                <p style={{ fontSize: 13, color: 'var(--hs-text-muted)', marginTop: 8 }}>
                    Enter your license key to activate or upgrade your panel instance.
                </p>
            </div>
        </div>
    );
}

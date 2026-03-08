'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

const STEPS = ['Terms & Conditions', 'License Activation', 'Nameservers', 'Admin Account', 'Complete'];

export default function SetupWizardPage() {
    const [step, setStep] = useState(0);
    const [termsAccepted, setTermsAccepted] = useState(false);
    const [licenseKey, setLicenseKey] = useState('');
    const [ns1, setNs1] = useState('');
    const [ns2, setNs2] = useState('');
    const [admin, setAdmin] = useState({ username: '', password: '', email: '' });
    const [error, setError] = useState('');
    const router = useRouter();

    const apiUrl = typeof window !== 'undefined'
        ? `${window.location.protocol}//${window.location.hostname}:8000`
        : 'http://localhost:8000';

    const nextStep = () => { setError(''); setStep(s => s + 1); };

    const handleTerms = async () => {
        if (!termsAccepted) { setError('You must accept the terms'); return; }
        nextStep();
    };

    const handleLicense = async () => {
        if (!licenseKey.startsWith('HS-')) { setError('Invalid key format (HS-XXXX-...)'); return; }
        try {
            await fetch(`${apiUrl}/api/setup/step/license`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: licenseKey }) });
            nextStep();
        } catch { setError('Failed to activate license'); }
    };

    const handleNameservers = async () => {
        if (!ns1 || !ns2) { setError('Both nameservers are required'); return; }
        try {
            await fetch(`${apiUrl}/api/setup/step/nameservers`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ns1, ns2 }) });
            nextStep();
        } catch { setError('Failed to save nameservers'); }
    };

    const handleAdmin = async () => {
        if (!admin.username || !admin.password || !admin.email) { setError('All fields required'); return; }
        if (admin.password.length < 8) { setError('Password must be 8+ characters'); return; }
        try {
            await fetch(`${apiUrl}/api/setup/step/admin`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(admin) });
            nextStep();
        } catch { setError('Failed to create admin'); }
    };

    const handleFinish = async () => {
        await fetch(`${apiUrl}/api/setup/step/finish`, { method: 'POST' });
        router.push('/dashboard');
    };

    return (
        <div style={{ minHeight: '100vh', background: 'var(--hs-bg-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ maxWidth: 560, width: '90%' }}>
                <div style={{ textAlign: 'center', marginBottom: 32 }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                        <div style={{ width: 48, height: 48, background: 'linear-gradient(135deg, var(--hs-primary), var(--hs-primary-dark))', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 20, color: 'white' }}>HS</div>
                        <span style={{ fontSize: 24, fontWeight: 700 }}>HostingSignal</span>
                    </div>
                    <p style={{ color: 'var(--hs-text-muted)' }}>Setup Wizard</p>
                </div>

                <div style={{ display: 'flex', gap: 4, marginBottom: 32 }}>
                    {STEPS.map((s, i) => (
                        <div key={i} style={{ flex: 1, height: 4, borderRadius: 2, background: i <= step ? 'var(--hs-primary)' : 'var(--hs-border)', transition: 'background 0.3s' }} />
                    ))}
                </div>

                <div className="hs-card">
                    <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 4 }}>{STEPS[step]}</h2>
                    <p style={{ fontSize: 13, color: 'var(--hs-text-muted)', marginBottom: 24 }}>Step {step + 1} of {STEPS.length}</p>

                    {error && <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 6, color: '#ef4444', fontSize: 13, marginBottom: 16 }}>{error}</div>}

                    {step === 0 && (
                        <div>
                            <div style={{ maxHeight: 200, overflow: 'auto', padding: 16, background: 'var(--hs-bg-input)', borderRadius: 8, fontSize: 13, color: 'var(--hs-text-secondary)', marginBottom: 16, lineHeight: 1.8 }}>
                                <p><strong>HostingSignal Panel License Agreement</strong></p>
                                <p>By installing and using HostingSignal Panel, you agree to the following terms:</p>
                                <p>1. This software is licensed, not sold. A valid license key is required.</p>
                                <p>2. Each license is tied to a single server by hardware fingerprint.</p>
                                <p>3. Redistribution or reverse engineering is prohibited.</p>
                                <p>4. Software is provided as-is without warranty.</p>
                                <p>5. HostingSignal may revoke licenses that violate these terms.</p>
                            </div>
                            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, cursor: 'pointer', marginBottom: 20 }}>
                                <input type="checkbox" checked={termsAccepted} onChange={e => setTermsAccepted(e.target.checked)} />
                                I accept the Terms and Conditions
                            </label>
                            <button className="hs-btn hs-btn-primary" style={{ width: '100%' }} onClick={handleTerms}>Continue</button>
                        </div>
                    )}

                    {step === 1 && (
                        <div>
                            <div className="hs-input-group">
                                <label>License Key</label>
                                <input className="hs-input" placeholder="HS-XXXX-XXXX-XXXX-XXXX" value={licenseKey} onChange={e => setLicenseKey(e.target.value.toUpperCase())} style={{ fontFamily: 'monospace' }} />
                            </div>
                            <p style={{ fontSize: 12, color: 'var(--hs-text-muted)', marginBottom: 20 }}>Enter your license key from hostingsignal.com</p>
                            <button className="hs-btn hs-btn-primary" style={{ width: '100%' }} onClick={handleLicense}>Activate License</button>
                        </div>
                    )}

                    {step === 2 && (
                        <div>
                            <div className="hs-input-group">
                                <label>Primary Nameserver (NS1)</label>
                                <input className="hs-input" placeholder="ns1.yourdomain.com" value={ns1} onChange={e => setNs1(e.target.value)} />
                            </div>
                            <div className="hs-input-group">
                                <label>Secondary Nameserver (NS2)</label>
                                <input className="hs-input" placeholder="ns2.yourdomain.com" value={ns2} onChange={e => setNs2(e.target.value)} />
                            </div>
                            <button className="hs-btn hs-btn-primary" style={{ width: '100%' }} onClick={handleNameservers}>Save Nameservers</button>
                        </div>
                    )}

                    {step === 3 && (
                        <div>
                            <div className="hs-input-group">
                                <label>Username</label>
                                <input className="hs-input" placeholder="admin" value={admin.username} onChange={e => setAdmin({ ...admin, username: e.target.value })} />
                            </div>
                            <div className="hs-input-group">
                                <label>Email</label>
                                <input className="hs-input" type="email" placeholder="admin@yourdomain.com" value={admin.email} onChange={e => setAdmin({ ...admin, email: e.target.value })} />
                            </div>
                            <div className="hs-input-group">
                                <label>Password</label>
                                <input className="hs-input" type="password" placeholder="Min 8 characters" value={admin.password} onChange={e => setAdmin({ ...admin, password: e.target.value })} />
                            </div>
                            <button className="hs-btn hs-btn-primary" style={{ width: '100%' }} onClick={handleAdmin}>Create Admin Account</button>
                        </div>
                    )}

                    {step === 4 && (
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: 48, marginBottom: 16 }}>🎉</div>
                            <h3 style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>Setup Complete!</h3>
                            <p style={{ color: 'var(--hs-text-secondary)', marginBottom: 24 }}>Your HostingSignal Panel is ready.</p>
                            <button className="hs-btn hs-btn-primary" style={{ width: '100%' }} onClick={handleFinish}>Go to Dashboard</button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

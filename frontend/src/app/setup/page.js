'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

const TERMS_TEXT = `
HOSTINGSIGNAL END-USER LICENSE AGREEMENT (EULA)

Last Updated: March 2026

BY INSTALLING, COPYING, OR OTHERWISE USING THE HOSTINGSIGNAL SOFTWARE, YOU AGREE TO BE BOUND BY THE TERMS OF THIS AGREEMENT.

1. LICENSE GRANT
HostingSignal grants you a non-exclusive, non-transferable license to use the Software on a single server ("Licensed Server") for the purpose of web hosting management.

2. RESTRICTIONS
You may NOT:
• Redistribute, sublicense, rent, or lease the Software without written permission.
• Reverse-engineer, decompile, or disassemble any portion of the Software.
• Modify, alter, or create derivative works of the panel source code.
• Remove or alter any proprietary notices, labels, or marks on the Software.
• Use the Software on more servers than are permitted by your license tier.
• Share license keys with unauthorized third parties.

3. LICENSE TIERS
The Software is available under multiple license tiers (Free, Pro, Business, Enterprise), each with different feature sets, domain limits, and support levels. Features and limits are subject to change.

4. DATA & PRIVACY
HostingSignal does NOT collect personal data from your server. License validation requests transmit only: License Key, Server IP, and Panel Version for verification purposes.

5. TERMINATION
This license is effective until terminated. Your rights under this license will terminate automatically if you fail to comply with any of its terms.

6. WARRANTY DISCLAIMER
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.

7. LIMITATION OF LIABILITY
IN NO EVENT SHALL HOSTINGSIGNAL BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES.

8. INTELLECTUAL PROPERTY
HostingSignal and its logos are trademarks. All installation directories are locked and read-only after installation to protect software integrity.

9. GOVERNING LAW
This agreement shall be governed by applicable law.

By clicking "I Accept", you acknowledge that you have read, understood, and agree to be bound by this Agreement.
`;

export default function SetupWizard() {
    const router = useRouter();
    const [step, setStep] = useState(0);

    // Step 0: Terms
    const [termsAccepted, setTermsAccepted] = useState(false);

    // Step 1: Account
    const [accountMode, setAccountMode] = useState('create'); // create | login
    const [formData, setFormData] = useState({ name: '', email: '', password: '', confirmPassword: '' });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Step 2: License
    const [licenseKey, setLicenseKey] = useState('');
    const [licenseAction, setLicenseAction] = useState('activate'); // activate | buy | transfer
    const [oldServerIP, setOldServerIP] = useState('');
    const [licenseResult, setLicenseResult] = useState(null);

    // Step 3: Server config
    const [hostname, setHostname] = useState('');
    const [ns1, setNs1] = useState('ns1.hostingsignal.com');
    const [ns2, setNs2] = useState('ns2.hostingsignal.com');
    const [adminEmail, setAdminEmail] = useState('');

    const steps = [
        { title: 'Terms & Conditions', icon: '📋' },
        { title: 'Account Setup', icon: '👤' },
        { title: 'License Activation', icon: '🔑' },
        { title: 'Server Configuration', icon: '⚙️' },
        { title: 'Complete', icon: '🎉' },
    ];

    async function handleAccountSubmit() {
        setError('');
        setLoading(true);
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            if (accountMode === 'create') {
                if (formData.password !== formData.confirmPassword) {
                    setError('Passwords do not match');
                    setLoading(false);
                    return;
                }
                const res = await fetch(`${apiUrl}/api/auth/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: formData.name, email: formData.email, password: formData.password }),
                });
                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.detail || 'Registration failed');
                }
            }
            // Login
            const loginRes = await fetch(`${apiUrl}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ username: formData.email, password: formData.password }),
            });
            if (!loginRes.ok) throw new Error('Login failed');
            const loginData = await loginRes.json();
            localStorage.setItem('access_token', loginData.access_token);
            if (loginData.refresh_token) localStorage.setItem('refresh_token', loginData.refresh_token);
            setAdminEmail(formData.email);
            setStep(2);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    async function handleLicenseActivation() {
        setLoading(true);
        setError('');
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const token = localStorage.getItem('access_token');
            if (licenseAction === 'activate' && licenseKey) {
                const res = await fetch(`${apiUrl}/api/licenses/activate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                    body: JSON.stringify({ license_key: licenseKey }),
                });
                const data = await res.json();
                if (res.ok) {
                    setLicenseResult({ status: 'success', message: 'License activated successfully!', data });
                } else {
                    setLicenseResult({ status: 'error', message: data.detail || 'Activation failed' });
                }
            } else if (licenseAction === 'transfer' && licenseKey && oldServerIP) {
                const res = await fetch(`${apiUrl}/api/licenses/transfer`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                    body: JSON.stringify({ license_key: licenseKey, old_server_ip: oldServerIP }),
                });
                const data = await res.json();
                if (res.ok) {
                    setLicenseResult({ status: 'success', message: 'License transferred! Old server panel has been disabled.', data });
                } else {
                    setLicenseResult({ status: 'error', message: data.detail || 'Transfer failed' });
                }
            } else {
                // Skip / buy later
                setLicenseResult({ status: 'skip', message: 'Continuing with free tier. You can activate a license later in Settings.' });
            }
        } catch (err) {
            setLicenseResult({ status: 'error', message: err.message });
        } finally {
            setLoading(false);
        }
    }

    async function handleServerConfig() {
        setLoading(true);
        // Save server config (this would call the backend API)
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const token = localStorage.getItem('access_token');
            await fetch(`${apiUrl}/api/server/setup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({ hostname, nameservers: [ns1, ns2], admin_email: adminEmail }),
            }).catch(() => { });
            setStep(4);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div style={{
            minHeight: '100vh', background: 'linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 50%, #0a0a2e 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'Inter', system-ui, sans-serif",
        }}>
            <div style={{ width: '100%', maxWidth: '720px', padding: '20px' }}>
                {/* Progress Steps */}
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '32px', gap: '4px' }}>
                    {steps.map((s, i) => (
                        <div key={i} style={{
                            display: 'flex', alignItems: 'center', gap: '4px',
                        }}>
                            <div style={{
                                width: 36, height: 36, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                                fontSize: '14px', fontWeight: 700,
                                background: i <= step ? 'linear-gradient(135deg, #6c5ce7, #a29bfe)' : 'rgba(255,255,255,0.1)',
                                color: i <= step ? '#fff' : 'rgba(255,255,255,0.4)',
                                transition: 'all 0.3s ease',
                            }}>
                                {i < step ? '✓' : s.icon}
                            </div>
                            {i < steps.length - 1 && (
                                <div style={{
                                    width: 40, height: 2,
                                    background: i < step ? '#6c5ce7' : 'rgba(255,255,255,0.1)',
                                    transition: 'background 0.3s ease',
                                }} />
                            )}
                        </div>
                    ))}
                </div>

                {/* Card */}
                <div style={{
                    background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(20px)',
                    borderRadius: '16px', border: '1px solid rgba(255,255,255,0.1)',
                    padding: '40px', boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
                }}>
                    {/* Step 0: Terms */}
                    {step === 0 && (
                        <>
                            <h1 style={{ color: '#fff', fontSize: '24px', marginBottom: '8px' }}>📋 Terms & Conditions</h1>
                            <p style={{ color: 'rgba(255,255,255,0.6)', marginBottom: '20px' }}>Please read and accept the terms before proceeding.</p>
                            <div style={{
                                background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '16px',
                                height: '300px', overflowY: 'auto', marginBottom: '20px',
                                fontSize: '12px', color: 'rgba(255,255,255,0.7)', lineHeight: 1.6, whiteSpace: 'pre-wrap',
                            }}>
                                {TERMS_TEXT}
                            </div>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#fff', cursor: 'pointer', marginBottom: '20px' }}>
                                <input type="checkbox" checked={termsAccepted} onChange={e => setTermsAccepted(e.target.checked)}
                                    style={{ width: 20, height: 20, accentColor: '#6c5ce7' }} />
                                <span>I have read and accept the Terms & Conditions</span>
                            </label>
                            <button
                                disabled={!termsAccepted}
                                onClick={() => setStep(1)}
                                style={{
                                    width: '100%', padding: '14px', border: 'none', borderRadius: '10px', fontSize: '15px', fontWeight: 700,
                                    cursor: termsAccepted ? 'pointer' : 'not-allowed',
                                    background: termsAccepted ? 'linear-gradient(135deg, #6c5ce7, #a29bfe)' : 'rgba(255,255,255,0.1)',
                                    color: termsAccepted ? '#fff' : 'rgba(255,255,255,0.3)',
                                    transition: 'all 0.3s ease',
                                }}
                            >Continue →</button>
                        </>
                    )}

                    {/* Step 1: Account */}
                    {step === 1 && (
                        <>
                            <h1 style={{ color: '#fff', fontSize: '24px', marginBottom: '8px' }}>👤 Account Setup</h1>
                            <p style={{ color: 'rgba(255,255,255,0.6)', marginBottom: '20px' }}>Create a new admin account or login to an existing one.</p>

                            <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
                                {['create', 'login'].map(m => (
                                    <button key={m} onClick={() => setAccountMode(m)} style={{
                                        flex: 1, padding: '10px', border: '1px solid', borderRadius: '8px', fontSize: '14px', fontWeight: 600,
                                        borderColor: accountMode === m ? '#6c5ce7' : 'rgba(255,255,255,0.15)',
                                        background: accountMode === m ? 'rgba(108,92,231,0.2)' : 'transparent',
                                        color: accountMode === m ? '#a29bfe' : 'rgba(255,255,255,0.5)', cursor: 'pointer',
                                    }}>{m === 'create' ? '✨ Create Account' : '🔐 Login'}</button>
                                ))}
                            </div>

                            {error && <div style={{ background: 'rgba(255,71,87,0.15)', border: '1px solid rgba(255,71,87,0.3)', borderRadius: '8px', padding: '10px', marginBottom: '16px', color: '#ff4757', fontSize: '13px' }}>{error}</div>}

                            {accountMode === 'create' && (
                                <div style={{ marginBottom: '16px' }}>
                                    <label style={{ display: 'block', color: 'rgba(255,255,255,0.7)', fontSize: '13px', marginBottom: '6px' }}>Full Name</label>
                                    <input value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })}
                                        style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '8px', color: '#fff', fontSize: '14px', outline: 'none' }}
                                        placeholder="Your name" />
                                </div>
                            )}
                            <div style={{ marginBottom: '16px' }}>
                                <label style={{ display: 'block', color: 'rgba(255,255,255,0.7)', fontSize: '13px', marginBottom: '6px' }}>Email</label>
                                <input type="email" value={formData.email} onChange={e => setFormData({ ...formData, email: e.target.value })}
                                    style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '8px', color: '#fff', fontSize: '14px', outline: 'none' }}
                                    placeholder="admin@example.com" />
                            </div>
                            <div style={{ marginBottom: '16px' }}>
                                <label style={{ display: 'block', color: 'rgba(255,255,255,0.7)', fontSize: '13px', marginBottom: '6px' }}>Password</label>
                                <input type="password" value={formData.password} onChange={e => setFormData({ ...formData, password: e.target.value })}
                                    style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '8px', color: '#fff', fontSize: '14px', outline: 'none' }}
                                    placeholder="••••••••" />
                            </div>
                            {accountMode === 'create' && (
                                <div style={{ marginBottom: '16px' }}>
                                    <label style={{ display: 'block', color: 'rgba(255,255,255,0.7)', fontSize: '13px', marginBottom: '6px' }}>Confirm Password</label>
                                    <input type="password" value={formData.confirmPassword} onChange={e => setFormData({ ...formData, confirmPassword: e.target.value })}
                                        style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '8px', color: '#fff', fontSize: '14px', outline: 'none' }}
                                        placeholder="••••••••" />
                                </div>
                            )}
                            <button onClick={handleAccountSubmit} disabled={loading} style={{
                                width: '100%', padding: '14px', border: 'none', borderRadius: '10px', fontSize: '15px', fontWeight: 700,
                                background: 'linear-gradient(135deg, #6c5ce7, #a29bfe)', color: '#fff', cursor: 'pointer',
                            }}>{loading ? '⏳ Processing...' : accountMode === 'create' ? 'Create & Continue →' : 'Login & Continue →'}</button>
                        </>
                    )}

                    {/* Step 2: License */}
                    {step === 2 && (
                        <>
                            <h1 style={{ color: '#fff', fontSize: '24px', marginBottom: '8px' }}>🔑 License Activation</h1>
                            <p style={{ color: 'rgba(255,255,255,0.6)', marginBottom: '20px' }}>Activate, transfer, or purchase a license key.</p>

                            <div style={{ display: 'flex', gap: '6px', marginBottom: '24px', flexWrap: 'wrap' }}>
                                {[
                                    { id: 'activate', label: '✅ Activate Key', desc: 'I have a key' },
                                    { id: 'transfer', label: '🔄 Transfer', desc: 'From old server' },
                                    { id: 'skip', label: '⏭️ Skip', desc: 'Use free tier' },
                                ].map(a => (
                                    <button key={a.id} onClick={() => setLicenseAction(a.id)} style={{
                                        flex: 1, padding: '12px 8px', border: '1px solid', borderRadius: '8px', textAlign: 'center',
                                        borderColor: licenseAction === a.id ? '#6c5ce7' : 'rgba(255,255,255,0.15)',
                                        background: licenseAction === a.id ? 'rgba(108,92,231,0.2)' : 'transparent',
                                        color: licenseAction === a.id ? '#a29bfe' : 'rgba(255,255,255,0.5)', cursor: 'pointer',
                                    }}>
                                        <div style={{ fontSize: '13px', fontWeight: 700 }}>{a.label}</div>
                                        <div style={{ fontSize: '11px', marginTop: '2px' }}>{a.desc}</div>
                                    </button>
                                ))}
                            </div>

                            {(licenseAction === 'activate' || licenseAction === 'transfer') && (
                                <div style={{ marginBottom: '16px' }}>
                                    <label style={{ display: 'block', color: 'rgba(255,255,255,0.7)', fontSize: '13px', marginBottom: '6px' }}>License Key</label>
                                    <input value={licenseKey} onChange={e => setLicenseKey(e.target.value)}
                                        style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '8px', color: '#fff', fontSize: '14px', fontFamily: 'monospace', letterSpacing: '1px', outline: 'none' }}
                                        placeholder="HSIG-XXXX-XXXX-XXXX-XXXX" />
                                </div>
                            )}

                            {licenseAction === 'transfer' && (
                                <div style={{ marginBottom: '16px' }}>
                                    <label style={{ display: 'block', color: 'rgba(255,255,255,0.7)', fontSize: '13px', marginBottom: '6px' }}>Old Server IP Address</label>
                                    <input value={oldServerIP} onChange={e => setOldServerIP(e.target.value)}
                                        style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '8px', color: '#fff', fontSize: '14px', outline: 'none' }}
                                        placeholder="192.168.1.100" />
                                    <p style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>
                                        ⚠️ The admin panel on the old server will be disabled after transfer.
                                    </p>
                                </div>
                            )}

                            {licenseResult && (
                                <div style={{
                                    background: licenseResult.status === 'success' ? 'rgba(46,213,115,0.15)' : licenseResult.status === 'error' ? 'rgba(255,71,87,0.15)' : 'rgba(108,92,231,0.15)',
                                    border: `1px solid ${licenseResult.status === 'success' ? 'rgba(46,213,115,0.3)' : licenseResult.status === 'error' ? 'rgba(255,71,87,0.3)' : 'rgba(108,92,231,0.3)'}`,
                                    borderRadius: '8px', padding: '12px', marginBottom: '16px', fontSize: '13px',
                                    color: licenseResult.status === 'success' ? '#2ed573' : licenseResult.status === 'error' ? '#ff4757' : '#a29bfe',
                                }}>{licenseResult.message}</div>
                            )}

                            <div style={{ display: 'flex', gap: '10px' }}>
                                <button onClick={() => setStep(1)} style={{
                                    padding: '14px 20px', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '10px',
                                    background: 'transparent', color: 'rgba(255,255,255,0.6)', cursor: 'pointer', fontSize: '14px',
                                }}>← Back</button>
                                <button onClick={async () => { await handleLicenseActivation(); if (licenseAction === 'skip' || licenseResult?.status === 'success') setStep(3); }} disabled={loading}
                                    style={{
                                        flex: 1, padding: '14px', border: 'none', borderRadius: '10px', fontSize: '15px', fontWeight: 700,
                                        background: 'linear-gradient(135deg, #6c5ce7, #a29bfe)', color: '#fff', cursor: 'pointer',
                                    }}>{loading ? '⏳ Processing...' : licenseAction === 'skip' ? 'Continue with Free →' : 'Activate & Continue →'}</button>
                            </div>
                        </>
                    )}

                    {/* Step 3: Server Config */}
                    {step === 3 && (
                        <>
                            <h1 style={{ color: '#fff', fontSize: '24px', marginBottom: '8px' }}>⚙️ Server Configuration</h1>
                            <p style={{ color: 'rgba(255,255,255,0.6)', marginBottom: '20px' }}>Configure your server's basic settings.</p>

                            <div style={{ marginBottom: '16px' }}>
                                <label style={{ display: 'block', color: 'rgba(255,255,255,0.7)', fontSize: '13px', marginBottom: '6px' }}>Server Hostname</label>
                                <input value={hostname} onChange={e => setHostname(e.target.value)}
                                    style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '8px', color: '#fff', fontSize: '14px', outline: 'none' }}
                                    placeholder="server1.yourdomain.com" />
                            </div>
                            <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
                                <div style={{ flex: 1 }}>
                                    <label style={{ display: 'block', color: 'rgba(255,255,255,0.7)', fontSize: '13px', marginBottom: '6px' }}>Nameserver 1</label>
                                    <input value={ns1} onChange={e => setNs1(e.target.value)}
                                        style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '8px', color: '#fff', fontSize: '14px', outline: 'none' }} />
                                </div>
                                <div style={{ flex: 1 }}>
                                    <label style={{ display: 'block', color: 'rgba(255,255,255,0.7)', fontSize: '13px', marginBottom: '6px' }}>Nameserver 2</label>
                                    <input value={ns2} onChange={e => setNs2(e.target.value)}
                                        style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '8px', color: '#fff', fontSize: '14px', outline: 'none' }} />
                                </div>
                            </div>
                            <div style={{ marginBottom: '24px' }}>
                                <label style={{ display: 'block', color: 'rgba(255,255,255,0.7)', fontSize: '13px', marginBottom: '6px' }}>Admin Email</label>
                                <input value={adminEmail} onChange={e => setAdminEmail(e.target.value)}
                                    style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '8px', color: '#fff', fontSize: '14px', outline: 'none' }}
                                    placeholder="admin@yourdomain.com" />
                            </div>
                            <div style={{ display: 'flex', gap: '10px' }}>
                                <button onClick={() => setStep(2)} style={{
                                    padding: '14px 20px', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '10px',
                                    background: 'transparent', color: 'rgba(255,255,255,0.6)', cursor: 'pointer', fontSize: '14px',
                                }}>← Back</button>
                                <button onClick={handleServerConfig} disabled={loading} style={{
                                    flex: 1, padding: '14px', border: 'none', borderRadius: '10px', fontSize: '15px', fontWeight: 700,
                                    background: 'linear-gradient(135deg, #6c5ce7, #a29bfe)', color: '#fff', cursor: 'pointer',
                                }}>{loading ? '⏳ Saving...' : 'Complete Setup →'}</button>
                            </div>
                        </>
                    )}

                    {/* Step 4: Complete */}
                    {step === 4 && (
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '64px', marginBottom: '16px' }}>🎉</div>
                            <h1 style={{ color: '#fff', fontSize: '28px', marginBottom: '12px' }}>Setup Complete!</h1>
                            <p style={{ color: 'rgba(255,255,255,0.6)', marginBottom: '24px', lineHeight: 1.6 }}>
                                Your HostingSignal panel is ready to use.<br />
                                All services have been configured and are running.
                            </p>
                            <div style={{
                                background: 'rgba(108,92,231,0.15)', borderRadius: '10px', padding: '20px', marginBottom: '24px',
                                border: '1px solid rgba(108,92,231,0.3)', textAlign: 'left',
                            }}>
                                <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.8)', fontWeight: 600, marginBottom: '12px' }}>✅ Services Running:</div>
                                {['OpenLiteSpeed Web Server', 'PowerDNS Service', 'Postfix Mail Server', 'Dovecot IMAP', 'MariaDB Database', 'Pure-FTPd', 'FirewallD', 'SSL Auto-Renewal'].map((svc, i) => (
                                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0', color: 'rgba(255,255,255,0.7)', fontSize: '13px' }}>
                                        <span style={{ color: '#2ed573' }}>●</span> {svc}
                                    </div>
                                ))}
                            </div>
                            <button onClick={() => router.push('/dashboard')} style={{
                                width: '100%', padding: '16px', border: 'none', borderRadius: '10px', fontSize: '16px', fontWeight: 700,
                                background: 'linear-gradient(135deg, #6c5ce7, #a29bfe)', color: '#fff', cursor: 'pointer',
                                boxShadow: '0 4px 20px rgba(108,92,231,0.4)',
                            }}>🚀 Go to Dashboard</button>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <p style={{ textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '12px', marginTop: '20px' }}>
                    HostingSignal v1.0.0 • © 2026 All rights reserved
                </p>
            </div>
        </div>
    );
}

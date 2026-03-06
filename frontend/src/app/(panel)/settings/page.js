'use client';
import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

export default function SettingsPage() {
    const { user, refreshUser, logout } = useAuth();
    const { showToast, ToastContainer } = useToast();
    const [activeSection, setActiveSection] = useState('general');

    // Profile form
    const [profileName, setProfileName] = useState(user?.name || '');
    const [profileEmail, setProfileEmail] = useState(user?.email || '');
    const [savingProfile, setSavingProfile] = useState(false);

    // Password form
    const [currentPass, setCurrentPass] = useState('');
    const [newPass, setNewPass] = useState('');
    const [confirmPass, setConfirmPass] = useState('');
    const [savingPass, setSavingPass] = useState(false);

    // 2FA
    const [twoFASetup, setTwoFASetup] = useState(null);
    const [twoFACode, setTwoFACode] = useState('');
    const [enabling2FA, setEnabling2FA] = useState(false);

    // Settings state (local for non-API settings)
    const [panelName, setPanelName] = useState('HostingSignal');
    const [timezone, setTimezone] = useState('UTC');
    const [language, setLanguage] = useState('en');

    async function handleProfileSave(e) {
        e.preventDefault();
        setSavingProfile(true);
        try {
            await api.updateMe({ name: profileName, email: profileEmail });
            await refreshUser();
            showToast('Profile updated successfully!', 'success');
        } catch (err) {
            showToast('Failed: ' + err.message, 'error');
        } finally {
            setSavingProfile(false);
        }
    }

    async function handlePasswordChange(e) {
        e.preventDefault();
        if (newPass !== confirmPass) { showToast('Passwords do not match', 'error'); return; }
        if (newPass.length < 6) { showToast('Password must be at least 6 characters', 'error'); return; }
        setSavingPass(true);
        try {
            await api.changePassword(currentPass, newPass);
            showToast('Password changed successfully!', 'success');
            setCurrentPass(''); setNewPass(''); setConfirmPass('');
        } catch (err) {
            showToast('Failed: ' + err.message, 'error');
        } finally {
            setSavingPass(false);
        }
    }

    async function handleEnable2FA() {
        setEnabling2FA(true);
        try {
            const data = await api.enable2FA();
            setTwoFASetup(data);
            showToast('Scan the QR code with your authenticator app', 'info');
        } catch (err) {
            showToast('Failed: ' + err.message, 'error');
        } finally {
            setEnabling2FA(false);
        }
    }

    async function handleVerify2FA(e) {
        e.preventDefault();
        try {
            await api.verify2FA(twoFACode);
            showToast('2FA enabled successfully! 🔒', 'success');
            setTwoFASetup(null);
            setTwoFACode('');
            await refreshUser();
        } catch (err) {
            showToast('Invalid code: ' + err.message, 'error');
        }
    }

    const sections = [
        { id: 'general', label: '⚙️ General', icon: '⚙️' },
        { id: 'profile', label: '👤 Profile', icon: '👤' },
        { id: 'security', label: '🔒 Security', icon: '🔒' },
        { id: 'api', label: '🔗 API & Integrations', icon: '🔗' },
        { id: 'notifications', label: '🔔 Notifications', icon: '🔔' },
    ];

    return (
        <div className="animate-fade">
            <ToastContainer />
            <div className="page-header">
                <div>
                    <h1 className="glow-text">Settings</h1>
                    <p>Configure your HostingSignal panel</p>
                </div>
            </div>

            <div className="settings-layout">
                {/* Settings Sidebar */}
                <div className="settings-sidebar liquid-glass" style={{ padding: 'var(--space-sm)' }}>
                    {sections.map(s => (
                        <button key={s.id} className={`settings-nav-item skeuo-btn ${activeSection === s.id ? 'active' : ''}`}
                            onClick={() => setActiveSection(s.id)} style={{ marginBottom: 4 }}>
                            {s.label}
                        </button>
                    ))}
                </div>

                {/* Content */}
                <div className="settings-content">
                    {activeSection === 'general' && (
                        <div className="card liquid-glass">
                            <div className="card-header"><span className="card-title glow-text">General Settings</span></div>
                            <div style={{ padding: 'var(--space-md)' }}>
                                <div className="form-group">
                                    <label className="form-label">Panel Name</label>
                                    <input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} value={panelName} onChange={e => setPanelName(e.target.value)} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Timezone</label>
                                    <select className="form-input form-select" style={{ background: 'rgba(0,0,0,0.2)' }} value={timezone} onChange={e => setTimezone(e.target.value)}>
                                        <option value="UTC" style={{ background: 'black' }}>UTC</option>
                                        <option value="America/New_York" style={{ background: 'black' }}>Eastern Time</option>
                                        <option value="America/Chicago" style={{ background: 'black' }}>Central Time</option>
                                        <option value="America/Los_Angeles" style={{ background: 'black' }}>Pacific Time</option>
                                        <option value="Europe/London" style={{ background: 'black' }}>London</option>
                                        <option value="Asia/Kolkata" style={{ background: 'black' }}>India (IST)</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Language</label>
                                    <select className="form-input form-select" style={{ background: 'rgba(0,0,0,0.2)' }} value={language} onChange={e => setLanguage(e.target.value)}>
                                        <option value="en" style={{ background: 'black' }}>English</option>
                                        <option value="es" style={{ background: 'black' }}>Spanish</option>
                                        <option value="fr" style={{ background: 'black' }}>French</option>
                                        <option value="de" style={{ background: 'black' }}>German</option>
                                        <option value="hi" style={{ background: 'black' }}>Hindi</option>
                                    </select>
                                </div>
                                <button className="btn skeuo-btn-primary" onClick={() => showToast('Settings saved!', 'success')}>Save Changes</button>
                            </div>
                        </div>
                    )}

                    {activeSection === 'profile' && (
                        <div className="card liquid-glass">
                            <div className="card-header"><span className="card-title glow-text">Profile Settings</span></div>
                            <form onSubmit={handleProfileSave} style={{ padding: 'var(--space-md)' }}>
                                <div className="form-group">
                                    <label className="form-label">Full Name</label>
                                    <input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} value={profileName} onChange={e => setProfileName(e.target.value)} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Email</label>
                                    <input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} type="email" value={profileEmail} onChange={e => setProfileEmail(e.target.value)} />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Role</label>
                                    <input className="form-input" style={{ background: 'rgba(0,0,0,0.2)', opacity: 0.6 }} value={user?.role || 'client'} disabled />
                                    <p className="form-help">Contact administrator to change your role</p>
                                </div>
                                <button type="submit" className="btn skeuo-btn-primary" disabled={savingProfile}>
                                    {savingProfile ? '⏳ Saving...' : 'Save Profile'}
                                </button>
                            </form>
                        </div>
                    )}

                    {activeSection === 'security' && (
                        <>
                            {/* Change Password */}
                            <div className="card liquid-glass" style={{ marginBottom: 'var(--space-lg)' }}>
                                <div className="card-header"><span className="card-title glow-text">Change Password</span></div>
                                <form onSubmit={handlePasswordChange} style={{ padding: 'var(--space-md)' }}>
                                    <div className="form-group">
                                        <label className="form-label">Current Password</label>
                                        <input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} type="password" value={currentPass} onChange={e => setCurrentPass(e.target.value)} required />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">New Password</label>
                                        <input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} type="password" value={newPass} onChange={e => setNewPass(e.target.value)} required />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Confirm New Password</label>
                                        <input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} type="password" value={confirmPass} onChange={e => setConfirmPass(e.target.value)} required />
                                    </div>
                                    <button type="submit" className="btn skeuo-btn-primary" disabled={savingPass}>
                                        {savingPass ? '⏳ Changing...' : 'Change Password'}
                                    </button>
                                </form>
                            </div>

                            {/* 2FA */}
                            <div className="card liquid-glass">
                                <div className="card-header">
                                    <span className="card-title glow-text">Two-Factor Authentication</span>
                                    <span className={`badge ${user?.totp_enabled ? 'badge-success' : 'badge-warning'}`}>
                                        {user?.totp_enabled ? '🔒 Enabled' : '⚠️ Disabled'}
                                    </span>
                                </div>
                                <div style={{ padding: 'var(--space-md)' }}>
                                    {user?.totp_enabled ? (
                                        <div className="alert alert-success">✅ Two-factor authentication is enabled. Your account is secure.</div>
                                    ) : twoFASetup ? (
                                        <div>
                                            <div className="alert alert-info">📱 Open your authenticator app (Google Authenticator, Authy, etc.) and scan or enter this code:</div>
                                            <div style={{ margin: 'var(--space-md) 0', padding: 'var(--space-md)', background: 'rgba(0,0,0,0.3)', borderRadius: 'var(--radius-md)', textAlign: 'center', border: '1px solid rgba(255,255,255,0.1)' }}>
                                                <code style={{ fontSize: '18px', letterSpacing: '2px', fontWeight: 700, color: 'var(--accent-cyan)' }}>{twoFASetup.secret}</code>
                                            </div>
                                            <form onSubmit={handleVerify2FA}>
                                                <div className="form-group">
                                                    <label className="form-label">Enter 6-digit code from your app</label>
                                                    <input className="form-input" placeholder="000000" maxLength={6} value={twoFACode}
                                                        onChange={e => setTwoFACode(e.target.value)} style={{ background: 'rgba(0,0,0,0.2)', width: '200px', letterSpacing: '4px', fontSize: '18px', textAlign: 'center' }} />
                                                </div>
                                                <button type="submit" className="btn skeuo-btn-primary">Verify & Enable</button>
                                            </form>
                                        </div>
                                    ) : (
                                        <div>
                                            <p style={{ marginBottom: 'var(--space-md)', color: 'var(--text-secondary)' }}>
                                                Add an extra layer of security to your account with TOTP-based 2FA.
                                            </p>
                                            <button className="btn skeuo-btn-primary" onClick={handleEnable2FA} disabled={enabling2FA}>
                                                {enabling2FA ? '⏳ Setting up...' : '🔒 Enable 2FA'}
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </>
                    )}



                    {activeSection === 'api' && (
                        <>
                            <div className="card liquid-glass" style={{ marginBottom: 'var(--space-lg)' }}>
                                <div className="card-header"><span className="card-title glow-text">API Configuration</span></div>
                                <div style={{ padding: 'var(--space-md)' }}>
                                    <div className="form-group">
                                        <label className="form-label">API Base URL</label>
                                        <input className="form-input" style={{ background: 'rgba(0,0,0,0.2)', opacity: 0.6 }} value="http://localhost:8000" disabled />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Interactive Docs</label>
                                        <a href="http://localhost:8000/api/docs" target="_blank" rel="noopener noreferrer"
                                            className="btn skeuo-btn" style={{ display: 'inline-flex' }}>📄 Open Swagger Docs</a>
                                    </div>
                                </div>
                            </div>
                            <div className="card liquid-glass" style={{ marginBottom: 'var(--space-lg)' }}>
                                <div className="card-header"><span className="card-title glow-text">WHMCS Provisioning Module</span></div>
                                <div style={{ padding: 'var(--space-md)' }}>
                                    <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-md)', fontSize: '13px' }}>
                                        Download and install the HostingSignal WHMCS module to automate license provisioning,
                                        suspension, and termination directly from your WHMCS billing system.
                                    </p>
                                    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: 'var(--radius-md)', padding: 'var(--space-lg)', marginBottom: 'var(--space-md)', border: '1px solid rgba(255,255,255,0.1)' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-md)' }}>
                                            <div>
                                                <div style={{ fontWeight: 700, fontSize: '15px' }}>📦 hostingsignal-whmcs-module.zip</div>
                                                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>v1.0.0 • Compatible with WHMCS 8.x+</div>
                                            </div>
                                            <a href="/api/downloads/whmcs-module" className="btn skeuo-btn-primary" style={{ display: 'inline-flex' }}>⬇️ Download Module</a>
                                        </div>
                                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                                            <strong>Installation:</strong> Upload to <code>/modules/servers/hostingsignal/</code> in your WHMCS directory
                                        </div>
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">WHMCS URL</label>
                                        <input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="https://billing.your-domain.com" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">API Identifier</label>
                                        <input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="Enter WHMCS API identifier" />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">API Secret</label>
                                        <input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} type="password" placeholder="Enter WHMCS API secret" />
                                    </div>
                                    <button className="btn skeuo-btn-primary" onClick={() => showToast('WHMCS settings saved!', 'success')}>Save Integration</button>
                                </div>
                            </div>
                            <div className="card liquid-glass">
                                <div className="card-header"><span className="card-title glow-text">System Information</span></div>
                                <div style={{ padding: 'var(--space-md)' }}>
                                    <div className="alert alert-info" style={{ marginBottom: 0 }}>
                                        🔒 Panel installation directories are locked and read-only.
                                        Panel files cannot be modified after installation for security.
                                    </div>
                                </div>
                            </div>
                        </>
                    )}

                    {activeSection === 'notifications' && (
                        <div className="card liquid-glass">
                            <div className="card-header"><span className="card-title glow-text">Notification Preferences</span></div>
                            <div style={{ padding: 'var(--space-md)' }}>
                                {[
                                    { label: 'License expiration warnings', desc: '7 days before expiry' },
                                    { label: 'New license activations', desc: 'When a license is activated on a server' },
                                    { label: 'Failed heartbeat alerts', desc: 'When a server stops checking in' },
                                    { label: 'Security alerts', desc: 'Unauthorized access attempts' },
                                    { label: 'Server resource warnings', desc: 'CPU/RAM/Disk usage above 90%' },
                                ].map((item, i) => (
                                    <div key={i} style={{
                                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                        padding: '14px 0', borderBottom: i < 4 ? '1px solid rgba(255,255,255,0.1)' : 'none'
                                    }}>
                                        <div>
                                            <div style={{ fontWeight: 600, fontSize: '14px' }}>{item.label}</div>
                                            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{item.desc}</div>
                                        </div>
                                        <label className="toggle">
                                            <input type="checkbox" defaultChecked={i < 3} />
                                            <span className="toggle-slider skeuo-btn"></span>
                                        </label>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

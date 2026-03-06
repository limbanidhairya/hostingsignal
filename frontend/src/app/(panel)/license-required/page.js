'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function LicenseRequiredPage() {
    const [key, setKey] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const router = useRouter();

    const handleActivate = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const res = await fetch('http://localhost:8000/api/system/activate-license', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key })
            });

            if (res.ok) {
                // Success, reload app to re-evaluate middleware
                window.location.href = '/dashboard';
            } else {
                const data = await res.json();
                setError(data.detail || 'Invalid license key.');
            }
        } catch (err) {
            setError('Failed to contact activation server.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="animate-fade" style={{ width: '100%', maxWidth: '450px', padding: '20px' }}>
            <div className="clay-card liquid-glass" style={{ padding: '40px', textAlign: 'center' }}>
                <div style={{
                    width: '80px', height: '80px', margin: '0 auto 20px auto',
                    background: 'rgba(0,0,0,0.5)', borderRadius: '50%',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    border: '1px solid var(--accent-cyan)', boxShadow: '0 0 20px rgba(0, 240, 255, 0.3)'
                }}>
                    <span style={{ fontSize: '32px' }}>🔒</span>
                </div>

                <h1 className="glow-text" style={{ fontSize: '24px', marginBottom: '10px' }}>License Required</h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '30px' }}>
                    This HostingSignal panel installation has not been activated. Please enter a valid license key to proceed.
                </p>

                {error && (
                    <div className="alert alert-error" style={{ marginBottom: '20px' }}>
                        ❌ {error}
                    </div>
                )}

                <form onSubmit={handleActivate}>
                    <div className="form-group" style={{ textAlign: 'left' }}>
                        <input
                            className="form-input"
                            style={{
                                background: 'rgba(0,0,0,0.3)',
                                fontSize: '16px',
                                padding: '15px',
                                letterSpacing: '1px',
                                textAlign: 'center'
                            }}
                            placeholder="HS-XXXX-XXXX-XXXX-XXXX"
                            value={key}
                            onChange={(e) => setKey(e.target.value)}
                            required
                        />
                    </div>
                    <button
                        type="submit"
                        className="btn skeuo-btn-primary"
                        style={{ width: '100%', padding: '15px', fontSize: '16px', marginTop: '10px' }}
                        disabled={loading}
                    >
                        {loading ? 'Verifying...' : 'Activate Panel'}
                    </button>
                </form>

                <div style={{ marginTop: '20px', fontSize: '12px', color: 'var(--text-muted)' }}>
                    Don't have a license? <a href="#" style={{ color: 'var(--accent-cyan)', textDecoration: 'none' }}>Purchase one here</a>
                </div>
            </div>
        </div>
    );
}

'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();
    const router = useRouter();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await login(email, password);
            router.push('/dashboard');
        } catch (err) {
            setError(err.message || 'Invalid email or password');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-left">
                <div className="auth-card">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: 'var(--space-xl)' }}>
                        <div style={{
                            width: '42px', height: '42px', borderRadius: 'var(--radius-md)',
                            background: 'linear-gradient(135deg, var(--primary), var(--accent-cyan))',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontWeight: 800, color: 'white', fontSize: '16px'
                        }}>HS</div>
                        <span style={{ color: 'white', fontSize: '20px', fontWeight: 700 }}>HostingSignal</span>
                    </div>

                    <h1>Welcome back</h1>
                    <p>Sign in to your hosting control panel</p>

                    {error && (
                        <div className="alert alert-danger" style={{ marginBottom: 'var(--space-md)' }}>
                            ❌ {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label className="form-label">Email Address</label>
                            <input className="form-input" type="email" placeholder="you@example.com"
                                value={email} onChange={e => setEmail(e.target.value)} required />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Password</label>
                            <div style={{ position: 'relative' }}>
                                <input className="form-input" type={showPassword ? 'text' : 'password'}
                                    placeholder="Enter your password" value={password}
                                    onChange={e => setPassword(e.target.value)} required />
                                <button type="button" onClick={() => setShowPassword(!showPassword)} style={{
                                    position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
                                    background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)',
                                    cursor: 'pointer', fontSize: '16px'
                                }}>
                                    {showPassword ? '🙈' : '👁'}
                                </button>
                            </div>
                        </div>

                        <div className="auth-actions">
                            <label><input type="checkbox" /> Remember me</label>
                            <Link href="/auth/login">Forgot password?</Link>
                        </div>

                        <button type="submit" className="btn btn-primary" disabled={loading}
                            style={{ width: '100%', justifyContent: 'center', opacity: loading ? 0.7 : 1 }}>
                            {loading ? '⏳ Signing in...' : 'Sign In'}
                        </button>
                    </form>

                    <div className="auth-divider">or</div>

                    <button className="btn btn-secondary" style={{
                        width: '100%', justifyContent: 'center',
                        background: 'rgba(255,255,255,0.05)', borderColor: 'rgba(255,255,255,0.1)',
                        color: 'rgba(255,255,255,0.7)'
                    }}>
                        🔐 Sign in with SSO
                    </button>

                    <div className="auth-footer">
                        Don&apos;t have an account? <Link href="/auth/register">Sign up</Link>
                    </div>
                </div>
            </div>

            <div className="auth-right">
                <h2>Powerful Hosting<br />Made Simple</h2>
                <p>Manage websites, domains, emails, and databases with our modern control panel.</p>
                <ul className="auth-features">
                    <li><span>✓</span> One-click WordPress Installation</li>
                    <li><span>✓</span> Free SSL Certificates</li>
                    <li><span>✓</span> Advanced Security Scanner</li>
                    <li><span>✓</span> Docker Container Management</li>
                    <li><span>✓</span> License Distribution System</li>
                    <li><span>✓</span> White-label Customization</li>
                </ul>
            </div>
        </div>
    );
}

'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';

export default function RegisterPage() {
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [company, setCompany] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { register } = useAuth();
    const router = useRouter();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        if (password.length < 6) {
            setError('Password must be at least 6 characters');
            return;
        }
        setLoading(true);
        try {
            await register(name, email, password, company || undefined);
            router.push('/dashboard');
        } catch (err) {
            setError(err.message || 'Registration failed');
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

                    <h1>Create account</h1>
                    <p>Get started with HostingSignal</p>

                    {error && <div className="alert alert-danger" style={{ marginBottom: 'var(--space-md)' }}>❌ {error}</div>}

                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label className="form-label">Full Name</label>
                            <input className="form-input" placeholder="John Doe" value={name} onChange={e => setName(e.target.value)} required />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Email Address</label>
                            <input className="form-input" type="email" placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)} required />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Company (Optional)</label>
                            <input className="form-input" placeholder="Your Company" value={company} onChange={e => setCompany(e.target.value)} />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Password</label>
                            <input className="form-input" type="password" placeholder="Min 6 characters" value={password} onChange={e => setPassword(e.target.value)} required />
                        </div>

                        <button type="submit" className="btn btn-primary" disabled={loading}
                            style={{ width: '100%', justifyContent: 'center', marginTop: 'var(--space-md)', opacity: loading ? 0.7 : 1 }}>
                            {loading ? '⏳ Creating account...' : 'Create Account'}
                        </button>
                    </form>

                    <div className="auth-footer">
                        Already have an account? <Link href="/auth/login">Sign in</Link>
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

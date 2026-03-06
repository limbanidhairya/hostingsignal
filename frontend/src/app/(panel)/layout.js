'use client';
import { useRequireAuth } from '@/context/AuthContext';
import AppShell from '@/components/layout/AppShell';

export default function PanelLayout({ children }) {
    const { user, loading } = useRequireAuth();

    if (loading) {
        return (
            <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                height: '100vh', background: 'var(--bg-primary)'
            }}>
                <div style={{ textAlign: 'center' }}>
                    <div style={{
                        width: '48px', height: '48px', borderRadius: 'var(--radius-md)',
                        background: 'linear-gradient(135deg, var(--primary), var(--accent-cyan))',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontWeight: 800, color: 'white', fontSize: '18px', margin: '0 auto 16px'
                    }}>HS</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Loading HostingSignal...</div>
                </div>
            </div>
        );
    }

    if (!user) return null;

    return <AppShell>{children}</AppShell>;
}

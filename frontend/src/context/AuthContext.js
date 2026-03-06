'use client';
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import api from '@/lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    // Load user from storage on mount
    useEffect(() => {
        const stored = typeof window !== 'undefined' ? localStorage.getItem('hs_user') : null;
        const token = typeof window !== 'undefined' ? localStorage.getItem('hs_access_token') : null;
        if (stored && token) {
            setUser(JSON.parse(stored));
            // Verify token in background
            api.getMe().then(u => {
                setUser(u);
                localStorage.setItem('hs_user', JSON.stringify(u));
            }).catch(() => {
                // Token invalid
                api.clearTokens();
                setUser(null);
            }).finally(() => setLoading(false));
        } else {
            setLoading(false);
        }
    }, []);

    const login = useCallback(async (email, password, totpCode) => {
        const data = await api.login(email, password, totpCode);
        setUser(data.user);
        return data;
    }, []);

    const register = useCallback(async (name, email, password, company) => {
        const data = await api.register(name, email, password, company);
        setUser(data.user);
        return data;
    }, []);

    const logout = useCallback(() => {
        api.clearTokens();
        setUser(null);
        router.push('/auth/login');
    }, [router]);

    const refreshUser = useCallback(async () => {
        try {
            const u = await api.getMe();
            setUser(u);
            localStorage.setItem('hs_user', JSON.stringify(u));
            return u;
        } catch {
            return null;
        }
    }, []);

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) throw new Error('useAuth must be used within AuthProvider');
    return context;
}

export function useRequireAuth() {
    const { user, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!loading && !user) {
            router.push('/auth/login');
        }
    }, [user, loading, router]);

    return { user, loading };
}

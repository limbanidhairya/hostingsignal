'use client';
import { useState } from 'react';

export default function Header({ title }) {
    const [searchQuery, setSearchQuery] = useState('');

    return (
        <header className="hs-header">
            <div className="hs-header-left">
                <h1 className="hs-header-title">{title || 'Dashboard'}</h1>
            </div>
            <div className="hs-header-right">
                <div className="hs-search">
                    <span style={{ opacity: 0.5 }}>🔍</span>
                    <input
                        type="text"
                        placeholder="Search..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                    <kbd style={{ fontSize: '11px', padding: '2px 6px', background: 'var(--hs-bg-primary)', borderRadius: '4px', color: 'var(--hs-text-muted)', border: '1px solid var(--hs-border)' }}>⌘K</kbd>
                </div>
                <button className="hs-btn hs-btn-secondary hs-btn-sm" style={{ borderRadius: '50%', width: '36px', height: '36px', padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    🔔
                </button>
                <div style={{ width: '34px', height: '34px', borderRadius: '50%', background: 'linear-gradient(135deg, var(--hs-primary), var(--hs-accent))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px', fontWeight: '700', cursor: 'pointer' }}>
                    A
                </div>
            </div>
        </header>
    );
}

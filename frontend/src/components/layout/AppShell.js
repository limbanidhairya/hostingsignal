'use client';
import { useState } from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';

export default function AppShell({ children }) {
    const [collapsed, setCollapsed] = useState(false);

    return (
        <div className="app-layout">
            <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
            <div className={`main-area ${collapsed ? 'collapsed' : ''}`}>
                <TopBar collapsed={collapsed} />
                <main className="page-content">
                    {children}
                </main>
            </div>
        </div>
    );
}

'use client';
import { useState } from 'react';

const PHP_VERSIONS = [
    { version: '7.4', status: 'eol', label: 'PHP 7.4 (EOL)', installed: false },
    { version: '8.0', status: 'eol', label: 'PHP 8.0 (EOL)', installed: false },
    { version: '8.1', status: 'supported', label: 'PHP 8.1', installed: true },
    { version: '8.2', status: 'supported', label: 'PHP 8.2', installed: true },
    { version: '8.3', status: 'active', label: 'PHP 8.3 (Latest)', installed: true },
];

const EXTENSIONS = [
    { name: 'curl', description: 'Client URL library', enabled: true },
    { name: 'imagick', description: 'ImageMagick image processing', enabled: false },
    { name: 'gd', description: 'Image processing library', enabled: true },
    { name: 'mysqli', description: 'MySQL improved extension', enabled: true },
    { name: 'pdo', description: 'PHP Data Objects', enabled: true },
    { name: 'zip', description: 'Archive compression', enabled: true },
    { name: 'intl', description: 'Internationalization functions', enabled: false },
    { name: 'opcache', description: 'Opcode cache for performance', enabled: true },
    { name: 'redis', description: 'Redis PHP extension', enabled: false },
    { name: 'mbstring', description: 'Multibyte string support', enabled: true },
    { name: 'xml', description: 'XML parser', enabled: true },
    { name: 'bcmath', description: 'Arbitrary precision math', enabled: false },
];

const WEBSITES = [
    { domain: 'example.com', phpVersion: '8.2' },
    { domain: 'mysite.net', phpVersion: '8.3' },
    { domain: 'legacy-app.org', phpVersion: '7.4' },
];

export default function PHPManagerPage() {
    const [versions, setVersions] = useState(PHP_VERSIONS);
    const [extensions, setExtensions] = useState(EXTENSIONS);
    const [websites, setWebsites] = useState(WEBSITES);
    const [selectedVersion, setSelectedVersion] = useState('8.3');
    const [activeTab, setActiveTab] = useState('versions');
    const [installing, setInstalling] = useState(null);

    const toggleInstall = (ver) => {
        setInstalling(ver);
        setTimeout(() => {
            setVersions(prev => prev.map(v =>
                v.version === ver ? { ...v, installed: !v.installed } : v
            ));
            setInstalling(null);
        }, 2000);
    };

    const toggleExtension = (name) => {
        setExtensions(prev => prev.map(e =>
            e.name === name ? { ...e, enabled: !e.enabled } : e
        ));
    };

    const switchVersion = (domain, newVersion) => {
        setWebsites(prev => prev.map(w =>
            w.domain === domain ? { ...w, phpVersion: newVersion } : w
        ));
    };

    const installedVersions = versions.filter(v => v.installed);

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <div>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: 700 }}>PHP Version Manager</h2>
                    <p style={{ fontSize: 14, color: 'var(--hs-text-muted)', marginTop: 4 }}>
                        Install, switch, and manage PHP versions and extensions
                    </p>
                </div>
            </div>

            {/* Stats Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
                <div className="hs-card" style={{ textAlign: 'center', padding: '20px 16px' }}>
                    <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--hs-primary)' }}>{installedVersions.length}</div>
                    <div style={{ fontSize: 12, color: 'var(--hs-text-muted)', marginTop: 4 }}>Installed Versions</div>
                </div>
                <div className="hs-card" style={{ textAlign: 'center', padding: '20px 16px' }}>
                    <div style={{ fontSize: 28, fontWeight: 700, color: '#10b981' }}>{extensions.filter(e => e.enabled).length}</div>
                    <div style={{ fontSize: 12, color: 'var(--hs-text-muted)', marginTop: 4 }}>Active Extensions</div>
                </div>
                <div className="hs-card" style={{ textAlign: 'center', padding: '20px 16px' }}>
                    <div style={{ fontSize: 28, fontWeight: 700, color: '#f59e0b' }}>{websites.length}</div>
                    <div style={{ fontSize: 12, color: 'var(--hs-text-muted)', marginTop: 4 }}>Websites</div>
                </div>
                <div className="hs-card" style={{ textAlign: 'center', padding: '20px 16px' }}>
                    <div style={{ fontSize: 28, fontWeight: 700, color: '#8b5cf6' }}>8.3</div>
                    <div style={{ fontSize: 12, color: 'var(--hs-text-muted)', marginTop: 4 }}>Default Version</div>
                </div>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid var(--hs-border)', paddingBottom: 8 }}>
                {['versions', 'extensions', 'websites'].map(tab => (
                    <button key={tab} onClick={() => setActiveTab(tab)}
                        style={{
                            padding: '8px 20px', borderRadius: 6, border: 'none', cursor: 'pointer',
                            background: activeTab === tab ? 'var(--hs-primary)' : 'transparent',
                            color: activeTab === tab ? 'white' : 'var(--hs-text-secondary)',
                            fontWeight: 500, fontSize: 14, transition: 'all 0.2s',
                        }}>
                        {tab === 'versions' ? '📦 PHP Versions' : tab === 'extensions' ? '🔌 Extensions' : '🌐 Per-Site PHP'}
                    </button>
                ))}
            </div>

            {/* PHP Versions Tab */}
            {activeTab === 'versions' && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
                    {versions.map(v => (
                        <div key={v.version} className="hs-card" style={{
                            padding: 20,
                            border: v.installed ? '1px solid rgba(16,185,129,0.3)' : '1px solid var(--hs-border)',
                            position: 'relative', overflow: 'hidden',
                        }}>
                            {v.installed && (
                                <div style={{
                                    position: 'absolute', top: 12, right: 12,
                                    background: 'rgba(16,185,129,0.15)', color: '#10b981',
                                    padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 600
                                }}>
                                    ● Installed
                                </div>
                            )}
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                                <div style={{
                                    width: 44, height: 44, borderRadius: 10,
                                    background: v.status === 'active' ? 'linear-gradient(135deg, #8b5cf6, #6d28d9)' :
                                        v.status === 'supported' ? 'linear-gradient(135deg, #3b82f6, #2563eb)' :
                                            'linear-gradient(135deg, #6b7280, #4b5563)',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontWeight: 700, color: 'white', fontSize: 13,
                                }}>
                                    {v.version}
                                </div>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: 15 }}>{v.label}</div>
                                    <div style={{ fontSize: 12, color: 'var(--hs-text-muted)' }}>
                                        {v.status === 'active' ? 'Active support' : v.status === 'supported' ? 'Security fixes' : 'End of life'}
                                    </div>
                                </div>
                            </div>
                            <button
                                className={`hs-btn ${v.installed ? 'hs-btn-danger' : 'hs-btn-primary'} hs-btn-sm`}
                                style={{ width: '100%' }}
                                disabled={installing !== null}
                                onClick={() => toggleInstall(v.version)}
                            >
                                {installing === v.version ? '⏳ Processing...' : v.installed ? 'Uninstall' : 'Install'}
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* Extensions Tab */}
            {activeTab === 'extensions' && (
                <div>
                    <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: 14, color: 'var(--hs-text-muted)' }}>
                            Managing extensions for PHP {selectedVersion}
                        </span>
                        <select className="hs-input hs-select" style={{ width: 140 }}
                            value={selectedVersion} onChange={e => setSelectedVersion(e.target.value)}>
                            {installedVersions.map(v => (
                                <option key={v.version} value={v.version}>PHP {v.version}</option>
                            ))}
                        </select>
                    </div>
                    <div className="hs-card" style={{ padding: 0, overflow: 'hidden' }}>
                        <table className="hs-table">
                            <thead><tr><th>Extension</th><th>Description</th><th>Status</th><th>Action</th></tr></thead>
                            <tbody>
                                {extensions.map(ext => (
                                    <tr key={ext.name}>
                                        <td style={{ fontWeight: 600, fontFamily: 'monospace' }}>{ext.name}</td>
                                        <td style={{ color: 'var(--hs-text-secondary)', fontSize: 13 }}>{ext.description}</td>
                                        <td>
                                            <span className={`hs-badge ${ext.enabled ? 'success' : ''}`}
                                                style={ext.enabled ? {} : { background: 'rgba(107,114,128,0.15)', color: '#9ca3af' }}>
                                                {ext.enabled ? 'Enabled' : 'Disabled'}
                                            </span>
                                        </td>
                                        <td>
                                            <button
                                                className={`hs-btn hs-btn-sm ${ext.enabled ? 'hs-btn-secondary' : 'hs-btn-primary'}`}
                                                onClick={() => toggleExtension(ext.name)}
                                                style={{ minWidth: 80 }}
                                            >
                                                {ext.enabled ? 'Disable' : 'Enable'}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Per-Site PHP Tab */}
            {activeTab === 'websites' && (
                <div className="hs-card" style={{ padding: 0, overflow: 'hidden' }}>
                    <table className="hs-table">
                        <thead><tr><th>Website</th><th>Current PHP</th><th>Switch Version</th></tr></thead>
                        <tbody>
                            {websites.map(w => (
                                <tr key={w.domain}>
                                    <td style={{ fontWeight: 600 }}>🌐 {w.domain}</td>
                                    <td><span className="hs-badge info">PHP {w.phpVersion}</span></td>
                                    <td>
                                        <select className="hs-input hs-select" style={{ width: 140 }}
                                            value={w.phpVersion}
                                            onChange={e => switchVersion(w.domain, e.target.value)}>
                                            {installedVersions.map(v => (
                                                <option key={v.version} value={v.version}>PHP {v.version}</option>
                                            ))}
                                        </select>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

'use client';
import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

export default function FilesPage() {
    const { showToast, ToastContainer } = useToast();
    const [items, setItems] = useState([]);
    const [currentPath, setCurrentPath] = useState('/home');
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState(null);
    const [editContent, setEditContent] = useState('');
    const [showMkdir, setShowMkdir] = useState(false);
    const [newDir, setNewDir] = useState('');
    const [showRename, setShowRename] = useState(null);
    const [renameTo, setRenameTo] = useState('');

    useEffect(() => { loadFiles(currentPath); }, [currentPath]);

    async function loadFiles(path) {
        setLoading(true);
        try { const data = await api.getFiles(path); setItems(Array.isArray(data) ? data : []); }
        catch { showToast('Failed to load files', 'error'); }
        finally { setLoading(false); }
    }

    function navigateTo(name) {
        const sep = currentPath.endsWith('/') ? '' : '/';
        setCurrentPath(currentPath + sep + name);
    }

    function goUp() {
        const parts = currentPath.split('/').filter(Boolean);
        parts.pop();
        setCurrentPath('/' + parts.join('/'));
    }

    async function handleEdit(path) {
        try { const data = await api.readFile(path); setEditContent(data.content); setEditing(path); }
        catch { showToast('Cannot read file', 'error'); }
    }

    async function handleSave() {
        try { await api.writeFile(editing, editContent); showToast('File saved', 'success'); setEditing(null); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    async function handleDelete(path) {
        if (!confirm(`Delete ${path}?`)) return;
        try { await api.deleteFile(path); showToast('Deleted', 'success'); loadFiles(currentPath); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    async function handleMkdir() {
        if (!newDir) return;
        const path = currentPath + (currentPath.endsWith('/') ? '' : '/') + newDir;
        try { await api.createDirectory(path); showToast('Directory created', 'success'); setShowMkdir(false); setNewDir(''); loadFiles(currentPath); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    async function handleRename() {
        if (!renameTo || !showRename) return;
        try { await api.renameFile(showRename, renameTo); showToast('Renamed', 'success'); setShowRename(null); setRenameTo(''); loadFiles(currentPath); }
        catch (e) { showToast('Failed: ' + e.message, 'error'); }
    }

    const icon = (item) => item.type === 'directory' ? '📁' : item.name?.endsWith('.php') ? '🐘' : item.name?.endsWith('.js') ? '📜' : item.name?.endsWith('.html') ? '🌐' : item.name?.endsWith('.css') ? '🎨' : item.name?.endsWith('.json') ? '📋' : '📄';

    return (
        <div className="animate-fade">
            <ToastContainer />
            <div className="page-header"><div><h1 className="glow-text">File Manager</h1><p>Browse and manage server files</p></div>
                <button className="btn skeuo-btn-primary" onClick={() => setShowMkdir(true)}>+ New Folder</button></div>

            {/* Breadcrumb */}
            <div className="card liquid-glass" style={{ marginBottom: 'var(--space-md)', padding: 'var(--space-sm) var(--space-lg)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <button className="btn btn-sm skeuo-btn" onClick={goUp} disabled={currentPath === '/'}>⬆ Up</button>
                <span style={{ fontFamily: 'monospace', fontSize: 13, color: 'var(--text-secondary)', marginLeft: 8 }}>📂 {currentPath}</span>
            </div>

            {loading ? <div style={{ padding: 40, textAlign: 'center' }}>⏳ Loading...</div> : (
                <div className="table-container liquid-glass"><table><thead><tr><th>Name</th><th>Type</th><th>Size</th><th>Permissions</th><th>Actions</th></tr></thead>
                    <tbody>{items.map((item, i) => (
                        <tr key={i}>
                            <td>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: item.type === 'directory' ? 'pointer' : 'default' }}
                                    onClick={() => item.type === 'directory' && navigateTo(item.name)}>
                                    <span style={{ fontSize: 18 }}>{icon(item)}</span>
                                    <span style={{ fontWeight: 600, color: item.type === 'directory' ? 'var(--primary)' : 'inherit' }}>{item.name}</span>
                                </div>
                            </td>
                            <td><span className={`badge ${item.type === 'directory' ? 'badge-info' : 'badge-muted'}`}>{item.type}</span></td>
                            <td>{item.size || '-'}</td>
                            <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{item.permissions || '-'}</td>
                            <td><div style={{ display: 'flex', gap: 4 }}>
                                {item.type === 'file' && <button className="btn btn-sm skeuo-btn" onClick={() => handleEdit(currentPath + '/' + item.name)}>✏️</button>}
                                <button className="btn btn-sm skeuo-btn" onClick={() => { setShowRename(currentPath + '/' + item.name); setRenameTo(item.name); }}>📝</button>
                                <button className="btn btn-sm btn-danger skeuo-btn" style={{ background: 'var(--accent-red)' }} onClick={() => handleDelete(currentPath + '/' + item.name)}>✕</button>
                            </div></td>
                        </tr>
                    ))}</tbody></table></div>
            )}

            {editing && (
                <div className="modal-overlay" onClick={() => setEditing(null)}><div className="modal liquid-glass" style={{ maxWidth: 800 }} onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h2 className="modal-title glow-text">Edit: {editing.split('/').pop()}</h2><button className="modal-close" onClick={() => setEditing(null)}>✕</button></div>
                    <div className="modal-body"><textarea className="form-input" style={{ height: 350, fontFamily: 'monospace', fontSize: 13, resize: 'vertical', background: 'rgba(0,0,0,0.2)' }} value={editContent} onChange={e => setEditContent(e.target.value)} /></div>
                    <div className="modal-footer"><button className="btn skeuo-btn" onClick={() => setEditing(null)}>Cancel</button><button className="btn skeuo-btn-primary" onClick={handleSave}>💾 Save</button></div>
                </div></div>
            )}

            {showMkdir && (
                <div className="modal-overlay" onClick={() => setShowMkdir(false)}><div className="modal liquid-glass" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h2 className="modal-title glow-text">New Folder</h2><button className="modal-close" onClick={() => setShowMkdir(false)}>✕</button></div>
                    <div className="modal-body"><div className="form-group"><label className="form-label">Folder Name</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} placeholder="new_folder" value={newDir} onChange={e => setNewDir(e.target.value)} /></div></div>
                    <div className="modal-footer"><button className="btn skeuo-btn" onClick={() => setShowMkdir(false)}>Cancel</button><button className="btn skeuo-btn-primary" onClick={handleMkdir}>Create</button></div>
                </div></div>
            )}

            {showRename && (
                <div className="modal-overlay" onClick={() => setShowRename(null)}><div className="modal liquid-glass" onClick={e => e.stopPropagation()}>
                    <div className="modal-header"><h2 className="modal-title glow-text">Rename</h2><button className="modal-close" onClick={() => setShowRename(null)}>✕</button></div>
                    <div className="modal-body"><div className="form-group"><label className="form-label">New Name</label><input className="form-input" style={{ background: 'rgba(0,0,0,0.2)' }} value={renameTo} onChange={e => setRenameTo(e.target.value)} /></div></div>
                    <div className="modal-footer"><button className="btn skeuo-btn" onClick={() => setShowRename(null)}>Cancel</button><button className="btn skeuo-btn-primary" onClick={handleRename}>Rename</button></div>
                </div></div>
            )}
        </div>
    );
}

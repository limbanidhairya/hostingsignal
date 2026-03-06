'use client';
import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

export default function UsersPage() {
    const { showToast, ToastContainer } = useToast();
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [search, setSearch] = useState('');
    const [roleFilter, setRoleFilter] = useState('');

    // Form state
    const [formName, setFormName] = useState('');
    const [formEmail, setFormEmail] = useState('');
    const [formPassword, setFormPassword] = useState('');
    const [formRole, setFormRole] = useState('client');
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => { loadUsers(); }, []);

    async function loadUsers() {
        setLoading(true);
        try {
            const data = await api.getUsers();
            setUsers(data);
        } catch (err) {
            showToast('Failed to load users: ' + err.message, 'error');
        } finally {
            setLoading(false);
        }
    }

    async function handleCreate(e) {
        e.preventDefault();
        setSubmitting(true);
        try {
            await api.createUser(formEmail, formName, formPassword, formRole);
            showToast('User created successfully!', 'success');
            setShowCreate(false);
            setFormName(''); setFormEmail(''); setFormPassword(''); setFormRole('client');
            loadUsers();
        } catch (err) {
            showToast('Failed to create user: ' + err.message, 'error');
        } finally {
            setSubmitting(false);
        }
    }

    async function handleToggleActive(user) {
        try {
            await api.updateUser(user.id, { is_active: !user.is_active });
            showToast(`User ${user.is_active ? 'disabled' : 'enabled'}`, 'success');
            loadUsers();
        } catch (err) {
            showToast('Failed to update user: ' + err.message, 'error');
        }
    }

    async function handleChangeRole(user, newRole) {
        try {
            await api.updateUser(user.id, { role: newRole });
            showToast(`${user.name} role changed to ${newRole}`, 'success');
            loadUsers();
        } catch (err) {
            showToast('Failed to update role: ' + err.message, 'error');
        }
    }

    async function handleDelete(user) {
        if (!confirm(`Delete user ${user.name} (${user.email})?`)) return;
        try {
            await api.deleteUser(user.id);
            showToast('User deleted', 'success');
            loadUsers();
        } catch (err) {
            showToast('Failed to delete: ' + err.message, 'error');
        }
    }

    const filtered = users.filter(u => {
        if (roleFilter && u.role !== roleFilter) return false;
        if (search) {
            const s = search.toLowerCase();
            return u.name.toLowerCase().includes(s) || u.email.toLowerCase().includes(s);
        }
        return true;
    });

    const roleBadge = (role) => {
        const colors = { admin: 'badge-danger', reseller: 'badge-purple', client: 'badge-info' };
        return <span className={`badge ${colors[role] || 'badge-info'}`}>{role}</span>;
    };

    if (loading) {
        return <div className="animate-fade" style={{ padding: 'var(--space-xl)', textAlign: 'center', color: 'var(--text-muted)' }}>Loading users...</div>;
    }

    return (
        <div className="animate-fade">
            <ToastContainer />
            <div className="page-header">
                <div>
                    <h1>User Management</h1>
                    <p>Manage panel users, roles, and permissions</p>
                </div>
                <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ Add User</button>
            </div>

            {/* Stats */}
            <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
                <div className="stat-card blue">
                    <div className="stat-icon blue">👥</div>
                    <div className="stat-content">
                        <div className="stat-value">{users.length}</div>
                        <div className="stat-label">Total Users</div>
                    </div>
                </div>
                <div className="stat-card green">
                    <div className="stat-icon green">✅</div>
                    <div className="stat-content">
                        <div className="stat-value">{users.filter(u => u.is_active).length}</div>
                        <div className="stat-label">Active</div>
                    </div>
                </div>
                <div className="stat-card purple">
                    <div className="stat-icon purple">👑</div>
                    <div className="stat-content">
                        <div className="stat-value">{users.filter(u => u.role === 'admin').length}</div>
                        <div className="stat-label">Admins</div>
                    </div>
                </div>
                <div className="stat-card orange">
                    <div className="stat-icon orange">🏢</div>
                    <div className="stat-content">
                        <div className="stat-value">{users.filter(u => u.role === 'reseller').length}</div>
                        <div className="stat-label">Resellers</div>
                    </div>
                </div>
            </div>

            {/* Users Table */}
            <div className="table-container">
                <div className="table-header">
                    <span className="table-title">All Users ({filtered.length})</span>
                    <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                        <select className="form-input form-select" style={{ width: '130px' }}
                            value={roleFilter} onChange={e => setRoleFilter(e.target.value)}>
                            <option value="">All Roles</option>
                            <option value="admin">Admin</option>
                            <option value="reseller">Reseller</option>
                            <option value="client">Client</option>
                        </select>
                        <input className="form-input" placeholder="Search..." style={{ width: '200px' }}
                            value={search} onChange={e => setSearch(e.target.value)} />
                    </div>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>User</th>
                            <th>Role</th>
                            <th>Status</th>
                            <th>2FA</th>
                            <th>Last Login</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.map(u => (
                            <tr key={u.id}>
                                <td>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                        <div className="user-avatar" style={{ width: '34px', height: '34px', fontSize: '12px' }}>
                                            {u.name.split(' ').map(n => n[0]).join('').toUpperCase()}
                                        </div>
                                        <div>
                                            <div style={{ fontWeight: 600 }}>{u.name}</div>
                                            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{u.email}</div>
                                        </div>
                                    </div>
                                </td>
                                <td>
                                    <select className="form-input form-select" style={{ width: '100px', padding: '4px 8px', fontSize: '12px' }}
                                        value={u.role} onChange={e => handleChangeRole(u, e.target.value)}>
                                        <option value="admin">Admin</option>
                                        <option value="reseller">Reseller</option>
                                        <option value="client">Client</option>
                                    </select>
                                </td>
                                <td>
                                    <span className={`badge badge-dot ${u.is_active ? 'badge-success' : 'badge-danger'}`}>
                                        {u.is_active ? 'Active' : 'Disabled'}
                                    </span>
                                </td>
                                <td>
                                    <span className={`badge ${u.totp_enabled ? 'badge-success' : 'badge-warning'}`}>
                                        {u.totp_enabled ? '🔒 On' : '⚠️ Off'}
                                    </span>
                                </td>
                                <td style={{ fontSize: '12px' }}>{u.last_login ? new Date(u.last_login).toLocaleString() : 'Never'}</td>
                                <td style={{ fontSize: '12px' }}>{new Date(u.created_at).toLocaleDateString()}</td>
                                <td>
                                    <div style={{ display: 'flex', gap: '4px' }}>
                                        <button className="btn btn-sm btn-outline" onClick={() => handleToggleActive(u)}>
                                            {u.is_active ? 'Disable' : 'Enable'}
                                        </button>
                                        <button className="btn btn-sm btn-outline" style={{ color: 'var(--accent-red)' }} onClick={() => handleDelete(u)}>Delete</button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Create User Modal */}
            {showCreate && (
                <div className="modal-overlay" onClick={() => setShowCreate(false)}>
                    <div className="modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2 className="modal-title">Add New User</h2>
                            <button className="modal-close" onClick={() => setShowCreate(false)}>✕</button>
                        </div>
                        <form onSubmit={handleCreate}>
                            <div className="modal-body">
                                <div className="form-group">
                                    <label className="form-label">Full Name *</label>
                                    <input className="form-input" placeholder="John Doe" value={formName} onChange={e => setFormName(e.target.value)} required />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Email *</label>
                                    <input className="form-input" type="email" placeholder="user@example.com" value={formEmail} onChange={e => setFormEmail(e.target.value)} required />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Password *</label>
                                    <input className="form-input" type="password" placeholder="Min 6 characters" value={formPassword} onChange={e => setFormPassword(e.target.value)} required />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Role</label>
                                    <select className="form-input form-select" value={formRole} onChange={e => setFormRole(e.target.value)}>
                                        <option value="client">Client</option>
                                        <option value="reseller">Reseller</option>
                                        <option value="admin">Admin</option>
                                    </select>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
                                <button type="submit" className="btn btn-primary" disabled={submitting}>
                                    {submitting ? '⏳ Creating...' : '👤 Create User'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

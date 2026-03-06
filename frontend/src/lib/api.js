class ApiClient {
    constructor() {
        this.baseUrl = typeof window !== 'undefined'
            ? (process.env.NEXT_PUBLIC_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`)
            : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');
    }

    getToken() {
        if (typeof window !== 'undefined') {
            return localStorage.getItem('hs_access_token');
        }
        return null;
    }

    setTokens(access, refresh) {
        if (typeof window !== 'undefined') {
            localStorage.setItem('hs_access_token', access);
            localStorage.setItem('hs_refresh_token', refresh);
        }
    }

    clearTokens() {
        if (typeof window !== 'undefined') {
            localStorage.removeItem('hs_access_token');
            localStorage.removeItem('hs_refresh_token');
            localStorage.removeItem('hs_user');
        }
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(url, {
            ...options,
            headers,
        });

        // Handle 401 — try refresh
        if (response.status === 401 && token) {
            const refreshed = await this.refreshToken();
            if (refreshed) {
                headers['Authorization'] = `Bearer ${this.getToken()}`;
                const retry = await fetch(url, { ...options, headers });
                if (!retry.ok) {
                    if (retry.status === 402) {
                        if (typeof window !== 'undefined' && !window.location.pathname.includes('/license-required')) {
                            window.location.href = '/license-required';
                        }
                        throw new ApiError(retry.status, 'License required');
                    }
                    const err = await retry.json().catch(() => ({ detail: 'Request failed' }));
                    throw new ApiError(retry.status, err.detail || 'Request failed');
                }
                return retry.json();
            } else {
                this.clearTokens();
                if (typeof window !== 'undefined') {
                    window.location.href = '/auth/login';
                }
                throw new ApiError(401, 'Session expired');
            }
        }

        if (!response.ok) {
            if (response.status === 402) {
                if (typeof window !== 'undefined' && !window.location.pathname.includes('/license-required')) {
                    window.location.href = '/license-required';
                }
                throw new ApiError(response.status, 'License required');
            }
            const err = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new ApiError(response.status, err.detail || 'Request failed');
        }

        if (response.status === 204) return null;
        return response.json();
    }

    async refreshToken() {
        try {
            const refresh = typeof window !== 'undefined' ? localStorage.getItem('hs_refresh_token') : null;
            if (!refresh) return false;

            const res = await fetch(`${this.baseUrl}/api/auth/refresh?refresh_token=${encodeURIComponent(refresh)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (!res.ok) return false;

            const data = await res.json();
            this.setTokens(data.access_token, data.refresh_token);
            return true;
        } catch {
            return false;
        }
    }

    // ===== Auth =====
    async login(email, password, totpCode) {
        const body = { email, password };
        if (totpCode) body.totp_code = totpCode;
        const data = await this.request('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify(body),
        });
        this.setTokens(data.access_token, data.refresh_token);
        if (typeof window !== 'undefined') {
            localStorage.setItem('hs_user', JSON.stringify(data.user));
        }
        return data;
    }

    async register(name, email, password, company) {
        const data = await this.request('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify({ name, email, password, company }),
        });
        this.setTokens(data.access_token, data.refresh_token);
        if (typeof window !== 'undefined') {
            localStorage.setItem('hs_user', JSON.stringify(data.user));
        }
        return data;
    }

    async getMe() {
        return this.request('/api/auth/me');
    }

    async updateMe(data) {
        return this.request('/api/auth/me', {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async changePassword(currentPassword, newPassword) {
        return this.request('/api/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
        });
    }

    async enable2FA() {
        return this.request('/api/auth/2fa/enable', { method: 'POST' });
    }

    async verify2FA(code) {
        return this.request(`/api/auth/2fa/verify?code=${code}`, { method: 'POST' });
    }

    // ===== Licenses =====
    async getLicenses(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/api/licenses/?${query}`);
    }

    async issueLicense(data) {
        return this.request('/api/licenses/', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getLicense(id) {
        return this.request(`/api/licenses/${id}`);
    }

    async updateLicense(id, data) {
        return this.request(`/api/licenses/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async revokeLicense(id) {
        return this.request(`/api/licenses/${id}`, { method: 'DELETE' });
    }

    async getLicenseStats() {
        return this.request('/api/licenses/stats');
    }

    async validateLicense(licenseKey, serverIp, serverHostname) {
        return this.request('/api/licenses/validate', {
            method: 'POST',
            body: JSON.stringify({ license_key: licenseKey, server_ip: serverIp, server_hostname: serverHostname }),
        });
    }

    async activateLicense(licenseKey, serverIp, serverHostname) {
        return this.request('/api/licenses/activate', {
            method: 'POST',
            body: JSON.stringify({ license_key: licenseKey, server_ip: serverIp, server_hostname: serverHostname }),
        });
    }

    // ===== Admin =====
    async getDashboardStats() {
        return this.request('/api/admin/dashboard');
    }

    async getUsers(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/api/admin/users?${query}`);
    }

    async createUser(email, name, password, role) {
        return this.request(`/api/admin/users?email=${encodeURIComponent(email)}&name=${encodeURIComponent(name)}&password=${encodeURIComponent(password)}&role=${role}`, {
            method: 'POST',
        });
    }

    async updateUser(id, data) {
        const params = new URLSearchParams();
        if (data.name) params.set('name', data.name);
        if (data.role) params.set('role', data.role);
        if (data.is_active !== undefined) params.set('is_active', data.is_active);
        return this.request(`/api/admin/users/${id}?${params.toString()}`, { method: 'PUT' });
    }

    async deleteUser(id) {
        return this.request(`/api/admin/users/${id}`, { method: 'DELETE' });
    }

    // ===== Tiers =====
    async getTiers() {
        return this.request('/api/tiers');
    }

    // ===== Health =====
    async health() {
        return this.request('/api/health');
    }

    // ===== Server Management =====

    // Websites
    async getWebsites() { return this.request('/api/server/websites'); }
    async createWebsite(domain, phpVersion = '8.2') { return this.request('/api/server/websites', { method: 'POST', body: JSON.stringify({ domain, php_version: phpVersion }) }); }
    async deleteWebsite(domain) { return this.request(`/api/server/websites/${domain}`, { method: 'DELETE' }); }
    async changePhpVersion(domain, version) { return this.request(`/api/server/websites/${domain}/php`, { method: 'PUT', body: JSON.stringify({ version }) }); }
    async getWebserverStatus() { return this.request('/api/server/webserver/status'); }

    // DNS
    async getDnsZones() { return this.request('/api/server/dns/zones'); }
    async getDnsZone(domain) { return this.request(`/api/server/dns/zones/${domain}`); }
    async createDnsZone(domain) { return this.request('/api/server/dns/zones', { method: 'POST', body: JSON.stringify({ domain }) }); }
    async addDnsRecord(domain, name, type, content, ttl = 3600) { return this.request(`/api/server/dns/zones/${domain}/records`, { method: 'POST', body: JSON.stringify({ name, type, content, ttl }) }); }
    async deleteDnsRecord(domain, name, type) { return this.request(`/api/server/dns/zones/${domain}/records?name=${encodeURIComponent(name)}&type=${type}`, { method: 'DELETE' }); }
    async deleteDnsZone(domain) { return this.request(`/api/server/dns/zones/${domain}`, { method: 'DELETE' }); }

    // Email
    async getEmailAccounts(domain) { return this.request(`/api/server/email/accounts${domain ? `?domain=${domain}` : ''}`); }
    async createEmailAccount(email, password, quotaMb = 1024) { return this.request('/api/server/email/accounts', { method: 'POST', body: JSON.stringify({ email, password, quota_mb: quotaMb }) }); }
    async deleteEmailAccount(email) { return this.request(`/api/server/email/accounts/${encodeURIComponent(email)}`, { method: 'DELETE' }); }
    async getEmailAliases(domain) { return this.request(`/api/server/email/aliases${domain ? `?domain=${domain}` : ''}`); }
    async createEmailAlias(source, destination) { return this.request('/api/server/email/aliases', { method: 'POST', body: JSON.stringify({ source, destination }) }); }
    async setupDkim(domain) { return this.request(`/api/server/email/dkim/${domain}`, { method: 'POST' }); }

    // Databases
    async getDatabases() { return this.request('/api/server/databases'); }
    async createDatabase(name, username, password) { return this.request('/api/server/databases', { method: 'POST', body: JSON.stringify({ name, username, password }) }); }
    async deleteDatabase(name, dropUser) { return this.request(`/api/server/databases/${name}${dropUser ? `?drop_user=${dropUser}` : ''}`, { method: 'DELETE' }); }

    // SSL
    async getSSLCertificates() { return this.request('/api/server/ssl/certificates'); }
    async issueSSL(domain, email, wildcard = false) { return this.request('/api/server/ssl/certificates', { method: 'POST', body: JSON.stringify({ domain, email, wildcard }) }); }
    async renewSSL(domain) { return this.request(`/api/server/ssl/certificates/${domain}/renew`, { method: 'POST' }); }
    async revokeSSL(domain) { return this.request(`/api/server/ssl/certificates/${domain}`, { method: 'DELETE' }); }

    // Firewall
    async getFirewallRules() { return this.request('/api/server/firewall/rules'); }
    async openPort(port, protocol = 'tcp') { return this.request('/api/server/firewall/ports', { method: 'POST', body: JSON.stringify({ port, protocol }) }); }
    async closePort(port, protocol = 'tcp') { return this.request(`/api/server/firewall/ports/${port}?protocol=${protocol}`, { method: 'DELETE' }); }
    async getBlockedIPs() { return this.request('/api/server/firewall/blocked'); }
    async blockIP(ip, reason = '') { return this.request('/api/server/firewall/block', { method: 'POST', body: JSON.stringify({ ip, reason }) }); }
    async unblockIP(ip) { return this.request(`/api/server/firewall/block/${ip}`, { method: 'DELETE' }); }
    async getFirewallStatus() { return this.request('/api/server/firewall/status'); }

    // FTP
    async getFTPAccounts() { return this.request('/api/server/ftp/accounts'); }
    async createFTPAccount(username, password, directory, quotaMb = 0) { return this.request('/api/server/ftp/accounts', { method: 'POST', body: JSON.stringify({ username, password, directory, quota_mb: quotaMb }) }); }
    async deleteFTPAccount(username) { return this.request(`/api/server/ftp/accounts/${username}`, { method: 'DELETE' }); }

    // File Manager
    async getFiles(path = '/') { return this.request(`/api/server/files?path=${encodeURIComponent(path)}`); }
    async readFile(path) { return this.request(`/api/server/files/read?path=${encodeURIComponent(path)}`); }
    async writeFile(path, content) { return this.request('/api/server/files/write', { method: 'POST', body: JSON.stringify({ path, content }) }); }
    async createDirectory(path) { return this.request('/api/server/files/mkdir', { method: 'POST', body: JSON.stringify({ path }) }); }
    async deleteFile(path) { return this.request(`/api/server/files?path=${encodeURIComponent(path)}`, { method: 'DELETE' }); }
    async renameFile(path, newName) { return this.request('/api/server/files/rename', { method: 'POST', body: JSON.stringify({ path, new_name: newName }) }); }

    // Backups
    async getBackups(domain) { return this.request(`/api/server/backups${domain ? `?domain=${domain}` : ''}`); }
    async createBackup(domain, includeDb = true, includeEmail = true) { return this.request('/api/server/backups', { method: 'POST', body: JSON.stringify({ domain, include_db: includeDb, include_email: includeEmail }) }); }
    async restoreBackup(backupId, domain) { return this.request(`/api/server/backups/${backupId}/restore${domain ? `?domain=${domain}` : ''}`, { method: 'POST' }); }
    async deleteBackup(backupId) { return this.request(`/api/server/backups/${backupId}`, { method: 'DELETE' }); }

    // System Monitor
    async getSystemStats() { return this.request('/api/server/monitor'); }
    async getServiceStatuses() { return this.request('/api/server/monitor/services'); }
    async getProcessList(limit = 20) { return this.request(`/api/server/monitor/processes?limit=${limit}`); }

    // Docker
    async getDockerContainers() { return this.request('/api/server/docker/containers'); }
    async getDockerImages() { return this.request('/api/server/docker/images'); }
    async startContainer(id) { return this.request(`/api/server/docker/containers/${id}/start`, { method: 'POST' }); }
    async stopContainer(id) { return this.request(`/api/server/docker/containers/${id}/stop`, { method: 'POST' }); }
    async restartContainer(id) { return this.request(`/api/server/docker/containers/${id}/restart`, { method: 'POST' }); }
    async removeContainer(id) { return this.request(`/api/server/docker/containers/${id}`, { method: 'DELETE' }); }
    async getContainerLogs(id, tail = 100) { return this.request(`/api/server/docker/containers/${id}/logs?tail=${tail}`); }

    // Server Info
    async getServerInfo() { return this.request('/api/server/info'); }

    // License Transfer
    async transferLicense(licenseKey, oldServerIp) { return this.request('/api/licenses/transfer', { method: 'POST', body: JSON.stringify({ license_key: licenseKey, old_server_ip: oldServerIp }) }); }
}

class ApiError extends Error {
    constructor(status, message) {
        super(message);
        this.status = status;
        this.name = 'ApiError';
    }
}

const api = new ApiClient();
export default api;
export { ApiError };

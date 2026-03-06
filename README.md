# HostingSignal

HostingSignal is a next-generation, high-performance web hosting control panel designed as a sleek, futuristic alternative to classic control panels like CyberPanel and cPanel. Built with a modern Next.js frontend and a FastAPI (Python) backend, HostingSignal manages everything from domains, DNS, and databases to emails, FTP, web files, and Docker containers.

![HostingSignal UI](https://img.shields.io/badge/UI-Liquid%20Glass-cyan?style=for-the-badge)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)
![Frontend](https://img.shields.io/badge/Frontend-Next.js-black?style=for-the-badge&logo=next.js)

## 🚀 Features
- **Futuristic UI**: Beautiful Liquid Glass, Skeuomorphism, and dark neon aesthetics.
- **Server Stack**: OpenLiteSpeed, lsphp (8.1, 8.2), MariaDB.
- **Email & DNS**: Postfix, Dovecot, OpenDKIM, PowerDNS.
- **Caching & performance**: Redis, Memcached, SpamAssassin.
- **Containerization**: Native Docker integration.
- **License System**: Built-in master license verification middleware with a futuristic activation screen.
- **Security**: Built-in Firewall (firewalld) management and user access roles.

## 📋 System Requirements
- **Operating System**: A completely fresh install of **Ubuntu 22.04 LTS** or **Ubuntu 24.04 LTS**.
- **User Permissions**: You must be logged in as `root`.
- **Hardware**: 
  - Minimum 1GB RAM (2GB+ Recommended)
  - Minimum 1 CPU Core
  - Minimum 20GB Disk Space

---

## 💻 Installation

HostingSignal comes with a fully automated, one-click installer script that downloads the repository, provisions the entire server stack, installs dependencies, builds the user interface, sets up the systemd services, and secures your panel.

Run the following command via SSH on your server as the `root` user:

```bash
wget -O install.sh https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/install.sh && sudo bash install.sh
```

### Installation Output
Once the script has finished running (which may take ~5-15 minutes depending on your server's download speed and processing power), the script will automatically output your secure login credentials to the console:

```
=================================================================
[✓] HostingSignal Installation Completed Successfully!
=================================================================
You can now access your control panel at:
URL:  http://YOUR_SERVER_IP:3000

Admin Login Credentials:
Username: admin@hostingsignal.com
Password: (Generates a secure random 16 character password)

Note: If you have a firewall running, ensure ports 3000 and 8000 are open.
=================================================================
```

## ⚙️ Development Mode
If you are running the panel locally on your workstation for development purposes and do not want to install massive Linux server dependencies:

1. Clone the repository.
2. In the `/backend` folder, copy `.env.example` to `.env` and set `DEV_MODE=1`.
3. Setting Dev Mode perfectly mocks all Linux system outputs (OpenLiteSpeed restarts, pure-ftpd accounts, docker states) so you can purely develop the UI/FastAPI routes without a Linux environment.
4. Run `npm run dev` in the `/frontend` folder.
5. Run `uvicorn app.main:app --reload` in the `/backend` folder.

## 🛡️ Licensing
HostingSignal includes its own embedded Anti-Piracy License Verification module. If the backend fails to read or verify a valid `HS-XXXX-XXXX-XXXX-XXXX` license from the central master server, the panel will eject users directly to a `402 Payment Required` activation wall.

## 🤝 Contributing
Contributions, issues, and feature requests are always welcome! Feel free to check the issues page.

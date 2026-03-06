<p align="center">
  <img src="https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/frontend/public/logo.png" alt="HostingSignal Logo" width="200" onerror="this.src='https://via.placeholder.com/200?text=HostingSignal'"/>
</p>

<h1 align="center">HostingSignal</h1>

<p align="center">
  <strong>The Next-Generation, High-Performance Web Hosting Control Panel.</strong>
</p>

<p align="center">
  <img alt="UI Liquid Glass" src="https://img.shields.io/badge/UI-Liquid%20Glass-cyan?style=for-the-badge">
  <img alt="Backend FastAPI" src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi">
  <img alt="Frontend Next.js" src="https://img.shields.io/badge/Frontend-Next.js-black?style=for-the-badge&logo=next.js">
  <img alt="License MIT" src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge">
</p>

---

**HostingSignal** is a futuristic alternative to classic control panels like CyberPanel and cPanel. Built from the ground up with a modern **Next.js** frontend and a lightning-fast **FastAPI** (Python) backend, HostingSignal manages everything from domains, DNS, and databases to emails, FTP, web files, and Docker containers—all within a stunning **Liquid Glass** aesthetic.

## ✨ Key Features

- **🎨 Futuristic UI/UX**: Beautiful Liquid Glass, Skeuomorphism, and dark neon aesthetics providing a premium and smooth user experience.
- **⚡ High-Performance Server Stack**: Powered by **OpenLiteSpeed**, **lsphp** (8.1, 8.2), and **MariaDB** for maximum web hosting performance.
- **📧 Complete Email & DNS Management**: Fully integrated **Postfix**, **Dovecot**, **OpenDKIM**, and **PowerDNS**.
- **🚀 Caching & Optimization**: Built-in support for **Redis**, **Memcached**, and **SpamAssassin**.
- **🐳 Docker Containerization**: Native Docker integration to easily manage, deploy, and monitor containerized applications directly from the panel.
- **🛡️ Built-in Security**: Manage your firewall (`firewalld`), monitor server health, and enforce strict user access roles.
- **🔐 Intelligent License System**: Built-in master license verification middleware guaranteeing secure and verified panel instances.

---

## 📋 System Requirements

To ensure maximum stability and security, HostingSignal **MUST** be installed on a fresh, clean operating system.

- **Operating System**: **Ubuntu 22.04 LTS** or **Ubuntu 24.04 LTS** (Completely fresh install required)
- **User Permissions**: You must be logged in as `root`.
- **Hardware Requirements**:
  - **RAM**: Minimum 1GB (2GB+ Highly Recommended)
  - **CPU**: Minimum 1 Core
  - **Storage**: Minimum 20GB Disk Space

---

## 🚀 Installation

HostingSignal comes with a fully automated, **one-click installer script** that provisions the entire server stack, installs dependencies, builds the user interface, sets up the systemd services, and secures your panel.

Run the following command via SSH on your server as the `root` user:

```bash
wget -O install.sh https://raw.githubusercontent.com/limbanidhairya/hostingsignal/main/install.sh && sudo bash install.sh
```

### Installation Output

Depending on your server's download speed and processing power, the installation may take **~5-15 minutes**. Once finished, the script will output your secure login credentials directly to the console:

```text
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

> **Warning:** Please save these credentials in a secure place. The password is randomly generated specifically for your instance.

---

## 💻 Development Mode

Running the panel locally on your workstation for development purposes is easy. You do not need to install massive Linux server dependencies on your local machine.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/limbanidhairya/hostingsignal.git
   cd hostingsignal
   ```

2. **Setup Backend:**
   Navigate to the `/backend` folder. Copy `.env.example` to `.env` and set `DEV_MODE=True`.
   Setting Dev Mode perfectly mocks all Linux system outputs (OpenLiteSpeed restarts, pure-ftpd accounts, docker states) so you can purely develop the UI/FastAPI routes without a Linux environment.
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

3. **Setup Frontend:**
   In a new terminal, navigate to the `/frontend` folder:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Now open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🏗️ Architecture

- **Frontend**: Next.js 14 (App Router), React, Tailwind CSS, Framer Motion for animations.
- **Backend**: FastAPI (Python 3), SQLAlchemy, aiosqlite, Uvicorn.
- **Communication**: RESTful APIs & WebSockets for real-time server stats and logs.
- **Service Management**: `systemctl` bindings via Python to control OpenLiteSpeed, MariaDB, Docker, etc.

---

## 📜 Licensing Module

HostingSignal includes an embedded Anti-Piracy License Verification module. If the backend fails to read or verify a valid `HS-XXXX-XXXX-XXXX-XXXX` license from the central master server, the panel will securely eject users directly to an activation wall (`402 Payment Required`).

---

## 🤝 Contributing

We welcome contributions from the community! Whether it's a bug fix, new feature, or documentation improvement, please feel free to open an issue or submit a Pull Request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

<p align="center">
  Built with ❤️ by the <a href="https://github.com/limbanidhairya">HostingSignal Team</a>.
</p>

'use client';
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
const persistToken = (token) => {
    try {
        localStorage.setItem('hsdev_token', token);
    } catch {
        // Ignore storage write issues.
    }
};

const clearStoredToken = () => {
    try {
        localStorage.removeItem('hsdev_token');
    } catch {
        // ignore
    }
};

export default function LoginPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        const validateExistingSession = async () => {
            try {
                const res = await fetch('/api/session/me', { cache: 'no-store' });
                if (!res.ok) {
                    clearStoredToken();
                    return;
                }
                router.replace('/');
            } catch {
                // Keep user on login page when session check cannot be confirmed.
            }
        };

        validateExistingSession();
    }, [router]);

    const handleLogin = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        setError("");

        try {
            const response = await fetch('/api/session/login', {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password }),
            });

            const payload = await response.json();
            if (!response.ok) {
                throw new Error(payload.detail || "Login failed");
            }

            if (payload.access_token) {
                persistToken(payload.access_token);
            }

            const sessionCheck = await fetch('/api/session/me', { cache: 'no-store' });
            if (!sessionCheck.ok) {
                throw new Error('Session cookie was not established. Please try again.');
            }

            // Force a full navigation so middleware reads the fresh cookie deterministically.
            window.location.assign('/');
        } catch (err) {
            clearStoredToken();
            setError(err.message || "Unable to authenticate");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="bg-[#061529] font-sans text-slate-100 min-h-screen flex flex-col items-center justify-center relative overflow-hidden">
            {/* Background Grid Effect */}
            <div
                className="absolute inset-0 pointer-events-none"
                style={{
                    backgroundImage: `linear-gradient(rgba(56, 189, 248, 0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(56, 189, 248, 0.06) 1px, transparent 1px)`,
                    backgroundSize: '30px 30px'
                }}
            ></div>
            <div className="absolute inset-0 bg-gradient-to-b from-background-dark/60 via-transparent to-background-dark pointer-events-none"></div>

            {/* Main Container */}
            <div className="relative flex h-full w-full max-w-[480px] flex-col px-6 py-8 z-10">

                {/* Header / Logo Section */}
                <div className="flex flex-col items-center mb-10">
                    <div className="bg-primary/10 p-4 rounded-xl border border-primary/30 mb-4 shadow-[0_0_22px_rgba(56,189,248,0.22)] mt-[8vh]">
                        <img
                            src="/branding/hostingsignal-logo.png"
                            alt="HostingSignal"
                            className="h-14 w-auto object-contain"
                        />
                    </div>
                    <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
                        HOSTINGSIGNAL <span className="text-primary font-light">CONTROL</span>
                    </h1>
                    <p className="text-slate-400 mt-2 text-sm uppercase tracking-[0.2em]">Operations Portal Access</p>
                </div>

                {/* Glass Login Card */}
                <div className="glass rounded-xl p-8 shadow-2xl">
                    <h2 className="text-xl font-semibold mb-6 text-white text-center">Login to your account</h2>
                    <form className="space-y-5" onSubmit={handleLogin}>
                        {/* Email Field */}
                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium text-slate-300 ml-1">Email Address</label>
                            <div className="relative">
                                <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-xl">
                                    mail
                                </span>
                                <input
                                    required
                                    className="w-full bg-[#0a1628]/50 border border-slate-700 focus:border-[#00d9ff] focus:ring-1 focus:ring-[#00d9ff] rounded-lg py-4 pl-12 pr-4 text-white placeholder:text-slate-600 transition-all outline-none"
                                    placeholder="partner@hs-panel.com"
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>
                        </div>

                        {/* Password Field */}
                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium text-slate-300 ml-1">Password</label>
                            <div className="relative">
                                <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-xl">
                                    lock
                                </span>
                                <input
                                    required
                                    className="w-full bg-[#0a1628]/50 border border-slate-700 focus:border-[#00d9ff] focus:ring-1 focus:ring-[#00d9ff] rounded-lg py-4 pl-12 pr-12 text-white placeholder:text-slate-600 transition-all outline-none"
                                    placeholder="••••••••"
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                                <button className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-[#00d9ff] transition-colors" type="button">
                                    <span className="material-symbols-outlined text-xl">visibility</span>
                                </button>
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center justify-between text-xs py-1">
                            <label className="flex items-center gap-2 cursor-pointer group">
                                <input className="rounded border-slate-700 bg-[#0a1628] text-[#00d9ff] focus:ring-[#00d9ff]/50" type="checkbox" />
                                <span className="text-slate-400 group-hover:text-slate-200 transition-colors">Remember device</span>
                            </label>
                            <a className="text-primary hover:text-primary/80 transition-colors font-medium" href="#">Forgot Password?</a>
                        </div>

                        {/* Submit Button */}
                        <button disabled={submitting} className="w-full bg-gradient-to-r from-primary to-accent hover:from-primary/90 hover:to-accent/90 disabled:opacity-60 disabled:cursor-not-allowed text-background-dark font-bold py-4 rounded-lg shadow-lg shadow-primary/20 flex items-center justify-center gap-2 transition-transform active:scale-[0.98]" type="submit">
                            <span>{submitting ? 'Authenticating...' : 'Login to Control Panel'}</span>
                            <span className="material-symbols-outlined">arrow_forward</span>
                        </button>
                        {error && <p className="text-red-400 text-sm text-center">{error}</p>}
                    </form>
                </div>

                {/* Footer Actions */}
                <div className="mt-8 text-center space-y-4">
                    <p className="text-slate-400 text-sm">Client license and purchase flows are managed in WHMCS.</p>
                    <div className="pt-6 flex justify-center gap-6">
                        <a className="text-slate-500 hover:text-slate-300 transition-colors" href="#">
                            <span className="material-symbols-outlined">help_outline</span>
                        </a>
                        <a className="text-slate-500 hover:text-slate-300 transition-colors" href="#">
                            <span className="material-symbols-outlined">language</span>
                        </a>
                        <a className="text-slate-500 hover:text-slate-300 transition-colors" href="#">
                            <span className="material-symbols-outlined">terminal</span>
                        </a>
                    </div>
                </div>

                {/* Infrastructure Status Mockup Image */}
                <div className="mt-auto pt-10 px-4">
                    <div className="flex items-center justify-between p-4 bg-[#0a1628]/30 rounded-lg border border-slate-800/50">
                        <div className="flex items-center gap-3">
                            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                            <span className="text-[10px] uppercase tracking-widest text-slate-500">API Status: Operational</span>
                        </div>
                        <div className="h-[20px] w-32 bg-slate-800/50 rounded overflow-hidden">
                            <div className="h-full w-full bg-primary/20 border-r border-primary/50"></div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Decorative background element */}
            <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-primary/10 rounded-full blur-[100px] pointer-events-none"></div>
            <div className="absolute -top-24 -right-24 w-96 h-96 bg-accent/10 rounded-full blur-[100px] pointer-events-none"></div>
        </div>
    );
}

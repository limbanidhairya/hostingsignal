'use client';
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function LoginPage() {
    const router = useRouter();

    const handleLogin = (e) => {
        e.preventDefault();
        router.push("/");
    };

    return (
        <div className="bg-[#0a1628] font-sans text-slate-100 min-h-screen flex flex-col items-center justify-center relative overflow-hidden">
            {/* Background Grid Effect */}
            <div
                className="absolute inset-0 pointer-events-none"
                style={{
                    backgroundImage: `linear-gradient(rgba(0, 217, 255, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 217, 255, 0.05) 1px, transparent 1px)`,
                    backgroundSize: '30px 30px'
                }}
            ></div>
            <div className="absolute inset-0 bg-gradient-to-b from-[#0a1628]/50 via-transparent to-[#0a1628] pointer-events-none"></div>

            {/* Main Container */}
            <div className="relative flex h-full w-full max-w-[480px] flex-col px-6 py-8 z-10">

                {/* Header / Logo Section */}
                <div className="flex flex-col items-center mb-10">
                    <div className="bg-[#00d9ff]/10 p-4 rounded-xl border border-[#00d9ff]/30 mb-4 shadow-[0_0_20px_rgba(0,217,255,0.15)] mt-[10vh]">
                        <span className="material-symbols-outlined text-[#00d9ff] text-5xl" style={{ fontVariationSettings: "'FILL' 0, 'wght' 300" }}>
                            shield_lock
                        </span>
                    </div>
                    <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
                        HS-PANEL <span className="text-[#00d9ff] font-light">PARTNER</span>
                    </h1>
                    <p className="text-slate-400 mt-2 text-sm uppercase tracking-[0.2em]">Developer Portal Access</p>
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
                            <a className="text-[#00d9ff] hover:text-[#00d9ff]/80 transition-colors font-medium" href="#">Forgot Password?</a>
                        </div>

                        {/* Submit Button */}
                        <button className="w-full bg-gradient-to-r from-[#00d9ff] to-blue-600 hover:from-[#00d9ff]/90 hover:to-blue-600/90 text-[#0a1628] font-bold py-4 rounded-lg shadow-lg shadow-[#00d9ff]/20 flex items-center justify-center gap-2 transition-transform active:scale-[0.98]" type="submit">
                            <span>Login to Partner Portal</span>
                            <span className="material-symbols-outlined">arrow_forward</span>
                        </button>
                    </form>
                </div>

                {/* Footer Actions */}
                <div className="mt-8 text-center space-y-4">
                    <p className="text-slate-400 text-sm">
                        New developer?
                        <a className="text-[#00d9ff] font-semibold hover:underline decoration-[#00d9ff]/30 underline-offset-4 ml-1" href="#">Apply for access</a>
                    </p>
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
                            <div className="h-full w-full bg-[#00d9ff]/20 border-r border-[#00d9ff]/50"></div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Decorative background element */}
            <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-[#00d9ff]/5 rounded-full blur-[100px] pointer-events-none"></div>
            <div className="absolute -top-24 -right-24 w-96 h-96 bg-blue-600/5 rounded-full blur-[100px] pointer-events-none"></div>
        </div>
    );
}

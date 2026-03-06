"use client";

import { useState } from 'react';
import { motion } from 'framer-motion';
import { DownloadCloud, CheckCircle, Trash2, Box, Shield, Server, RefreshCw } from 'lucide-react';

const availablePlugins = [
    {
        id: "docker",
        name: "Docker Engine",
        description: "Install Docker to run isolated containers, apps, and services directly from the panel.",
        icon: <Box className="w-8 h-8 text-blue-400" />,
        installed: false,
        version: "v24.0.5",
    },
    {
        id: "redis",
        name: "Redis Server",
        description: "In-memory data structure store, used as a secure, high-performance database cache.",
        icon: <Server className="w-8 h-8 text-red-400" />,
        installed: true,
        version: "v7.0.12",
    },
    {
        id: "clamav",
        name: "ClamAV Anti-Virus",
        description: "Open source antivirus engine for detecting trojans, viruses, malware & other malicious threats.",
        icon: <Shield className="w-8 h-8 text-green-400" />,
        installed: false,
        version: "Latest",
    }
];

export default function PluginsPage() {
    const [plugins, setPlugins] = useState(availablePlugins);
    const [processing, setProcessing] = useState(null);

    const togglePlugin = (id, currentStatus) => {
        setProcessing(id);
        // Simulate installation/removal process
        setTimeout(() => {
            setPlugins(plugins.map(p =>
                p.id === id ? { ...p, installed: !currentStatus } : p
            ));
            setProcessing(null);
        }, 2500);
    };

    return (
        <div className="p-8 space-y-8 animate-in fade-in duration-500">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Plugin Manager</h1>
                    <p className="text-sm text-gray-400 mt-1">
                        Install additional software modules and features on-demand.
                    </p>
                </div>
                <button className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-sm font-medium text-white hover:bg-white/10 transition">
                    <RefreshCw className="w-4 h-4" />
                    Refresh Registry
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {plugins.map((plugin, index) => (
                    <motion.div
                        key={plugin.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="group relative bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-xl hover:bg-white/[0.07] hover:border-white/20 transition-all"
                    >
                        {plugin.installed && (
                            <div className="absolute top-4 right-4 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium">
                                <CheckCircle className="w-3.5 h-3.5" />
                                Installed
                            </div>
                        )}

                        <div className="p-3 bg-white/5 rounded-xl border border-white/10 inline-flex group-hover:scale-110 transition-transform duration-300">
                            {plugin.icon}
                        </div>

                        <h3 className="text-lg font-semibold text-white mt-4">{plugin.name}</h3>
                        <p className="text-sm text-gray-400 mt-2 line-clamp-2 leading-relaxed h-10">
                            {plugin.description}
                        </p>

                        <div className="mt-6 pt-6 border-t border-white/10 flex items-center justify-between">
                            <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {plugin.version}
                            </span>

                            <button
                                onClick={() => togglePlugin(plugin.id, plugin.installed)}
                                disabled={processing !== null}
                                className={`
                  flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all shadow-lg
                  ${processing === plugin.id
                                        ? 'bg-blue-500/50 cursor-not-allowed opacity-80 text-white'
                                        : plugin.installed
                                            ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20'
                                            : 'bg-blue-600 hover:bg-blue-500 text-white hover:shadow-blue-500/25'}
                `}
                            >
                                {processing === plugin.id ? (
                                    <>
                                        <RefreshCw className="w-4 h-4 animate-spin" />
                                        Processing...
                                    </>
                                ) : plugin.installed ? (
                                    <>
                                        <Trash2 className="w-4 h-4" />
                                        Uninstall
                                    </>
                                ) : (
                                    <>
                                        <DownloadCloud className="w-4 h-4" />
                                        Install
                                    </>
                                )}
                            </button>
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
}

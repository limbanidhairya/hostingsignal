'use client';
import { useState } from 'react';

export default function Toast({ message, type = 'success', onClose }) {
    return (
        <div className={`toast toast-${type}`} onClick={onClose}>
            <span className="toast-icon">
                {type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️'}
            </span>
            <span className="toast-message">{message}</span>
            <button className="toast-close" onClick={onClose}>✕</button>
        </div>
    );
}

// Hook for using toasts
export function useToast() {
    const [toasts, setToasts] = useState([]);

    const showToast = (message, type = 'success', duration = 4000) => {
        const id = Date.now();
        setToasts(prev => [...prev, { id, message, type }]);
        setTimeout(() => {
            setToasts(prev => prev.filter(t => t.id !== id));
        }, duration);
    };

    const ToastContainer = () => (
        <div className="toast-container">
            {toasts.map(t => (
                <Toast key={t.id} message={t.message} type={t.type}
                    onClose={() => setToasts(prev => prev.filter(x => x.id !== t.id))} />
            ))}
        </div>
    );

    return { showToast, ToastContainer };
}

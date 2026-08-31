/**
 * Enterprise Core API & Notification Helper Module
 */

/**
 * Unified asynchronous Fetch wrapper with structured error handling.
 * @param {string} endpoint - API route (e.g. '/api/admin/metrics')
 * @param {object} options - Standard fetch options (method, body, headers, etc.)
 * @returns {Promise<object>} Resolves to { success, message, data }
 */
async function apiFetch(endpoint, options = {}) {
    const defaultHeaders = {
        'Accept': 'application/json'
    };

    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
        defaultHeaders['Content-Type'] = 'application/json';
        options.body = JSON.stringify(options.body);
    }

    const config = {
        credentials: 'same-origin',
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers
        }
    };

    try {
        const response = await fetch(endpoint, config);
        let result;
        
        try {
            result = await response.json();
        } catch (jsonErr) {
            result = {
                success: false,
                message: `Server returned HTTP ${response.status} with non-JSON body.`,
                data: null
            };
        }

        if (response.status === 401) {
            if (!window.location.pathname.includes('/login')) {
                showToast('Session expired. Redirecting to sign in...', 'warning');
                setTimeout(() => {
                    window.location.href = '/login';
                }, 1200);
            }
        }

        if (!response.ok && result.success !== false) {
            result.success = false;
            if (!result.message) {
                result.message = `HTTP Error ${response.status}: ${response.statusText}`;
            }
        }

        return result;
    } catch (error) {
        console.error('Network request failed:', error);
        return {
            success: false,
            message: 'Network communication error. Please verify your connection.',
            data: null
        };
    }
}

/**
 * Display a non-blocking floating toast notification.
 * @param {string} message - Toast message text
 * @param {'success'|'error'|'warning'|'info'} type - Visual category
 * @param {number} duration - Display time in ms
 */
function showToast(message, type = 'info', duration = 3500) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toastId = 'toast-' + Math.random().toString(36).substr(2, 9);
    
    // Styling configurations based on category
    const configs = {
        success: {
            bg: 'bg-slate-900',
            border: 'border-emerald-500/50',
            iconColor: 'text-emerald-400',
            icon: 'check-circle-2',
            glow: 'shadow-lg shadow-emerald-950/40'
        },
        error: {
            bg: 'bg-slate-900',
            border: 'border-rose-500/50',
            iconColor: 'text-rose-400',
            icon: 'alert-octagon',
            glow: 'shadow-lg shadow-rose-950/40'
        },
        warning: {
            bg: 'bg-slate-900',
            border: 'border-amber-500/50',
            iconColor: 'text-amber-400',
            icon: 'alert-triangle',
            glow: 'shadow-lg shadow-amber-950/40'
        },
        info: {
            bg: 'bg-slate-900',
            border: 'border-indigo-500/50',
            iconColor: 'text-indigo-400',
            icon: 'info',
            glow: 'shadow-lg shadow-indigo-950/40'
        }
    };

    const config = configs[type] || configs.info;

    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `pointer-events-auto flex items-center justify-between gap-3 px-4 py-3 rounded-xl border ${config.border} ${config.bg} ${config.glow} text-slate-100 text-sm font-medium backdrop-blur-md transition-all duration-300 toast-enter max-w-md w-full shadow-2xl`;
    
    toast.innerHTML = `
        <div class="flex items-center gap-3">
            <i data-lucide="${config.icon}" class="w-5 h-5 ${config.iconColor} shrink-0"></i>
            <span class="leading-snug">${escapeHtml(message)}</span>
        </div>
        <button type="button" onclick="dismissToast('${toastId}')" class="text-slate-400 hover:text-slate-200 transition-colors p-1 rounded-lg hover:bg-slate-800 shrink-0">
            <i data-lucide="x" class="w-4 h-4"></i>
        </button>
    `;

    container.appendChild(toast);
    
    if (window.lucide) {
        lucide.createIcons({ root: toast });
    }

    const timer = setTimeout(() => {
        dismissToast(toastId);
    }, duration);

    toast.dataset.timer = timer;
}

/**
 * Remove a toast notification with smooth exit animation.
 */
function dismissToast(toastId) {
    const toast = document.getElementById(toastId);
    if (!toast) return;

    if (toast.dataset.timer) {
        clearTimeout(Number(toast.dataset.timer));
    }

    toast.classList.remove('toast-enter');
    toast.classList.add('toast-leave');

    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 250);
}

/**
 * Format numerical amount to standard USD currency string ($xx,xxx.xx).
 */
function formatCurrency(amount) {
    const val = Number(amount) || 0;
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(val);
}

/**
 * Format standard ISO or SQL date to human-readable format.
 */
function formatDate(dateStr) {
    if (!dateStr) return 'No date specified';
    try {
        // Parse yyyy-mm-dd safely
        const parts = dateStr.split(' ')[0].split('-');
        if (parts.length === 3) {
            const date = new Date(parts[0], parts[1] - 1, parts[2]);
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
        }
        const date = new Date(dateStr);
        return isNaN(date.getTime()) ? dateStr : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
        return dateStr;
    }
}

/**
 * Escape HTML to prevent XSS in dynamic string injections.
 */
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/**
 * Global User Sign Out handler.
 */
async function handleLogout() {
    try {
        const res = await apiFetch('/api/auth/logout', { method: 'POST' });
        if (res.success) {
            showToast('Signed out successfully.', 'info');
            setTimeout(() => {
                window.location.href = res.data?.redirect_url || '/login';
            }, 500);
        } else {
            showToast(res.message || 'Logout failed', 'error');
        }
    } catch (err) {
        window.location.href = '/login';
    }
}

/**
 * Enterprise Core - Employee Portal Controller
 */

let myTasks = [];
let myProfile = null;

document.addEventListener('DOMContentLoaded', () => {
    initEmployeePortal();
});

async function initEmployeePortal() {
    setupEmployeeEventListeners();
    await Promise.all([
        loadProfile(),
        loadMyTasks()
    ]);
}

/**
 * Register search & filter listeners.
 */
function setupEmployeeEventListeners() {
    const searchInput = document.getElementById('my-task-search');
    const statusFilter = document.getElementById('my-task-status-filter');
    const priorityFilter = document.getElementById('my-task-priority-filter');

    if (searchInput) {
        searchInput.addEventListener('input', filterAndRenderMyTasks);
    }
    if (statusFilter) {
        statusFilter.addEventListener('change', filterAndRenderMyTasks);
    }
    if (priorityFilter) {
        priorityFilter.addEventListener('change', filterAndRenderMyTasks);
    }
}

/**
 * Fetch employee profile and metrics.
 */
async function loadProfile() {
    const res = await apiFetch('/api/employee/me');
    if (!res.success) {
        showToast(res.message || 'Unable to load profile', 'error');
        return;
    }

    myProfile = res.data;
    renderProfile(myProfile);
}

/**
 * Render personal profile details, salary, payslip badge, and KPI metrics.
 */
function renderProfile(profile) {
    if (!profile) return;

    // Header greeting & avatar
    const employeeNameEl = document.getElementById('emp-full-name');
    const employeeRoleEl = document.getElementById('emp-username-tag');
    const employeeEmailEl = document.getElementById('emp-email');
    const employeePhoneEl = document.getElementById('emp-phone');
    const employeeInitialsEl = document.getElementById('emp-avatar-initials');

    if (employeeNameEl) employeeNameEl.textContent = profile.full_name;
    if (employeeRoleEl) employeeRoleEl.textContent = `@${profile.username}`;
    if (employeeEmailEl) employeeEmailEl.textContent = profile.email;
    if (employeePhoneEl) employeePhoneEl.textContent = profile.phone;

    if (employeeInitialsEl) {
        const initials = profile.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        employeeInitialsEl.textContent = initials;
    }

    // Compensation & Payslip Card
    const salaryEl = document.getElementById('emp-salary');
    const payslipBadgeEl = document.getElementById('emp-payslip-badge');

    if (salaryEl) salaryEl.textContent = formatCurrency(profile.salary);

    if (payslipBadgeEl) {
        const isPaid = profile.payslip_status === 'Paid';
        payslipBadgeEl.className = `inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
            isPaid 
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 glow-emerald' 
            : 'bg-rose-500/10 text-rose-400 border-rose-500/30 glow-rose'
        }`;
        payslipBadgeEl.innerHTML = `
            <span class="w-2 h-2 rounded-full ${isPaid ? 'bg-emerald-400' : 'bg-rose-400 animate-pulse-slow'}"></span>
            ${isPaid ? 'Payslip Disbursed (Paid)' : 'Pending Disbursement (Unpaid)'}
        `;
    }

    // Task KPI Counters
    const metrics = profile.metrics || {};
    const totalTasksEl = document.getElementById('emp-metric-total');
    const ongoingTasksEl = document.getElementById('emp-metric-ongoing');
    const completedTasksEl = document.getElementById('emp-metric-completed');
    const blockedTasksEl = document.getElementById('emp-metric-blocked');
    const completionRateEl = document.getElementById('emp-completion-rate');
    const completionBarEl = document.getElementById('emp-completion-bar');

    if (totalTasksEl) totalTasksEl.textContent = metrics.total_tasks || 0;
    if (ongoingTasksEl) ongoingTasksEl.textContent = metrics.ongoing_tasks || 0;
    if (completedTasksEl) completedTasksEl.textContent = metrics.completed_tasks || 0;
    if (blockedTasksEl) blockedTasksEl.textContent = metrics.blocked_tasks || 0;

    if (completionRateEl) completionRateEl.textContent = `${metrics.completion_rate || 0}%`;
    if (completionBarEl) completionBarEl.style.width = `${metrics.completion_rate || 0}%`;

    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * Fetch personal assigned tasks.
 */
async function loadMyTasks() {
    const res = await apiFetch('/api/employee/my-tasks');
    if (!res.success) {
        showToast(res.message || 'Unable to load assigned tasks', 'error');
        return;
    }

    myTasks = res.data || [];
    filterAndRenderMyTasks();
}

/**
 * Filter and render task cards.
 */
function filterAndRenderMyTasks() {
    const searchVal = (document.getElementById('my-task-search')?.value || '').toLowerCase().trim();
    const statusVal = document.getElementById('my-task-status-filter')?.value || 'all';
    const priorityVal = document.getElementById('my-task-priority-filter')?.value || 'all';

    const filtered = myTasks.filter(task => {
        const matchesSearch = 
            task.task_title.toLowerCase().includes(searchVal) ||
            (task.description && task.description.toLowerCase().includes(searchVal));

        const matchesStatus = statusVal === 'all' || task.status === statusVal;
        const matchesPriority = priorityVal === 'all' || task.priority === priorityVal;

        return matchesSearch && matchesStatus && matchesPriority;
    });

    renderTaskCards(filtered);
}

/**
 * Render task cards with interactive status transition dropdowns.
 */
function renderTaskCards(tasks) {
    const container = document.getElementById('my-tasks-container');
    const countBadge = document.getElementById('my-tasks-count');

    if (countBadge) countBadge.textContent = `${tasks.length} Assigned Task${tasks.length === 1 ? '' : 's'}`;
    if (!container) return;

    if (tasks.length === 0) {
        container.innerHTML = `
            <div class="col-span-full py-16 text-center text-slate-500 glass-card rounded-2xl p-8 border border-slate-800">
                <div class="flex flex-col items-center justify-center gap-3">
                    <div class="w-12 h-12 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400">
                        <i data-lucide="inbox" class="w-6 h-6"></i>
                    </div>
                    <h3 class="text-base font-semibold text-slate-300">No tasks found</h3>
                    <p class="text-sm text-slate-500 max-w-sm">No tasks currently match your filter criteria or you are fully caught up.</p>
                </div>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    const priorityBadges = {
        Urgent: 'bg-rose-500/10 text-rose-400 border-rose-500/30 glow-rose',
        High: 'bg-amber-500/10 text-amber-400 border-amber-500/30 glow-amber',
        Medium: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30 glow-indigo',
        Low: 'bg-slate-700/30 text-slate-300 border-slate-600/40'
    };

    container.innerHTML = tasks.map(task => {
        const pBadge = priorityBadges[task.priority] || priorityBadges.Medium;
        const isBlocked = task.status === 'Blocked';
        
        return `
            <div class="glass-card rounded-2xl p-5 border ${isBlocked ? 'border-rose-500/50 bg-rose-950/10 glow-rose' : 'border-slate-800'} flex flex-col justify-between transition-all duration-200 hover:border-slate-700">
                <div>
                    <!-- Top row: Priority badge and Due Date -->
                    <div class="flex items-center justify-between gap-2 mb-3">
                        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${pBadge}">
                            <i data-lucide="flag" class="w-3 h-3 mr-1"></i>
                            ${task.priority} Priority
                        </span>
                        
                        <div class="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
                            <i data-lucide="calendar" class="w-3.5 h-3.5 text-slate-500"></i>
                            <span>Due: ${task.due_date ? formatDate(task.due_date) : 'Flexible'}</span>
                        </div>
                    </div>

                    <!-- Title & Description -->
                    <h3 class="text-base font-semibold text-slate-100 mb-2 leading-snug flex items-center gap-2">
                        ${isBlocked ? '<span class="text-xs px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/40 font-bold uppercase tracking-wider">BLOCKED</span>' : ''}
                        ${escapeHtml(task.task_title)}
                    </h3>
                    <p class="text-sm text-slate-400 line-clamp-3 mb-5 leading-relaxed">
                        ${escapeHtml(task.description || 'No detailed instructions provided.')}
                    </p>
                </div>

                <!-- Bottom row: Status selector & Assigned stamp -->
                <div class="pt-4 border-t border-slate-800/80 flex items-center justify-between gap-3">
                    <div class="text-xs text-slate-500 font-mono">
                        Assigned: ${formatDate(task.assigned_date)}
                    </div>

                    <div class="flex items-center gap-2">
                        <label for="status-select-${task.id}" class="text-xs text-slate-400 font-medium">Status:</label>
                        <select 
                            id="status-select-${task.id}"
                            onchange="handleStatusChange(${task.id}, this.value)"
                            class="bg-slate-950 border border-slate-700 text-xs rounded-lg px-2.5 py-1.5 font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors cursor-pointer ${
                                task.status === 'Completed' ? 'border-emerald-500/50 text-emerald-400 bg-emerald-950/20' :
                                task.status === 'Ongoing' ? 'border-amber-500/50 text-amber-300 bg-amber-950/20' :
                                task.status === 'Blocked' ? 'border-rose-500/60 text-rose-400 bg-rose-950/40 font-bold' :
                                'text-slate-300'
                            }">
                            <option value="Pending" ${task.status === 'Pending' ? 'selected' : ''}>⏳ Pending</option>
                            <option value="Ongoing" ${task.status === 'Ongoing' ? 'selected' : ''}>⚡ Ongoing</option>
                            <option value="Blocked" ${task.status === 'Blocked' ? 'selected' : ''}>🚨 Blocked (Escalate)</option>
                            <option value="Completed" ${task.status === 'Completed' ? 'selected' : ''}>✓ Completed</option>
                        </select>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * Prompt employee for roadblock context if setting status to Blocked.
 */
function handleStatusChange(taskId, newStatus) {
    if (newStatus === 'Blocked') {
        const comment = prompt('Please specify the roadblock or dependency issue encountered (this will be emailed to administrator immediately):', 'Waiting on external API credentials / infrastructure access.');
        if (comment === null) {
            // User cancelled prompt; revert select UI
            filterAndRenderMyTasks();
            return;
        }
        updateTaskStatus(taskId, newStatus, comment);
    } else {
        updateTaskStatus(taskId, newStatus);
    }
}

/**
 * Handle inline task status transition.
 */
async function updateTaskStatus(taskId, newStatus, comment = null) {
    const payload = { status: newStatus };
    if (comment) payload.comment = comment;

    const res = await apiFetch(`/api/employee/tasks/${taskId}/status`, {
        method: 'PATCH',
        body: payload
    });

    if (res.success) {
        showToast(res.message, newStatus === 'Blocked' ? 'warning' : 'success');
        
        // Update local task
        const task = myTasks.find(t => t.id === taskId);
        if (task) {
            task.status = newStatus;
        }

        // Re-render tasks and refresh profile metrics
        filterAndRenderMyTasks();
        loadProfile();
    } else {
        showToast(res.message || 'Failed to update status', 'error');
        // Revert UI on failure
        filterAndRenderMyTasks();
    }
}

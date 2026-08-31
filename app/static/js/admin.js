/**
 * Enterprise Core - Admin Operations Dashboard Controller
 */

let allEmployees = [];
let allTasks = [];
let activeTab = 'employees';

document.addEventListener('DOMContentLoaded', () => {
    initAdminDashboard();
});

async function initAdminDashboard() {
    setupEventListeners();
    await Promise.all([
        loadMetrics(),
        loadEmployees(),
        loadTasks()
    ]);
}

/**
 * Register form submissions, search bars, filters, and modal triggers.
 */
function setupEventListeners() {
    // Search & Filter listeners for Employees
    const employeeSearchInput = document.getElementById('employee-search');
    const employeeStatusFilter = document.getElementById('employee-status-filter');
    if (employeeSearchInput) {
        employeeSearchInput.addEventListener('input', filterAndRenderEmployees);
    }
    if (employeeStatusFilter) {
        employeeStatusFilter.addEventListener('change', filterAndRenderEmployees);
    }

    // Search & Filter listeners for Tasks
    const taskSearchInput = document.getElementById('task-search');
    const taskPriorityFilter = document.getElementById('task-priority-filter');
    const taskStatusFilter = document.getElementById('task-status-filter');
    if (taskSearchInput) {
        taskSearchInput.addEventListener('input', filterAndRenderTasks);
    }
    if (taskPriorityFilter) {
        taskPriorityFilter.addEventListener('change', filterAndRenderTasks);
    }
    if (taskStatusFilter) {
        taskStatusFilter.addEventListener('change', filterAndRenderTasks);
    }

    // Modal Form Submissions
    const addEmployeeForm = document.getElementById('add-employee-form');
    if (addEmployeeForm) {
        addEmployeeForm.addEventListener('submit', handleCreateEmployee);
    }

    const createTaskForm = document.getElementById('create-task-form');
    if (createTaskForm) {
        createTaskForm.addEventListener('submit', handleCreateTask);
    }

    // Tab Navigation
    const tabEmployeesBtn = document.getElementById('tab-employees-btn');
    const tabTasksBtn = document.getElementById('tab-tasks-btn');
    if (tabEmployeesBtn && tabTasksBtn) {
        tabEmployeesBtn.addEventListener('click', () => switchTab('employees'));
        tabTasksBtn.addEventListener('click', () => switchTab('tasks'));
    }

    // Global ESC key to close open modals
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });
}

/**
 * Switch active view between Staff Directory and Task Allocation tabs.
 */
function switchTab(tabName) {
    activeTab = tabName;
    const tabEmployeesBtn = document.getElementById('tab-employees-btn');
    const tabTasksBtn = document.getElementById('tab-tasks-btn');
    const employeesSection = document.getElementById('employees-section');
    const tasksSection = document.getElementById('tasks-section');

    if (tabName === 'employees') {
        tabEmployeesBtn.className = 'px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white shadow-md shadow-indigo-600/30 transition-all flex items-center gap-2';
        tabTasksBtn.className = 'px-4 py-2 text-sm font-medium rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all flex items-center gap-2';
        employeesSection.classList.remove('hidden');
        tasksSection.classList.add('hidden');
    } else {
        tabTasksBtn.className = 'px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white shadow-md shadow-indigo-600/30 transition-all flex items-center gap-2';
        tabEmployeesBtn.className = 'px-4 py-2 text-sm font-medium rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all flex items-center gap-2';
        tasksSection.classList.remove('hidden');
        employeesSection.classList.add('hidden');
    }

    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * Fetch and render organizational metrics in the top KPI summary cards.
 */
async function loadMetrics() {
    const res = await apiFetch('/api/admin/metrics');
    if (!res.success) {
        showToast(res.message || 'Unable to load metrics', 'error');
        return;
    }

    const data = res.data;
    
    // Total Payroll
    const totalPayrollEl = document.getElementById('metric-total-payroll');
    if (totalPayrollEl) totalPayrollEl.textContent = formatCurrency(data.total_payroll);

    const paidPayrollEl = document.getElementById('metric-paid-breakdown');
    if (paidPayrollEl) {
        paidPayrollEl.textContent = `${formatCurrency(data.paid_payroll)} Paid (${data.paid_count}) • ${formatCurrency(data.unpaid_payroll)} Unpaid (${data.unpaid_count})`;
    }

    // Active Staff Count
    const activeStaffEl = document.getElementById('metric-active-staff');
    if (activeStaffEl) activeStaffEl.textContent = data.active_staff;

    // Task Completion Rate
    const completionRateEl = document.getElementById('metric-completion-rate');
    const completionBarEl = document.getElementById('metric-completion-bar');
    if (completionRateEl) completionRateEl.textContent = `${data.completion_rate}%`;
    if (completionBarEl) completionBarEl.style.width = `${data.completion_rate}%`;

    const taskCountsEl = document.getElementById('metric-task-counts');
    if (taskCountsEl) {
        taskCountsEl.textContent = `${data.completed_tasks} completed of ${data.total_tasks} total`;
    }

    // Pending / Urgent stats
    const pendingTasksEl = document.getElementById('metric-pending-tasks');
    if (pendingTasksEl) pendingTasksEl.textContent = data.pending_tasks;

    const urgentTasksEl = document.getElementById('metric-urgent-tasks');
    if (urgentTasksEl) {
        const blockedText = data.blocked_tasks > 0 ? `🚨 ${data.blocked_tasks} BLOCKED, ` : '';
        urgentTasksEl.textContent = `${blockedText}${data.urgent_open_tasks} urgent, ${data.ongoing_tasks} ongoing`;
    }
}

/**
 * Fetch all employee records from backend.
 */
async function loadEmployees() {
    const res = await apiFetch('/api/admin/employees');
    if (!res.success) {
        showToast(res.message || 'Unable to load employees', 'error');
        return;
    }

    allEmployees = res.data || [];
    filterAndRenderEmployees();
    populateEmployeeDropdown();
}

/**
 * Filter employee list based on search term & payslip status, then render table rows.
 */
function filterAndRenderEmployees() {
    const searchVal = (document.getElementById('employee-search')?.value || '').toLowerCase().trim();
    const statusVal = document.getElementById('employee-status-filter')?.value || 'all';

    const filtered = allEmployees.filter(emp => {
        const matchesSearch = 
            emp.full_name.toLowerCase().includes(searchVal) ||
            emp.email.toLowerCase().includes(searchVal) ||
            emp.username.toLowerCase().includes(searchVal) ||
            emp.phone.toLowerCase().includes(searchVal);

        const matchesStatus = statusVal === 'all' || emp.payslip_status === statusVal;

        return matchesSearch && matchesStatus;
    });

    renderEmployeesTable(filtered);
}

/**
 * Render the employees data table.
 */
function renderEmployeesTable(employees) {
    const tbody = document.getElementById('employees-table-body');
    const countBadge = document.getElementById('employees-count-badge');
    if (countBadge) countBadge.textContent = `${employees.length} Staff Member${employees.length === 1 ? '' : 's'}`;

    if (!tbody) return;

    if (employees.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="py-12 text-center text-slate-500">
                    <div class="flex flex-col items-center justify-center gap-2">
                        <i data-lucide="users" class="w-8 h-8 text-slate-600"></i>
                        <p class="text-sm font-medium">No matching employee records found.</p>
                    </div>
                </td>
            </tr>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    tbody.innerHTML = employees.map(emp => {
        const isPaid = emp.payslip_status === 'Paid';
        const initials = emp.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        
        return `
            <tr class="border-b border-slate-800/80 hover:bg-slate-800/40 transition-colors">
                <td class="py-4 px-4">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300 font-bold text-xs shrink-0">
                            ${initials}
                        </div>
                        <div>
                            <div class="font-semibold text-slate-100">${escapeHtml(emp.full_name)}</div>
                            <div class="text-xs text-slate-400 font-mono">@${escapeHtml(emp.username)}</div>
                        </div>
                    </div>
                </td>
                <td class="py-4 px-4 text-sm text-slate-300">
                    <div>${escapeHtml(emp.email)}</div>
                    <div class="text-xs text-slate-400">${escapeHtml(emp.phone)}</div>
                </td>
                <td class="py-4 px-4 text-sm font-medium text-slate-100 font-mono">
                    ${formatCurrency(emp.salary)}
                </td>
                <td class="py-4 px-4">
                    <button 
                        type="button"
                        onclick="togglePayroll(${emp.id})"
                        title="Click to toggle payroll status"
                        class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
                            isPaid 
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20 glow-emerald' 
                            : 'bg-rose-500/10 text-rose-400 border-rose-500/30 hover:bg-rose-500/20 glow-rose'
                        }">
                        <span class="w-1.5 h-1.5 rounded-full ${isPaid ? 'bg-emerald-400' : 'bg-rose-400'}"></span>
                        ${emp.payslip_status}
                        <i data-lucide="refresh-cw" class="w-3 h-3 ml-0.5 opacity-60"></i>
                    </button>
                </td>
                <td class="py-4 px-4 text-sm">
                    <div class="flex items-center gap-2">
                        <div class="w-20 bg-slate-800 h-2 rounded-full overflow-hidden">
                            <div class="bg-indigo-500 h-full rounded-full" style="width: ${emp.total_assigned_tasks > 0 ? (emp.completed_tasks / emp.total_assigned_tasks * 100) : 0}%"></div>
                        </div>
                        <span class="text-xs text-slate-400 font-mono">${emp.completed_tasks}/${emp.total_assigned_tasks}</span>
                    </div>
                </td>
                <td class="py-4 px-4 text-right">
                    <button 
                        type="button" 
                        onclick="openDispatchTaskForEmployee(${emp.id})"
                        class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-indigo-600 text-slate-300 hover:text-white text-xs font-medium border border-slate-700 hover:border-indigo-500 transition-all inline-flex items-center gap-1.5">
                        <i data-lucide="plus-circle" class="w-3.5 h-3.5"></i>
                        <span>Assign Task</span>
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * Inline one-click toggle for employee payslip status.
 */
async function togglePayroll(employeeId) {
    const res = await apiFetch(`/api/admin/employees/${employeeId}/toggle-payroll`, {
        method: 'PATCH'
    });

    if (res.success) {
        showToast(res.message, 'success');
        // Update local state and re-render
        const emp = allEmployees.find(e => e.id === employeeId);
        if (emp) {
            emp.payslip_status = res.data.payslip_status;
            filterAndRenderEmployees();
        }
        // Update top KPI cards
        loadMetrics();
    } else {
        showToast(res.message || 'Failed to update payroll status', 'error');
    }
}

/**
 * Handle new employee creation form submission.
 */
async function handleCreateEmployee(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    
    const payload = {
        full_name: form.full_name.value.trim(),
        username: form.username.value.trim(),
        email: form.email.value.trim(),
        phone: form.phone.value.trim(),
        password: form.password.value.trim(),
        salary: form.salary.value,
        payslip_status: form.payslip_status.value
    };

    if (!payload.full_name || !payload.username || !payload.email || !payload.phone || !payload.password) {
        showToast('Please fill out all mandatory fields.', 'warning');
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="inline-block animate-spin mr-2">⟳</span> Registering...';
    }

    const res = await apiFetch('/api/admin/employees/create', {
        method: 'POST',
        body: payload
    });

    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i data-lucide="user-plus" class="w-4 h-4 mr-1.5"></i> Register Employee';
    }

    if (res.success) {
        showToast(res.message, 'success');
        form.reset();
        closeModal('add-employee-modal');
        await Promise.all([loadEmployees(), loadMetrics()]);
    } else {
        showToast(res.message || 'Failed to register employee', 'error');
    }
}

/**
 * Fetch all tasks from backend.
 */
async function loadTasks() {
    const res = await apiFetch('/api/admin/tasks');
    if (!res.success) {
        showToast(res.message || 'Unable to load tasks', 'error');
        return;
    }

    allTasks = res.data || [];
    filterAndRenderTasks();
}

/**
 * Filter tasks based on search term, priority, and status filters.
 */
function filterAndRenderTasks() {
    const searchVal = (document.getElementById('task-search')?.value || '').toLowerCase().trim();
    const priorityVal = document.getElementById('task-priority-filter')?.value || 'all';
    const statusVal = document.getElementById('task-status-filter')?.value || 'all';

    const filtered = allTasks.filter(task => {
        const matchesSearch = 
            task.task_title.toLowerCase().includes(searchVal) ||
            (task.description && task.description.toLowerCase().includes(searchVal)) ||
            task.employee_name.toLowerCase().includes(searchVal);

        const matchesPriority = priorityVal === 'all' || task.priority === priorityVal;
        const matchesStatus = statusVal === 'all' || task.status === statusVal;

        return matchesSearch && matchesPriority && matchesStatus;
    });

    renderTasksTable(filtered);
}

/**
 * Render the task allocation table.
 */
function renderTasksTable(tasks) {
    const tbody = document.getElementById('tasks-table-body');
    const countBadge = document.getElementById('tasks-count-badge');
    if (countBadge) countBadge.textContent = `${tasks.length} Allocated Task${tasks.length === 1 ? '' : 's'}`;

    if (!tbody) return;

    if (tasks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="py-12 text-center text-slate-500">
                    <div class="flex flex-col items-center justify-center gap-2">
                        <i data-lucide="check-square" class="w-8 h-8 text-slate-600"></i>
                        <p class="text-sm font-medium">No tasks found matching criteria.</p>
                    </div>
                </td>
            </tr>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    tbody.innerHTML = tasks.map(task => {
        // Priority styling
        const priorityColors = {
            Urgent: 'bg-rose-500/10 text-rose-400 border-rose-500/30 glow-rose',
            High: 'bg-amber-500/10 text-amber-400 border-amber-500/30 glow-amber',
            Medium: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30 glow-indigo',
            Low: 'bg-slate-700/30 text-slate-300 border-slate-600/40'
        };

        // Status styling
        const statusColors = {
            Completed: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 glow-emerald',
            Ongoing: 'bg-amber-500/10 text-amber-300 border-amber-500/30 glow-amber',
            Pending: 'bg-slate-800 text-slate-400 border-slate-700',
            Blocked: 'bg-rose-500/20 text-rose-400 border-rose-500/50 glow-rose font-bold'
        };

        const priorityBadge = priorityColors[task.priority] || priorityColors.Medium;
        const statusBadge = statusColors[task.status] || statusColors.Pending;
        const isBlocked = task.status === 'Blocked';

        return `
            <tr class="border-b border-slate-800/80 hover:bg-slate-800/40 transition-colors ${isBlocked ? 'bg-rose-950/20' : ''}">
                <td class="py-4 px-4">
                    <div class="font-semibold text-slate-100 mb-0.5 flex items-center gap-2">
                        ${isBlocked ? '<span class="px-1.5 py-0.5 rounded text-[10px] bg-rose-500/30 text-rose-300 border border-rose-500/50">ROADBLOCK</span>' : ''}
                        ${escapeHtml(task.task_title)}
                    </div>
                    <div class="text-xs text-slate-400 line-clamp-1 max-w-md">${escapeHtml(task.description || 'No description provided.')}</div>
                </td>
                <td class="py-4 px-4 text-sm">
                    <div class="font-medium text-slate-200 flex items-center gap-1.5">
                        <i data-lucide="user" class="w-3.5 h-3.5 text-indigo-400"></i>
                        ${escapeHtml(task.employee_name)}
                    </div>
                    <div class="text-xs text-slate-400 font-mono">${escapeHtml(task.employee_email)}</div>
                </td>
                <td class="py-4 px-4">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${priorityBadge}">
                        ${task.priority}
                    </span>
                </td>
                <td class="py-4 px-4">
                    <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusBadge}">
                        <span class="w-1.5 h-1.5 rounded-full ${task.status === 'Completed' ? 'bg-emerald-400' : task.status === 'Ongoing' ? 'bg-amber-400' : task.status === 'Blocked' ? 'bg-rose-400 animate-pulse-slow' : 'bg-slate-400'}"></span>
                        ${task.status}
                    </span>
                </td>
                <td class="py-4 px-4 text-sm text-slate-300 font-mono">
                    ${task.due_date ? formatDate(task.due_date) : '<span class="text-slate-500 text-xs">None</span>'}
                </td>
                <td class="py-4 px-4 text-right text-xs text-slate-400 font-mono">
                    ${formatDate(task.assigned_date)}
                </td>
            </tr>
        `;
    }).join('');

    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * Populate the assignee dropdown inside Create Task modal with active staff.
 */
function populateEmployeeDropdown(selectedId = null) {
    const select = document.getElementById('task-employee-id');
    if (!select) return;

    select.innerHTML = '<option value="" disabled selected>Select Assignee Employee</option>' +
        allEmployees.map(emp => `
            <option value="${emp.id}" ${selectedId && Number(selectedId) === emp.id ? 'selected' : ''}>
                ${escapeHtml(emp.full_name)} (@${escapeHtml(emp.username)}) - ${emp.pending_tasks} open task(s)
            </option>
        `).join('');
}

/**
 * Handle new task creation form submission.
 */
async function handleCreateTask(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');

    const payload = {
        employee_id: form.employee_id.value,
        task_title: form.task_title.value.trim(),
        description: form.description.value.trim(),
        priority: form.priority.value,
        due_date: form.due_date.value || null
    };

    if (!payload.employee_id || !payload.task_title) {
        showToast('Please select an employee and provide a task title.', 'warning');
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="inline-block animate-spin mr-2">⟳</span> Dispatching...';
    }

    const res = await apiFetch('/api/admin/tasks/create', {
        method: 'POST',
        body: payload
    });

    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i data-lucide="send" class="w-4 h-4 mr-1.5"></i> Dispatch Task';
    }

    if (res.success) {
        showToast(res.message, 'success');
        form.reset();
        closeModal('create-task-modal');
        await Promise.all([loadTasks(), loadEmployees(), loadMetrics()]);
    } else {
        showToast(res.message || 'Failed to dispatch task', 'error');
    }
}

/**
 * Open Dispatch Task Modal with preselected employee.
 */
function openDispatchTaskForEmployee(employeeId) {
    populateEmployeeDropdown(employeeId);
    openModal('create-task-modal');
}

/**
 * Modal helpers.
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.remove('modal-hidden');
    document.body.classList.add('overflow-hidden');
    
    if (modalId === 'create-task-modal') {
        populateEmployeeDropdown();
    }

    if (window.lucide) {
        lucide.createIcons();
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.add('modal-hidden');
    document.body.classList.remove('overflow-hidden');
}

function closeAllModals() {
    document.querySelectorAll('.modal-backdrop').forEach(modal => {
        modal.classList.add('modal-hidden');
    });
    document.body.classList.remove('overflow-hidden');
}

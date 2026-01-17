const API_BASE = '/api';

async function api(path, { method = 'GET', headers = {}, body } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  // helpful errors in the console
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`${method} ${path} -> ${res.status} ${res.statusText}\n${text}`);
  }

  // handle 204 / empty
  const ct = res.headers.get('content-type') || '';
  if (!ct.includes('application/json')) return null;
  return res.json();
}

const state = {
  employees: [],
  timeEntries: [],
  payrollRuns: [],
  users: [],
};

async function probeApi() {
  try {
    await api('/health');

    const employees = await api('/employees');
    await api('/users');
    const required = [
      'id',
      'name',
      'role',
      'type',
      'rate',
      'defaultHours',
      'status',
      'tax',
    ];

    const ok =
      Array.isArray(employees) &&
      employees.every((e) => e && required.every((k) => k in e));

    if (!ok) throw new Error('employees endpoint not console-ready');

    return true;
  } catch (e) {
    console.error('Backend not ready for console.', e);
    throw e;
  }
}

async function loadStateFromApi() {
  // Each call is isolated so one missing endpoint doesn’t break everything.
  state.employees = await api('/employees').catch(() => []);

  const timeEntries = await api('/time').catch(() => []);
  state.timeEntries = timeEntries
    .map((entry) => ({
      id: entry.id ?? crypto.randomUUID(),
      employeeId: entry.employeeId ?? entry.employee_id ?? entry.employee ?? '',
      date: entry.date ?? entry.work_date ?? entry.workDate ?? '',
      hours: Number(entry.hours ?? entry.duration ?? 0),
    }))
    .filter((entry) => entry.employeeId);

  const payrollRuns = await api('/payroll').catch(() => []);
  state.payrollRuns = payrollRuns.map((run) => ({
    id: run.id ?? crypto.randomUUID(),
    start: run.start ?? run.period_start ?? run.start_date ?? '',
    end: run.end ?? run.period_end ?? run.end_date ?? '',
    paymentDate: run.paymentDate ?? run.payment_date ?? run.pay_date ?? '',
    status: run.status ?? 'processed',
    headcount: run.headcount ?? run.entries?.length ?? 0,
    netTotal: Number(run.netTotal ?? run.total_net ?? run.total_gross ?? 0),
    entries: run.entries ?? [],
  }));

  state.users = await api('/users').catch(() => []);
}

const $ = (id) => document.getElementById(id);

const statusBanner = () => $('api-status');

function setStatus(message, tone = 'info') {
  const el = statusBanner();
  if (!el) return;

  el.textContent = message;
  el.className = `api-status ${tone}`;
}

function localISODate(d = new Date()) {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function renderEmployees(filter = '') {
  const tbody = $('employee-table');
  const query = filter.toLowerCase();
  tbody.innerHTML = '';

  state.employees
    .filter((emp) => emp.name.toLowerCase().includes(query))
    .forEach((emp) => {
      const row = document.createElement('tr');
      const payLabel =
        emp.type === 'hourly'
          ? `${formatCurrency(emp.rate)}/hr`
          : `${formatCurrency(emp.rate)} salary`;

      row.innerHTML = `
        <td>
          <div class="strong">${emp.name}</div>
          <div class="muted small">${emp.tax} withholding</div>
        </td>
        <td>${emp.role || '—'}</td>
        <td>${payLabel}</td>
        <td><span class="badge ${emp.status}">${emp.status.replace('_', ' ')}</span></td>
        <td><button class="btn ghost" data-remove="${emp.id}">Remove</button></td>
      `;

      tbody.appendChild(row);
    });
}

function renderUsers() {
  const tbody = $('user-table');
  if (!tbody) return;

  tbody.innerHTML = '';

  state.users
    .slice()
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .forEach((user) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td><div class="strong">${user.email}</div></td>
        <td><span class="badge">${user.role.replace('_', ' ')}</span></td>
        <td>${formatDateTime(user.created_at)}</td>
      `;
      tbody.appendChild(row);
    });
}

function renderEmployeeOptions() {
  const select = $('time-employee');
  select.innerHTML = '';

  state.employees
    .filter((emp) => emp.status === 'active')
    .forEach((emp) => {
      const option = document.createElement('option');
      option.value = emp.id;
      option.textContent = emp.name;
      select.appendChild(option);
    });
}

function renderTimeEntries(range = '7') {
  const tbody = $('time-table');
  tbody.innerHTML = '';

  const now = Date.now();
  let entries = [...state.timeEntries];

  if (range !== 'all') {
    const days = parseInt(range, 10);
    entries = entries.filter(
      (entry) => now - new Date(entry.date).getTime() <= days * 86400000
    );
  }

  entries.sort((a, b) => new Date(b.date) - new Date(a.date));

  entries.forEach((entry) => {
    const emp = state.employees.find((e) => e.id === entry.employeeId);
    const row = document.createElement('tr');

    row.innerHTML = `
      <td>${emp ? emp.name : 'Former employee'}</td>
      <td>${entry.date}</td>
      <td>${entry.hours}</td>
      <td><button class="btn ghost" data-remove-time="${entry.id}">Delete</button></td>
    `;

    tbody.appendChild(row);
  });
}

function computeDeductions(gross, taxProfile) {
  const baseFederal = 0.1 * gross;
  const baseState = 0.05 * gross;

  let modifier = 1;
  if (taxProfile === 'high') modifier = 1.2;
  if (taxProfile === 'low') modifier = 0.8;

  const benefits = gross * 0.03;
  const total = (baseFederal + baseState) * modifier + benefits;

  return {
    total,
    federal: baseFederal * modifier,
    state: baseState * modifier,
    benefits,
  };
}

function runPayroll({ start, end, notes, paymentDate }) {
  if (!paymentDate) {
    alert('Payment date is required to run payroll.');
    return;
  }
  const periodStart = new Date(start);
  const periodEnd = new Date(end);

  const run = {
    id: crypto.randomUUID(),
    status: 'draft',
    start,
    end,
    notes,
    paymentDate,
    createdAt: new Date().toISOString(),
    entries: [],
  };

  state.employees.forEach((emp) => {
    const entries = state.timeEntries.filter(
      (t) =>
        t.employeeId === emp.id &&
        new Date(t.date) >= periodStart &&
        new Date(t.date) <= periodEnd
    );

    const hours = entries.reduce((sum, e) => sum + Number(e.hours), 0);
    const gross = emp.type === 'hourly' ? emp.rate * hours : emp.rate;

    if (gross === 0 && emp.type === 'hourly') return;

    const deductions = computeDeductions(gross, emp.tax);
    const net = Math.max(gross - deductions.total, 0);

    run.entries.push({
      employeeId: emp.id,
      hours,
      gross,
      deductions,
      net,
    });
  });

  run.netTotal = run.entries.reduce((sum, e) => sum + e.net, 0);
  run.headcount = run.entries.length;

  state.payrollRuns.unshift(run);

  renderPayroll();
  renderMetrics();
  renderReports();
  renderPreview(run);
}

function renderPayroll(filter = 'all') {
  const tbody = $('payroll-table');
  tbody.innerHTML = '';

  state.payrollRuns
    .filter((run) => filter === 'all' || run.status === filter)
    .forEach((run) => {
      const row = document.createElement('tr');

      row.innerHTML = `
        <td>${formatDateTime(run.paymentDate)}</td>
        <td>${run.start} → ${run.end}</td>
        <td><span class="badge ${run.status}">${run.status}</span></td>
        <td>${run.headcount}</td>
        <td>${formatCurrency(run.netTotal)}</td>
        <td class="actions" data-id="${run.id}">
          <button class="btn primary" data-action="process">Mark processed</button>
          <button class="btn ghost" data-action="preview">Preview</button>
        </td>
      `;

      tbody.appendChild(row);
    });
}

function renderPreview(run) {
  if (!run) {
    $('payroll-preview').innerHTML =
      '<p class="muted">Generate a run to see the breakdown.</p>';
    return;
  }

  const employees = run.entries
    .map((entry) => {
      const emp = state.employees.find((e) => e.id === entry.employeeId);
      return `<li><strong>${
        emp ? emp.name : 'Former employee'
      }</strong> — ${formatCurrency(entry.net)} net (${formatCurrency(
        entry.gross
      )} gross, ${formatCurrency(entry.deductions.total)} deductions)</li>`;
    })
    .join('');

  $('payroll-preview').innerHTML = `
    <h3>Run ${run.start} → ${run.end}</h3>
    <p class="muted">${run.notes || 'No notes'} · ${run.status.toUpperCase()} · ${
    run.entries.length
  } employees</p>
    <ul>${employees}</ul>
    <p><strong>Total net:</strong> ${formatCurrency(run.netTotal)}</p>
  `;
}

function renderMetrics() {
  $('metric-employees').textContent = state.employees.length;

  const pendingHours = state.timeEntries.reduce((sum, e) => sum + Number(e.hours), 0);
  $('metric-hours').textContent = pendingHours.toFixed(1);

  const lastRun = state.payrollRuns[0];
  $('metric-last').textContent = lastRun ? formatCurrency(lastRun.netTotal) : '—';

  const drafts = state.payrollRuns.filter((r) => r.status === 'draft').length;
  $('metric-drafts').textContent = drafts;
}

function renderReports() {
  const labor = $('labor-mix');
  labor.innerHTML = '';

  const latest = state.payrollRuns[0];
  if (latest) {
    const hourly = latest.entries
      .filter((e) => {
        const emp = state.employees.find((x) => x.id === e.employeeId);
        return emp?.type === 'hourly';
      })
      .reduce((sum, e) => sum + e.net, 0);

    const salary = latest.entries
      .filter((e) => {
        const emp = state.employees.find((x) => x.id === e.employeeId);
        return emp?.type === 'salary';
      })
      .reduce((sum, e) => sum + e.net, 0);

    const total = hourly + salary || 1;

    const items = [
      { label: 'Hourly', value: hourly, pct: Math.round((hourly / total) * 100) },
      { label: 'Salary', value: salary, pct: Math.round((salary / total) * 100) },
    ];

    items.forEach((item) => {
      const li = document.createElement('li');
      li.textContent = `${item.label}: ${formatCurrency(item.value)} (${item.pct}% )`;
      labor.appendChild(li);
    });
  } else {
    labor.innerHTML = '<li class="muted">Run payroll to see labor mix</li>';
  }

  const audit = $('audit-log');
  audit.innerHTML = '';

  state.payrollRuns.slice(0, 5).forEach((run) => {
    const item = document.createElement('div');
    item.className = 'audit-item';
    item.innerHTML = `
      <div class="strong">${run.start} → ${run.end} · ${run.status.toUpperCase()}</div>
      <div class="muted small">${run.entries.length} employees · ${formatCurrency(
      run.netTotal
    )} net · ${run.notes || 'No notes'}</div>
    `;
    audit.appendChild(item);
  });

  const trend = $('net-trend');
  trend.innerHTML = '';

  state.payrollRuns.slice(0, 5).forEach((run, index) => {
    const li = document.createElement('li');
    li.textContent = `#${state.payrollRuns.length - index} · ${formatCurrency(run.netTotal)}`;
    trend.appendChild(li);
  });
}

function attachHandlers() {
  $('user-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = new FormData(e.target);

    const payload = {
      email: form.get('email'),
      role: form.get('role'),
      password: form.get('password'),
    };

    try {
      const created = await api('/users', { method: 'POST', body: payload });
      state.users.unshift(created);

      renderUsers();
      e.target.reset();
      $('user-role').value = 'viewer';
    } catch (err) {
      console.error('Failed to create user', err);
      alert(String(err));
    }
  });

  $('employee-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = new FormData(e.target);

    const payload = {
      name: form.get('name'),
      role: form.get('role'),
      type: form.get('type'),
      rate: Number(form.get('rate')),
      defaultHours: Number(form.get('defaultHours')) || 0,
      status: form.get('status'),
      tax: form.get('tax'),
    };

    try {
      const created = await api('/employees', { method: 'POST', body: payload });
      state.employees.unshift(created);

      renderEmployees($('employee-search').value);
      renderEmployeeOptions();
      renderMetrics();
      e.target.reset();
    } catch (err) {
      console.error('Failed to create employee', err);
      alert(String(err));
    }
  });

  $('employee-table').addEventListener('click', async (e) => {
    const id = e.target.getAttribute('data-remove');
    if (!id) return;

    try {
      await api(`/employees/${id}`, { method: 'DELETE' });

      state.employees = state.employees.filter((emp) => String(emp.id) !== String(id));
      state.timeEntries = state.timeEntries.filter((t) => String(t.employeeId) !== String(id));

      renderEmployees($('employee-search').value);
      renderEmployeeOptions();
      renderTimeEntries($('time-range').value);
      renderMetrics();
    } catch (err) {
      console.error('Failed to delete employee', err);
      alert(String(err));
    }
  });

  $('employee-search').addEventListener('input', (e) => renderEmployees(e.target.value));

  $('time-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const form = new FormData(e.target);

    state.timeEntries.unshift({
      id: crypto.randomUUID(),
      employeeId: form.get('employee'),
      date: form.get('date'),
      hours: Number(form.get('hours')),
    });

    renderTimeEntries($('time-range').value);
    renderMetrics();
    e.target.reset();
    $('time-date').value = localISODate();
  });

  $('time-table').addEventListener('click', (e) => {
    const id = e.target.getAttribute('data-remove-time');
    if (!id) return;

    state.timeEntries = state.timeEntries.filter((entry) => entry.id !== id);
    renderTimeEntries($('time-range').value);
    renderMetrics();
  });

  $('time-range').addEventListener('change', (e) => renderTimeEntries(e.target.value));

  $('payroll-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    runPayroll({
      start: form.get('start'),
      end: form.get('end'),
      notes: form.get('notes'),
      paymentDate: form.get('paymentDate'),
    });
    e.target.reset();
  });

  $('payroll-filter').addEventListener('change', (e) => renderPayroll(e.target.value));

  $('payroll-table').addEventListener('click', (e) => {
    const action = e.target.getAttribute('data-action');
    if (!action) return;

    const runId = e.target.closest('.actions').dataset.id;
    const run = state.payrollRuns.find((r) => r.id === runId);
    if (!run) return;

    if (action === 'process') {
      run.status = 'processed';
      renderPayroll($('payroll-filter').value);
      renderMetrics();
      renderReports();
      renderPreview(run);
    }

    if (action === 'preview') {
      renderPreview(run);
    }
  });

  $('quick-run').addEventListener('click', () => {
    document.querySelector('a[href="#payroll"]').scrollIntoView({ behavior: 'smooth' });
  });

  $('quick-add').addEventListener('click', () => {
    document.querySelector('a[href="#employees"]').scrollIntoView({ behavior: 'smooth' });
  });

  const navToggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');

  navToggle.addEventListener('click', () => {
    const open = navLinks.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', String(open));
  });

  navLinks.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      navLinks.classList.remove('open');
      navToggle.setAttribute('aria-expanded', 'false');
    });
  });
}

let HANDLERS_BOUND = false;

async function init() {
  try {
    await probeApi();
    await loadStateFromApi();
    setStatus('Connected to payroll API', 'success');
  } catch (e) {
    setStatus('Cannot reach the payroll API. Please start the backend and reload.', 'error');
    return;
  }

  renderEmployees();
  renderEmployeeOptions();
  renderTimeEntries();
  renderPayroll();
  renderMetrics();
  renderReports();
  renderUsers();
  renderPreview();

  $('time-date').value = localISODate();

  if (!HANDLERS_BOUND) {
    attachHandlers();
    HANDLERS_BOUND = true;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  init().catch((e) => console.error('init failed', e));
});

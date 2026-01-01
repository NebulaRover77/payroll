const state = {
  employees: [],
  timeEntries: [],
  payrollRuns: [],
};

const storageKey = 'nebulaPayrollState';

const $ = (id) => document.getElementById(id);

function loadState() {
  const saved = localStorage.getItem(storageKey);
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      state.employees = parsed.employees || [];
      state.timeEntries = parsed.timeEntries || [];
      state.payrollRuns = parsed.payrollRuns || [];
      return;
    } catch (e) {
      console.warn('Could not parse saved state', e);
    }
  }
  seedData();
}

function saveState() {
  localStorage.setItem(storageKey, JSON.stringify(state));
}

function seedData() {
  state.employees = [
    { id: crypto.randomUUID(), name: 'Alex Chen', role: 'Payroll Analyst', type: 'salary', rate: 3600, defaultHours: 80, status: 'active', tax: 'standard' },
    { id: crypto.randomUUID(), name: 'Priya Patel', role: 'Support Lead', type: 'hourly', rate: 38, defaultHours: 80, status: 'active', tax: 'low' },
    { id: crypto.randomUUID(), name: 'Marcos Diaz', role: 'Implementation', type: 'hourly', rate: 42, defaultHours: 60, status: 'on_leave', tax: 'standard' },
  ];
  const today = new Date();
  const dayMs = 86400000;
  state.timeEntries = [
    { id: crypto.randomUUID(), employeeId: state.employees[1].id, date: new Date(today - dayMs * 2).toISOString().slice(0, 10), hours: 8 },
    { id: crypto.randomUUID(), employeeId: state.employees[1].id, date: new Date(today - dayMs * 3).toISOString().slice(0, 10), hours: 7.5 },
    { id: crypto.randomUUID(), employeeId: state.employees[0].id, date: new Date(today - dayMs * 4).toISOString().slice(0, 10), hours: 8 },
  ];
  state.payrollRuns = [];
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

function renderEmployees(filter = '') {
  const tbody = $('employee-table');
  const query = filter.toLowerCase();
  tbody.innerHTML = '';
  state.employees
    .filter((emp) => emp.name.toLowerCase().includes(query))
    .forEach((emp) => {
      const row = document.createElement('tr');
      const payLabel = emp.type === 'hourly' ? `${formatCurrency(emp.rate)}/hr` : `${formatCurrency(emp.rate)} salary`;
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
    entries = entries.filter((entry) => now - new Date(entry.date).getTime() <= days * 86400000);
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
  return { total, federal: baseFederal * modifier, state: baseState * modifier, benefits };
}

function runPayroll({ start, end, notes }) {
  const periodStart = new Date(start);
  const periodEnd = new Date(end);
  const run = {
    id: crypto.randomUUID(),
    status: 'draft',
    start,
    end,
    notes,
    createdAt: new Date().toISOString(),
    entries: [],
  };

  state.employees.forEach((emp) => {
    const entries = state.timeEntries.filter((t) => t.employeeId === emp.id && new Date(t.date) >= periodStart && new Date(t.date) <= periodEnd);
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
  saveState();
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
    $('payroll-preview').innerHTML = '<p class="muted">Generate a run to see the breakdown.</p>';
    return;
  }
  const employees = run.entries
    .map((entry) => {
      const emp = state.employees.find((e) => e.id === entry.employeeId);
      return `<li><strong>${emp ? emp.name : 'Former employee'}</strong> — ${formatCurrency(entry.net)} net (${formatCurrency(entry.gross)} gross, ${formatCurrency(entry.deductions.total)} deductions)</li>`;
    })
    .join('');
  $('payroll-preview').innerHTML = `
    <h3>Run ${run.start} → ${run.end}</h3>
    <p class="muted">${run.notes || 'No notes'} · ${run.status.toUpperCase()} · ${run.entries.length} employees</p>
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
    const hourly = latest.entries.filter((e) => {
      const emp = state.employees.find((x) => x.id === e.employeeId);
      return emp?.type === 'hourly';
    }).reduce((sum, e) => sum + e.net, 0);
    const salary = latest.entries.filter((e) => {
      const emp = state.employees.find((x) => x.id === e.employeeId);
      return emp?.type === 'salary';
    }).reduce((sum, e) => sum + e.net, 0);
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
      <div class="muted small">${run.entries.length} employees · ${formatCurrency(run.netTotal)} net · ${run.notes || 'No notes'}</div>
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
  $('employee-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    const employee = {
      id: crypto.randomUUID(),
      name: form.get('name'),
      role: form.get('role'),
      type: form.get('type'),
      rate: Number(form.get('rate')),
      defaultHours: Number(form.get('defaultHours')) || 0,
      status: form.get('status'),
      tax: form.get('tax'),
    };
    state.employees.unshift(employee);
    saveState();
    renderEmployees($('employee-search').value);
    renderEmployeeOptions();
    renderMetrics();
    e.target.reset();
  });

  $('employee-table').addEventListener('click', (e) => {
    const id = e.target.getAttribute('data-remove');
    if (!id) return;
    state.employees = state.employees.filter((emp) => emp.id !== id);
    state.timeEntries = state.timeEntries.filter((t) => t.employeeId !== id);
    saveState();
    renderEmployees($('employee-search').value);
    renderEmployeeOptions();
    renderTimeEntries($('time-range').value);
    renderMetrics();
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
    saveState();
    renderTimeEntries($('time-range').value);
    renderMetrics();
    e.target.reset();
  });

  $('time-table').addEventListener('click', (e) => {
    const id = e.target.getAttribute('data-remove-time');
    if (!id) return;
    state.timeEntries = state.timeEntries.filter((entry) => entry.id !== id);
    saveState();
    renderTimeEntries($('time-range').value);
    renderMetrics();
  });

  $('time-range').addEventListener('change', (e) => renderTimeEntries(e.target.value));

  $('payroll-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    runPayroll({ start: form.get('start'), end: form.get('end'), notes: form.get('notes') });
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
      saveState();
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

function init() {
  loadState();
  renderEmployees();
  renderEmployeeOptions();
  renderTimeEntries();
  renderPayroll();
  renderMetrics();
  renderReports();
  renderPreview();
  attachHandlers();
}

document.addEventListener('DOMContentLoaded', init);

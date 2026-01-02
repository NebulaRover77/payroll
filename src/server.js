const http = require('http');
const fs = require('fs');
const path = require('path');
const { randomUUID } = require('crypto');
const {
  validateSetup,
  validatePartialSetup,
  EIN_REGEX,
  STATES
} = require('./validators');
const { loadSetup, saveSetup, appendAuditEvent, loadAuditLog } = require('./storage');

const ADMIN_TOKEN = process.env.ADMIN_TOKEN || 'changeme';
const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname, '..', 'public');
const DATA_DIR = path.join(__dirname, '..', 'data');
const DATA_STORE_PATH = path.join(DATA_DIR, 'store.json');
const defaultStore = { employees: [], pay_periods: [], time_entries: [], pto_requests: [] };

function sendJson(res, status, payload) {
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, X-Admin-Token'
  });
  res.end(JSON.stringify(payload));
}

function sendFile(res, filePath) {
  const ext = path.extname(filePath);
  const mime =
    ext === '.js'
      ? 'text/javascript'
      : ext === '.css'
        ? 'text/css'
        : 'text/html';
  res.writeHead(200, { 'Content-Type': mime });
  fs.createReadStream(filePath).pipe(res);
}

function requireAdmin(req, res) {
  const token = req.headers['x-admin-token'];
  if (!token || token !== ADMIN_TOKEN) {
    sendJson(res, 403, { error: 'Admin token required' });
    return false;
  }
  return true;
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => {
      data += chunk.toString();
      if (data.length > 1_000_000) req.connection.destroy();
    });
    req.on('end', () => {
      if (!data) return resolve({});
      try {
        resolve(JSON.parse(data));
      } catch (error) {
        reject(error);
      }
    });
  });
}

function ensureDataDir() {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
}

function readStore() {
  ensureDataDir();
  if (!fs.existsSync(DATA_STORE_PATH)) {
    return { ...defaultStore };
  }
  try {
    const content = fs.readFileSync(DATA_STORE_PATH, 'utf-8');
    const parsed = JSON.parse(content || '{}');
    return { ...defaultStore, ...parsed, employees: parsed.employees || [] };
  } catch (error) {
    console.error('Unable to read data store', error);
    return { ...defaultStore };
  }
}

function saveStore(store) {
  ensureDataDir();
  fs.writeFileSync(DATA_STORE_PATH, JSON.stringify(store, null, 2));
}

function loadEmployees() {
  const parsed = readStore();
  const employees = Array.isArray(parsed.employees) ? parsed.employees : [];
  return employees.sort((a, b) => (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' }));
}

function loadEmployeeById(employeeId) {
  const employees = loadEmployees();
  return employees.find((employee) => employee.id === employeeId);
}

function loadPaySchedules() {
  const setup = loadSetup();
  const schedules = Array.isArray(setup.paySchedules) ? setup.paySchedules : [];
  if (schedules.length === 0) {
    return [{ name: 'Monthly', cadence: 'monthly' }];
  }
  return schedules;
}

function audit(actor, action, payload) {
  appendAuditEvent({ id: randomUUID(), actor, action, payload, timestamp: new Date().toISOString() });
}

function handleApi(req, res) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  if (req.method === 'OPTIONS') {
    res.writeHead(200, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type, X-Admin-Token',
      'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    });
    return res.end();
  }

  if (req.method === 'GET' && url.pathname === '/api/setup') {
    const setup = loadSetup();
    return sendJson(res, 200, { setup, payrollEnabled: Boolean(setup.completed) });
  }

  if (req.method === 'GET' && url.pathname === '/api/payroll/status') {
    const setup = loadSetup();
    return sendJson(res, 200, {
      enabled: Boolean(setup.completed),
      reason: setup.completed ? null : 'Complete the company setup wizard before running payroll.'
    });
  }

  if (req.method === 'GET' && url.pathname === '/api/employees') {
    try {
      return sendJson(res, 200, { employees: loadEmployees() });
    } catch (error) {
      console.error('Failed to load employees', error);
      return sendJson(res, 500, { error: 'Unable to load employees' });
    }
  }

  if (req.method === 'POST' && url.pathname === '/api/employees') {
    return parseBody(req)
      .then((body) => {
        const firstName = (body.first_name || body.firstName || '').trim();
        const middleName = (body.middle_name || body.middleName || '').trim();
        const lastName = (body.last_name || body.lastName || '').trim();
        const ssn = (body.ssn || '').trim();
        const dob = (body.dob || '').trim();
        const address = (body.address || '').trim();
        const email = (body.email || '').trim();
        const phone = (body.phone || body.cell_phone || '').trim();
        const paySchedule = (body.pay_schedule || body.paySchedule || '').trim();
        const department = (body.department || '').trim();
        const providedId = (body.id || '').trim();
        const ptoBalance = Number(body.pto_balance_hours ?? body.pto ?? 0);

        const payScheduleNames = loadPaySchedules()
          .map((schedule) => schedule.name)
          .filter(Boolean);

        if (!firstName || !lastName || !ssn || !dob || !address || !paySchedule) {
          return sendJson(res, 400, { error: 'First name, last name, SSN, DOB, address, and pay schedule are required' });
        }

        if (!/^\d{3}-?\d{2}-?\d{4}$/.test(ssn)) {
          return sendJson(res, 400, { error: 'SSN must match ###-##-####' });
        }

        if (Number.isNaN(Date.parse(dob))) {
          return sendJson(res, 400, { error: 'Provide a valid date of birth' });
        }

        if (payScheduleNames.length && !payScheduleNames.map((n) => n.toLowerCase()).includes(paySchedule.toLowerCase())) {
          return sendJson(res, 400, { error: 'Select a valid pay schedule' });
        }

        const employee = {
          id: providedId || randomUUID(),
          name: [firstName, middleName, lastName].filter(Boolean).join(' '),
          first_name: firstName,
          middle_name: middleName,
          last_name: lastName,
          ssn,
          dob,
          address,
          email,
          phone,
          pay_schedule: paySchedule,
          department,
          pto_balance_hours: Number.isFinite(ptoBalance) ? ptoBalance : 0
        };

        const store = readStore();
        const employees = Array.isArray(store.employees) ? store.employees : [];
        const existingIndex = employees.findIndex((item) => item.id === employee.id);
        if (existingIndex >= 0) {
          employees[existingIndex] = employee;
        } else {
          employees.push(employee);
        }

        saveStore({ ...store, employees });
        audit('user', 'employee.add', { id: employee.id, name: employee.name });
        return sendJson(res, 201, { employee });
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
  }

  if (req.method === 'GET' && url.pathname.startsWith('/api/employees/')) {
    try {
      const employeeId = decodeURIComponent(url.pathname.replace('/api/employees/', ''));
      if (!employeeId) {
        return sendJson(res, 400, { error: 'Employee ID is required' });
      }
      const employee = loadEmployeeById(employeeId);
      if (!employee) {
        return sendJson(res, 404, { error: 'Employee not found' });
      }
      return sendJson(res, 200, { employee });
    } catch (error) {
      console.error('Failed to load employee', error);
      return sendJson(res, 500, { error: 'Unable to load employee' });
    }
  }

  if (req.method === 'GET' && url.pathname === '/api/metadata') {
    return sendJson(res, 200, {
      einPattern: EIN_REGEX.toString(),
      states: STATES,
      cadenceOptions: ['weekly', 'biweekly', 'semimonthly', 'monthly'],
      filingFrequencies: ['monthly', 'quarterly', 'annual'],
      paySchedules: loadPaySchedules().map((schedule) => ({
        name: schedule.name,
        cadence: schedule.cadence || 'monthly'
      }))
    });
  }

  if (url.pathname === '/api/admin/audit') {
    if (!requireAdmin(req, res)) return true;
    if (req.method === 'GET') {
      return sendJson(res, 200, loadAuditLog());
    }
  }

  if (url.pathname === '/api/admin/setup' && req.method === 'POST') {
    if (!requireAdmin(req, res)) return true;
    return parseBody(req)
      .then((body) => {
        const result = validateSetup(body);
        if (!result.valid) return sendJson(res, 400, { error: 'Validation failed', details: result.errors });
        const saved = saveSetup({ ...body, completed: !!body.completed, currentStep: 'complete' });
        audit('admin', 'setup.upsert', { company: saved.company?.legalName, completed: saved.completed });
        sendJson(res, 200, saved);
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
  }

  if (url.pathname === '/api/admin/progress' && req.method === 'POST') {
    if (!requireAdmin(req, res)) return true;
    return parseBody(req)
      .then((body) => {
        const result = validatePartialSetup(body);
        if (!result.valid) return sendJson(res, 400, { error: 'Validation failed', details: result.errors });
        const saved = saveSetup({ ...body, completed: false });
        audit('admin', 'setup.progress', { currentStep: saved.currentStep, company: saved.company?.legalName });
        sendJson(res, 200, saved);
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
  }

  if (url.pathname === '/api/admin/reset' && req.method === 'POST') {
    if (!requireAdmin(req, res)) return true;
    const saved = saveSetup({ company: null, addresses: [], taxAccounts: [], paySchedules: [], completed: false, currentStep: 'company' });
    audit('admin', 'setup.reset', {});
    return sendJson(res, 200, saved);
  }

  return false;
}

function handleStatic(req, res) {
  const urlPath = req.url.split('?')[0];
  const filePath = urlPath === '/' ? path.join(PUBLIC_DIR, 'index.html') : path.join(PUBLIC_DIR, urlPath);
  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    return sendFile(res, filePath);
  }
  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not found');
}

const server = http.createServer((req, res) => {
  try {
    const handled = handleApi(req, res);
    if (handled === false) {
      return handleStatic(req, res);
    }
  } catch (error) {
    console.error(error);
    sendJson(res, 500, { error: 'Internal server error' });
  }
});

server.listen(PORT, () => {
  console.log(`Payroll wizard server running on http://localhost:${PORT}`);
});

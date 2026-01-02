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
const DATA_STORE_PATH = path.join(__dirname, '..', 'data', 'store.json');

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

function loadEmployees() {
  if (!fs.existsSync(DATA_STORE_PATH)) return [];
  const content = fs.readFileSync(DATA_STORE_PATH, 'utf-8');
  const parsed = JSON.parse(content || '{}');
  const employees = Array.isArray(parsed.employees) ? parsed.employees : [];
  return employees.sort((a, b) => (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' }));
}

function loadEmployeeById(employeeId) {
  const employees = loadEmployees();
  return employees.find((employee) => employee.id === employeeId);
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
      filingFrequencies: ['monthly', 'quarterly', 'annual']
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

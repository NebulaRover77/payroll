const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');
const { randomUUID } = require('crypto');
const {
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
const DEFAULT_PAY_TYPES = [
  { id: 'regular', name: 'Regular' },
  { id: 'vacation', name: 'Vacation' },
  { id: 'holiday', name: 'Holiday' }
];
const defaultStore = {
  employees: [],
  pay_periods: [],
  time_entries: [],
  pto_requests: [],
  pay_types: DEFAULT_PAY_TYPES,
  payroll_runs: [],
  payroll_history: []
};
const ZIP_REGEX = /^\d{5}(-\d{4})?$/;
const PAY_CADENCE_OPTIONS = ['weekly', 'biweekly', 'semimonthly', 'monthly'];
const EMPLOYMENT_STATUSES = ['Active', 'On Leave', 'Terminated'];

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

function runStubPdfExport({ entryId }) {
  return new Promise((resolve, reject) => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'paystub-'));
    const outputPath = path.join(tempDir, `pay-stub-${entryId}.pdf`);
    const setupPath = path.join(DATA_DIR, 'setup.json');
    const scriptArgs = [
      '-m',
      'payroll_reports.web_stub_export',
      '--store-path',
      DATA_STORE_PATH,
      '--setup-path',
      setupPath,
      '--entry-id',
      entryId,
      '--output',
      outputPath
    ];
    const pythonPath = process.env.PAYROLL_PDF_PYTHON || 'python3';
    const childProcess = spawn(pythonPath, scriptArgs, { stdio: 'pipe' });
    let stderr = '';
    childProcess.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    childProcess.on('close', (code) => {
      if (code !== 0) {
        return reject(new Error(stderr || 'PDF generation failed.'));
      }
      return resolve({ outputPath, tempDir });
    });
  });
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

function getPayTypes(store) {
  const payTypes = Array.isArray(store.pay_types) && store.pay_types.length ? store.pay_types : DEFAULT_PAY_TYPES;
  return payTypes.map((type) => ({ id: type.id, name: type.name }));
}

function ensurePayTypeFlags(current, payTypes) {
  const enabled = {};
  payTypes.forEach((type) => {
    enabled[type.id] = current?.[type.id] ?? true;
  });
  return enabled;
}

function loadEmployees() {
  const parsed = readStore();
  const payTypes = getPayTypes(parsed);
  const employees = Array.isArray(parsed.employees) ? parsed.employees : [];
  return employees
    .map((employee) => ({
      ...employee,
      pay_types_enabled: ensurePayTypeFlags(employee.pay_types_enabled, payTypes)
    }))
    .sort((a, b) => (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' }));
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
  if (req.method === 'POST' && url.pathname === '/api/setup') {
    return parseBody(req)
      .then((body) => {
        const result = validatePartialSetup({ company: body.company, addresses: body.addresses });
        if (!result.valid) return sendJson(res, 400, { error: 'Validation failed', details: result.errors });
        const saved = saveSetup({ ...body, completed: !!body.completed, currentStep: 'complete' });
        audit('user', 'setup.upsert', { company: saved.company?.legalName, completed: saved.completed });
        return sendJson(res, 200, saved);
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
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
        const hireDate = (body.hire_date || body.hireDate || '').trim();
        const addressLine1 = (body.address_line1 || body.addressLine1 || '').trim();
        const addressLine2 = (body.address_line2 || body.addressLine2 || '').trim();
        const city = (body.city || '').trim();
        const state = (body.state || '').trim();
        const postalCode = (body.postal_code || body.postalCode || '').trim();
        const email = (body.email || '').trim();
        const phone = (body.phone || body.cell_phone || '').trim();
        const paySchedule = (body.pay_schedule || body.paySchedule || '').trim();
        const department = (body.department || '').trim();
        const providedId = (body.id || '').trim();
        const ptoBalance = Number(body.pto_balance_hours ?? body.pto ?? 0);
        const statusInput = (body.status || '').trim();
        const status = statusInput
          ? EMPLOYMENT_STATUSES.find((item) => item.toLowerCase() === statusInput.toLowerCase())
          : 'Active';
        const payRateTypeRaw = (body.pay_rate_type || body.payRateType || '').trim();
        const payRateType = payRateTypeRaw.toLowerCase() === 'period' ? 'period' : payRateTypeRaw.toLowerCase() === 'hourly' ? 'hourly' : '';
        const payRateValue = body.pay_rate ?? body.payRate;
        const parsedPayRate = Number(payRateValue);
        const payTypeRaw = (body.pay_type || body.payType || '').trim();

        const addressParts = [
          addressLine1,
          addressLine2,
          [city, state].filter(Boolean).join(', '),
          postalCode
        ].filter(Boolean);
        const address = addressParts.join('\n');

        const payScheduleNames = loadPaySchedules()
          .map((schedule) => schedule.name)
          .filter(Boolean);

        if (!firstName || !lastName || !addressLine1 || !postalCode || !paySchedule) {
          return sendJson(res, 400, { error: 'First name, last name, address line 1, zip, and pay schedule are required' });
        }

        if (ssn && !/^\d{3}-?\d{2}-?\d{4}$/.test(ssn)) {
          return sendJson(res, 400, { error: 'SSN must match ###-##-####' });
        }

        if (dob && Number.isNaN(Date.parse(dob))) {
          return sendJson(res, 400, { error: 'Provide a valid date of birth' });
        }

        if (hireDate && Number.isNaN(Date.parse(hireDate))) {
          return sendJson(res, 400, { error: 'Provide a valid hire date' });
        }

        if (postalCode && !ZIP_REGEX.test(postalCode)) {
          return sendJson(res, 400, { error: 'Provide a valid zip code' });
        }

        if (payScheduleNames.length && !payScheduleNames.map((n) => n.toLowerCase()).includes(paySchedule.toLowerCase())) {
          return sendJson(res, 400, { error: 'Select a valid pay schedule' });
        }

        if (statusInput && !status) {
          return sendJson(res, 400, { error: 'Select a valid status' });
        }

        const store = readStore();
        const payTypes = getPayTypes(store);
        const employees = Array.isArray(store.employees) ? store.employees : [];
        const existingIndex = employees.findIndex((item) => item.id === (providedId || body.id || ''));
        const existingEmployee = existingIndex >= 0 ? employees[existingIndex] : null;

        const employee = {
          id: providedId || randomUUID(),
          name: [firstName, middleName, lastName].filter(Boolean).join(' '),
          first_name: firstName,
          middle_name: middleName,
          last_name: lastName,
          ssn,
          dob,
          hire_date: hireDate,
          address,
          address_line1: addressLine1,
          address_line2: addressLine2,
          city,
          state,
          postal_code: postalCode,
          email,
          phone,
          pay_schedule: paySchedule,
          status,
          department,
          pto_balance_hours: Number.isFinite(ptoBalance) ? ptoBalance : 0,
          pay_rate_type: payRateType || existingEmployee?.pay_rate_type || '',
          pay_rate: Number.isFinite(parsedPayRate) ? parsedPayRate : existingEmployee?.pay_rate || 0,
          pay_type: payTypeRaw || existingEmployee?.pay_type || '',
          pay_types_enabled: ensurePayTypeFlags(body.pay_types_enabled || body.payTypesEnabled || existingEmployee?.pay_types_enabled, payTypes),
          w4: existingEmployee?.w4 || null,
          tax_exemptions: existingEmployee?.tax_exemptions || null
        };

        const index = employees.findIndex((item) => item.id === employee.id);
        if (index >= 0) {
          employees[index] = employee;
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
      cadenceOptions: PAY_CADENCE_OPTIONS,
      filingFrequencies: ['monthly', 'quarterly', 'annual'],
      paySchedules: loadPaySchedules().map((schedule) => ({
        name: schedule.name,
        cadence: schedule.cadence || 'monthly'
      }))
    });
  }

  if (req.method === 'GET' && url.pathname === '/api/pay-types') {
    const store = readStore();
    return sendJson(res, 200, { payTypes: getPayTypes(store) });
  }

  if (req.method === 'POST' && url.pathname === '/api/pay-types/assignments') {
    return parseBody(req)
      .then((body) => {
        const assignments = Array.isArray(body.assignments) ? body.assignments : [];
        if (!assignments.length) {
          return sendJson(res, 400, { error: 'Provide at least one assignment update' });
        }
        const store = readStore();
        const payTypes = getPayTypes(store);
        const employees = Array.isArray(store.employees) ? store.employees : [];

        assignments.forEach((assignment) => {
          const employeeId = (assignment.employeeId || '').trim();
          const employee = employees.find((item) => item.id === employeeId);
          if (!employee) return;
          employee.pay_types_enabled = ensurePayTypeFlags(assignment.enabled, payTypes);
        });

        saveStore({ ...store, employees });
        return sendJson(res, 200, { employees: loadEmployees() });
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
  }

  if (req.method === 'POST' && url.pathname.endsWith('/w4') && url.pathname.startsWith('/api/employees/')) {
    return parseBody(req)
      .then((body) => {
        const employeeId = decodeURIComponent(url.pathname.replace('/api/employees/', '').replace('/w4', ''));
        if (!employeeId) {
          return sendJson(res, 400, { error: 'Employee ID is required' });
        }

        const store = readStore();
        const employees = Array.isArray(store.employees) ? store.employees : [];
        const employee = employees.find((item) => item.id === employeeId);
        if (!employee) {
          return sendJson(res, 404, { error: 'Employee not found' });
        }

        employee.w4 = {
          effective_date: body.effective_date || '',
          filing_status: body.filing_status || '',
          tax_exempt: Boolean(body.tax_exempt),
          box2c_checked: Boolean(body.box2c_checked),
          step3: Number(body.step3 || 0),
          step4a: Number(body.step4a || 0),
          step4b: Number(body.step4b || 0),
          step4c: Number(body.step4c || 0),
          document_name: body.document_name || '',
          document_data: body.document_data || ''
        };

        saveStore({ ...store, employees });
        audit('user', 'employee.w4', { employeeId });
        return sendJson(res, 200, { employee });
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
  }

  if (req.method === 'POST' && url.pathname.endsWith('/tax-exemptions') && url.pathname.startsWith('/api/employees/')) {
    return parseBody(req)
      .then((body) => {
        const employeeId = decodeURIComponent(url.pathname.replace('/api/employees/', '').replace('/tax-exemptions', ''));
        if (!employeeId) {
          return sendJson(res, 400, { error: 'Employee ID is required' });
        }

        const store = readStore();
        const employees = Array.isArray(store.employees) ? store.employees : [];
        const employee = employees.find((item) => item.id === employeeId);
        if (!employee) {
          return sendJson(res, 404, { error: 'Employee not found' });
        }

        employee.tax_exemptions = {
          fica_exempt: Boolean(body.fica_exempt),
          fica_end_date: body.fica_end_date || '',
          ss_only_exempt: Boolean(body.ss_only_exempt),
          ss_only_end_date: body.ss_only_end_date || '',
          suta_exempt: Boolean(body.suta_exempt),
          suta_end_date: body.suta_end_date || '',
          futa_exempt: Boolean(body.futa_exempt),
          futa_end_date: body.futa_end_date || '',
          futa_reason: body.futa_reason || ''
        };

        saveStore({ ...store, employees });
        audit('user', 'employee.taxExemptions', { employeeId });
        return sendJson(res, 200, { employee });
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
  }

  if (req.method === 'GET' && url.pathname === '/api/time-entries') {
    const store = readStore();
    const entries = Array.isArray(store.time_entries) ? store.time_entries : [];
    const startDate = url.searchParams.get('start_date');
    const endDate = url.searchParams.get('end_date');
    const status = url.searchParams.get('status');
    const unpaid = url.searchParams.get('unpaid') === 'true';
    const filtered = entries.filter((entry) => {
      if (startDate && entry.start_date !== startDate) return false;
      if (endDate && entry.end_date !== endDate) return false;
      if (status && entry.status !== status) return false;
      if (unpaid && entry.status === 'paid') return false;
      return true;
    });
    return sendJson(res, 200, { entries: filtered });
  }

  if (req.method === 'POST' && url.pathname === '/api/time-entries') {
    return parseBody(req)
      .then((body) => {
        const startDate = (body.start_date || '').trim();
        const endDate = (body.end_date || '').trim();
        const entriesPayload = Array.isArray(body.entries) ? body.entries : [];
        if (!startDate || !endDate) {
          return sendJson(res, 400, { error: 'Start and end dates are required' });
        }
        if (!entriesPayload.length) {
          return sendJson(res, 400, { error: 'Provide at least one entry' });
        }

        const store = readStore();
        const payTypes = getPayTypes(store);
        const employees = Array.isArray(store.employees) ? store.employees : [];
        const entries = Array.isArray(store.time_entries) ? store.time_entries : [];

        for (const payload of entriesPayload) {
          const employeeId = (payload.employeeId || '').trim();
          if (!employeeId) return sendJson(res, 400, { error: 'Employee ID is required' });
          const employee = employees.find((item) => item.id === employeeId);
          if (!employee) return sendJson(res, 404, { error: `Employee not found: ${employeeId}` });

          const hours = {};
          let total = 0;
          payTypes.forEach((type) => {
            const value = Number(payload.hours?.[type.id] || 0);
            if (!Number.isFinite(value)) return;
            const rounded = Math.max(0, Math.round(value * 100) / 100);
            hours[type.id] = rounded;
            total += rounded;
          });

          const existingIndex = entries.findIndex(
            (entry) => entry.employee_id === employeeId && entry.start_date === startDate && entry.end_date === endDate
          );
          if (total === 0 && existingIndex >= 0 && entries[existingIndex].status !== 'paid') {
            entries.splice(existingIndex, 1);
            continue;
          }
          if (total === 0) continue;

          if (existingIndex >= 0) {
            if (entries[existingIndex].status === 'paid') {
              return sendJson(res, 400, { error: 'Paid entries cannot be edited' });
            }
            entries[existingIndex] = {
              ...entries[existingIndex],
              hours,
              status: 'submitted'
            };
          } else {
            entries.push({
              id: randomUUID(),
              employee_id: employeeId,
              start_date: startDate,
              end_date: endDate,
              hours,
              status: 'submitted'
            });
          }
        }

        saveStore({ ...store, time_entries: entries });
        audit('user', 'timesheet.update', { startDate, endDate });
        return sendJson(res, 200, { entries });
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
  }

  if (req.method === 'POST' && url.pathname === '/api/time-entries/approve') {
    return parseBody(req)
      .then((body) => {
        const entryIds = Array.isArray(body.entryIds) ? body.entryIds : [];
        if (!entryIds.length) {
          return sendJson(res, 400, { error: 'Provide entry IDs to approve' });
        }
        const store = readStore();
        const entries = Array.isArray(store.time_entries) ? store.time_entries : [];
        entries.forEach((entry) => {
          if (entryIds.includes(entry.id) && entry.status !== 'paid') {
            entry.status = 'approved';
          }
        });
        saveStore({ ...store, time_entries: entries });
        audit('user', 'timesheet.approve', { count: entryIds.length });
        return sendJson(res, 200, { entries });
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
  }

  if (req.method === 'POST' && url.pathname === '/api/time-entries/pay') {
    return parseBody(req)
      .then((body) => {
        const startDate = (body.start_date || '').trim();
        const endDate = (body.end_date || '').trim();
        if (!startDate || !endDate) {
          return sendJson(res, 400, { error: 'Start and end dates are required' });
        }
        const store = readStore();
        const entries = Array.isArray(store.time_entries) ? store.time_entries : [];
        const payrollRuns = Array.isArray(store.payroll_runs) ? store.payroll_runs : [];
        let updated = 0;
        entries.forEach((entry) => {
          if (entry.start_date === startDate && entry.end_date === endDate && entry.status !== 'paid') {
            entry.status = 'paid';
            entry.paid_at = new Date().toISOString();
            updated += 1;
          }
        });
        let run = payrollRuns.find((item) => item.start_date === startDate && item.end_date === endDate);
        if (!run) {
          run = {
            id: randomUUID(),
            start_date: startDate,
            end_date: endDate,
            created_at: new Date().toISOString(),
            label: '',
            entry_ids: entries.filter((entry) => entry.start_date === startDate && entry.end_date === endDate).map((entry) => entry.id)
          };
          payrollRuns.push(run);
        }
        saveStore({ ...store, time_entries: entries, payroll_runs: payrollRuns });
        audit('user', 'timesheet.paid', { startDate, endDate, updated });
        return sendJson(res, 200, { updated, run });
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
  }

  if (req.method === 'GET' && url.pathname === '/api/pay-stubs/pdf') {
    const entryId = url.searchParams.get('entry_id');
    if (!entryId) {
      return sendJson(res, 400, { error: 'Entry ID is required' });
    }
    const store = readStore();
    const entries = Array.isArray(store.time_entries) ? store.time_entries : [];
    const entry = entries.find((item) => item.id === entryId);
    if (!entry) {
      return sendJson(res, 404, { error: 'Time entry not found' });
    }
    if (entry.status !== 'paid') {
      return sendJson(res, 400, { error: 'Pay stubs are only available for paid entries' });
    }

    return runStubPdfExport({ entryId })
      .then(({ outputPath, tempDir }) => {
        res.writeHead(200, {
          'Content-Type': 'application/pdf',
          'Content-Disposition': `attachment; filename="pay-stub-${entryId}.pdf"`
        });
        const stream = fs.createReadStream(outputPath);
        stream.pipe(res);
        stream.on('close', () => {
          fs.unlink(outputPath, () => {
            fs.rmdir(tempDir, () => undefined);
          });
        });
        return null;
      })
      .catch((error) => {
        console.error('Failed to generate pay stub PDF', error);
        return sendJson(res, 500, { error: 'Unable to generate pay stub PDF' });
      });
  }

  if (req.method === 'POST' && url.pathname === '/api/time-entries/payment-date') {
    return parseBody(req)
      .then((body) => {
        const entryId = (body.entry_id || '').trim();
        const paidAt = (body.paid_at || '').trim();
        if (!entryId) return sendJson(res, 400, { error: 'Entry ID is required' });
        if (!paidAt) return sendJson(res, 400, { error: 'Payment date is required' });
        const parsed = new Date(paidAt);
        if (Number.isNaN(parsed.getTime())) {
          return sendJson(res, 400, { error: 'Payment date is invalid' });
        }
        const store = readStore();
        const entries = Array.isArray(store.time_entries) ? store.time_entries : [];
        const entry = entries.find((item) => item.id === entryId);
        if (!entry) return sendJson(res, 404, { error: 'Time entry not found' });
        if (entry.status !== 'paid') {
          return sendJson(res, 400, { error: 'Only paid entries can update payment dates' });
        }
        entry.paid_at = parsed.toISOString();
        saveStore({ ...store, time_entries: entries });
        audit('user', 'timesheet.payment_date.update', { entryId });
        return sendJson(res, 200, { entry });
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
  }

  if (req.method === 'GET' && url.pathname === '/api/payroll-runs') {
    const store = readStore();
    const payrollRuns = Array.isArray(store.payroll_runs) ? store.payroll_runs : [];
    const entries = Array.isArray(store.time_entries) ? store.time_entries : [];
    const paidPeriods = entries
      .filter((entry) => entry.status === 'paid')
      .reduce((acc, entry) => {
        const key = `${entry.start_date}_${entry.end_date}`;
        if (!acc.has(key)) {
          acc.set(key, { start_date: entry.start_date, end_date: entry.end_date });
        }
        return acc;
      }, new Map());
    paidPeriods.forEach((period) => {
      const exists = payrollRuns.find((run) => run.start_date === period.start_date && run.end_date === period.end_date);
      if (!exists) {
        payrollRuns.push({
          id: randomUUID(),
          start_date: period.start_date,
          end_date: period.end_date,
          created_at: new Date().toISOString(),
          label: '',
          entry_ids: entries
            .filter((entry) => entry.start_date === period.start_date && entry.end_date === period.end_date)
            .map((entry) => entry.id)
        });
      }
    });
    saveStore({ ...store, payroll_runs: payrollRuns });
    return sendJson(res, 200, { runs: payrollRuns });
  }

  if (req.method === 'POST' && url.pathname === '/api/payroll-runs/update') {
    return parseBody(req)
      .then((body) => {
        const runId = (body.run_id || '').trim();
        if (!runId) return sendJson(res, 400, { error: 'Run ID is required' });
        const store = readStore();
        const payrollRuns = Array.isArray(store.payroll_runs) ? store.payroll_runs : [];
        const run = payrollRuns.find((item) => item.id === runId);
        if (!run) return sendJson(res, 404, { error: 'Payroll run not found' });
        run.label = (body.label || '').trim();
        saveStore({ ...store, payroll_runs: payrollRuns });
        audit('user', 'payroll.update', { runId });
        return sendJson(res, 200, { run });
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
  }

  if (req.method === 'POST' && url.pathname === '/api/payroll-runs/delete') {
    return parseBody(req)
      .then((body) => {
        const runId = (body.run_id || '').trim();
        if (!runId) return sendJson(res, 400, { error: 'Run ID is required' });
        const store = readStore();
        const payrollRuns = Array.isArray(store.payroll_runs) ? store.payroll_runs : [];
        const run = payrollRuns.find((item) => item.id === runId);
        if (!run) {
          return sendJson(res, 404, { error: 'Payroll run not found' });
        }
        const nextRuns = payrollRuns.filter((item) => item.id !== runId);
        const entries = Array.isArray(store.time_entries) ? store.time_entries : [];
        let reverted = 0;
        entries.forEach((entry) => {
          if (entry.start_date === run.start_date && entry.end_date === run.end_date && entry.status === 'paid') {
            entry.status = 'approved';
            delete entry.paid_at;
            reverted += 1;
          }
        });
        saveStore({ ...store, payroll_runs: nextRuns, time_entries: entries });
        audit('user', 'payroll.delete', { runId, reverted });
        return sendJson(res, 200, { runs: nextRuns });
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
  }

  if (req.method === 'GET' && url.pathname === '/api/payroll-history') {
    const store = readStore();
    const history = Array.isArray(store.payroll_history) ? store.payroll_history : [];
    const employeeId = url.searchParams.get('employee_id');
    const filtered = employeeId ? history.filter((entry) => entry.employee_id === employeeId) : history;
    return sendJson(res, 200, { entries: filtered });
  }

  if (req.method === 'POST' && url.pathname === '/api/payroll-history') {
    return parseBody(req)
      .then((body) => {
        const employeeId = (body.employee_id || '').trim();
        const entryType = (body.entry_type || '').trim().toLowerCase();
        if (!employeeId) return sendJson(res, 400, { error: 'Employee ID is required' });
        if (!['check', 'quarter'].includes(entryType)) {
          return sendJson(res, 400, { error: 'Entry type must be check or quarter' });
        }

        const hoursPayload = body.hours && typeof body.hours === 'object' ? body.hours : {};
        const payLinesPayload = body.pay_lines && typeof body.pay_lines === 'object' ? body.pay_lines : {};
        const SS_RATE = 0.062;
        const MEDICARE_RATE = 0.0145;
        const FIT_RATE = 0.1;
        const FUTA_RATE = 0.006;
        const SUTA_RATE = 0.027;

        let checkDate = '';
        let periodStart = '';
        let periodEnd = '';
        let year = null;
        let quarter = null;

        if (entryType === 'check') {
          checkDate = (body.check_date || '').trim();
          periodStart = (body.period_start || '').trim();
          periodEnd = (body.period_end || '').trim();
          if (!checkDate) return sendJson(res, 400, { error: 'Check date is required' });
          if (!periodStart || !periodEnd) {
            return sendJson(res, 400, { error: 'Period start and end dates are required' });
          }
          const parsed = new Date(checkDate);
          if (Number.isNaN(parsed.getTime())) {
            return sendJson(res, 400, { error: 'Check date is invalid' });
          }
          checkDate = parsed.toISOString();
          const parsedStart = new Date(periodStart);
          const parsedEnd = new Date(periodEnd);
          if (Number.isNaN(parsedStart.getTime()) || Number.isNaN(parsedEnd.getTime())) {
            return sendJson(res, 400, { error: 'Period dates are invalid' });
          }
          if (parsedStart > parsedEnd) {
            return sendJson(res, 400, { error: 'Period start must be before period end' });
          }
          periodStart = parsedStart.toISOString();
          periodEnd = parsedEnd.toISOString();
        } else {
          year = Number(body.year);
          quarter = Number(body.quarter);
          if (!Number.isFinite(year) || year < 1900) {
            return sendJson(res, 400, { error: 'Year is required for quarterly entries' });
          }
          if (![1, 2, 3, 4].includes(quarter)) {
            return sendJson(res, 400, { error: 'Quarter must be 1, 2, 3, or 4' });
          }
        }

        const store = readStore();
        const employees = Array.isArray(store.employees) ? store.employees : [];
        const employee = employees.find((item) => item.id === employeeId);
        if (!employee) return sendJson(res, 404, { error: 'Employee not found' });

        const history = Array.isArray(store.payroll_history) ? store.payroll_history : [];
        const payTypes = getPayTypes(store);
        const hours = {};
        const payLines = {};
        let gross = 0;
        for (const type of payTypes) {
          const value = Number(hoursPayload[type.id] ?? payLinesPayload[type.id]?.hours ?? 0);
          const rate = Number(payLinesPayload[type.id]?.rate ?? 0);
          if (!Number.isFinite(value) || value < 0) {
            return sendJson(res, 400, { error: `Hours for ${type.name} must be a valid number` });
          }
          if (!Number.isFinite(rate) || rate < 0) {
            return sendJson(res, 400, { error: `Rate for ${type.name} must be a valid number` });
          }
          const roundedHours = Math.round(value * 100) / 100;
          const roundedRate = Math.round(rate * 100) / 100;
          const amount = Math.round(roundedHours * roundedRate * 100) / 100;
          hours[type.id] = roundedHours;
          payLines[type.id] = { hours: roundedHours, rate: roundedRate, amount };
          gross += amount;
        }
        gross = Math.round(gross * 100) / 100;
        const fit = Math.round(gross * FIT_RATE * 100) / 100;
        const employeeSS = Math.round(gross * SS_RATE * 100) / 100;
        const employeeMedicare = Math.round(gross * MEDICARE_RATE * 100) / 100;
        const employeeTaxes = Math.round((fit + employeeSS + employeeMedicare) * 100) / 100;
        const net = Math.round((gross - employeeTaxes) * 100) / 100;
        const employerSS = Math.round(gross * SS_RATE * 100) / 100;
        const employerMedicare = Math.round(gross * MEDICARE_RATE * 100) / 100;
        const futa = Math.round(gross * FUTA_RATE * 100) / 100;
        const suta = Math.round(gross * SUTA_RATE * 100) / 100;
        const employerTaxes = Math.round((employerSS + employerMedicare + futa + suta) * 100) / 100;
        const entry = {
          id: randomUUID(),
          employee_id: employeeId,
          entry_type: entryType,
          gross,
          net,
          taxes: employeeTaxes,
          hours,
          pay_lines: payLines,
          fit,
          employee_ss: employeeSS,
          employee_medicare: employeeMedicare,
          employer_ss: employerSS,
          employer_medicare: employerMedicare,
          futa,
          suta,
          employer_taxes: employerTaxes,
          notes: (body.notes || '').trim(),
          created_at: new Date().toISOString()
        };

        if (entryType === 'check') {
          entry.check_date = checkDate;
          entry.period_start = periodStart;
          entry.period_end = periodEnd;
        } else {
          entry.year = year;
          entry.quarter = quarter;
        }

        history.unshift(entry);
        saveStore({ ...store, payroll_history: history });
        audit('user', 'payroll.history.create', { employeeId, entryType });
        return sendJson(res, 200, { entry });
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
  }

  if (req.method === 'GET' && url.pathname === '/api/pto') {
    const employees = loadEmployees().map((employee) => ({
      id: employee.id,
      name: employee.name,
      department: employee.department || '',
      pay_schedule: employee.pay_schedule || '',
      pto_balance_hours: Number(employee.pto_balance_hours || 0)
    }));
    return sendJson(res, 200, { employees });
  }

  if (req.method === 'POST' && url.pathname === '/api/pto') {
    return parseBody(req)
      .then((body) => {
        const adjustments = Array.isArray(body.adjustments) ? body.adjustments : [];
        if (!adjustments.length) {
          return sendJson(res, 400, { error: 'Provide at least one PTO adjustment' });
        }

        const store = readStore();
        const employees = Array.isArray(store.employees) ? store.employees : [];

        for (const adjustment of adjustments) {
          const employeeId = (adjustment.employeeId || '').trim();
          const amount = Number(adjustment.amount);
          const reason = (adjustment.reason || '').trim();

          if (!employeeId) {
            return sendJson(res, 400, { error: 'Employee ID is required for PTO adjustments' });
          }

          if (!Number.isFinite(amount)) {
            return sendJson(res, 400, { error: 'Adjustment amount must be a valid number of hours' });
          }

          const employee = employees.find((item) => item.id === employeeId);
          if (!employee) {
            return sendJson(res, 404, { error: `Employee not found: ${employeeId}` });
          }

          const current = Number(employee.pto_balance_hours || 0);
          const updated = Math.max(0, current + amount);

          employee.pto_balance_hours = Math.round(updated * 100) / 100;
          audit('user', 'pto.adjust', { employeeId, amount, reason });
        }

        saveStore({ ...store, employees });
        const refreshed = loadEmployees().map((employee) => ({
          id: employee.id,
          name: employee.name,
          department: employee.department || '',
          pay_schedule: employee.pay_schedule || '',
          pto_balance_hours: Number(employee.pto_balance_hours || 0)
        }));

        return sendJson(res, 200, { employees: refreshed });
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
  }

  if (req.method === 'GET' && url.pathname === '/api/pay-schedules') {
    const paySchedules = loadPaySchedules();
    return sendJson(res, 200, { paySchedules });
  }

  if (req.method === 'POST' && url.pathname === '/api/pay-schedules') {
    return parseBody(req)
      .then((body) => {
        const payload = Array.isArray(body.paySchedules) ? body.paySchedules : [];
        if (!payload.length) {
          return sendJson(res, 400, { error: 'Add at least one pay schedule' });
        }

        const normalized = payload.map((schedule) => ({
          ...schedule,
          name: (schedule.name || '').trim(),
          cadence: (schedule.cadence || '').toLowerCase(),
          firstPayDate: schedule.firstPayDate || schedule.first_pay_date || '',
          timezone: schedule.timezone || ''
        }));

        for (const schedule of normalized) {
          if (!schedule.name) return sendJson(res, 400, { error: 'Schedule name is required' });
          if (!PAY_CADENCE_OPTIONS.includes(schedule.cadence)) {
            return sendJson(res, 400, { error: 'Cadence must be weekly, biweekly, semimonthly, or monthly' });
          }
        }

        const lowerNames = normalized.map((schedule) => schedule.name.toLowerCase());
        const hasDuplicate = lowerNames.some((name, idx) => lowerNames.indexOf(name) !== idx);
        if (hasDuplicate) {
          return sendJson(res, 400, { error: 'Schedule names must be unique' });
        }

        const setup = loadSetup();
        const saved = saveSetup({ ...setup, paySchedules: normalized });
        audit('user', 'paySchedules.update', { count: normalized.length });
        return sendJson(res, 200, { paySchedules: saved.paySchedules });
      })
      .catch(() => sendJson(res, 400, { error: 'Invalid JSON payload' }));
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

const steps = ['company', 'addresses', 'tax', 'paySchedules'];
let currentStepIndex = 0;
let metadata = { states: [], cadenceOptions: [], filingFrequencies: [], einPattern: '' };
let wizardState = {
  company: {
    legalName: '',
    ein: '',
    contact: { name: '', email: '', phone: '' }
  },
  addresses: [],
  taxAccounts: [],
  paySchedules: [],
  completed: false
};

const messagesEl = document.getElementById('messages');
const badgeEl = document.getElementById('status-badge');
const statusCopyEl = document.getElementById('status-copy');
const adminTokenEl = document.getElementById('adminToken');

function setBadge(status, copy) {
  badgeEl.textContent = status;
  statusCopyEl.textContent = copy || '';
}

function showMessage(type, text) {
  const div = document.createElement('div');
  div.className = type === 'error' ? 'notice' : type === 'success' ? 'success' : 'notice';
  div.textContent = text;
  messagesEl.innerHTML = '';
  messagesEl.appendChild(div);
  setTimeout(() => {
    if (messagesEl.contains(div)) messagesEl.removeChild(div);
  }, 5000);
}

function persistLocalDraft() {
  const draft = { wizardState, currentStepIndex, savedAt: new Date().toISOString() };
  localStorage.setItem('wizardDraft', JSON.stringify(draft));
}

async function persistServerDraft(partial) {
  const token = getAdminToken();
  if (!token) {
    showMessage('notice', 'Draft saved locally. Add an admin token to sync to the server.');
    return;
  }
  try {
    await fetch('/api/admin/progress', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Token': token
      },
      body: JSON.stringify(partial)
    });
    showMessage('success', 'Draft synced to server');
  } catch (error) {
    showMessage('error', 'Unable to save draft to server');
  }
}

function getAdminToken() {
  return adminTokenEl.value || localStorage.getItem('adminToken') || '';
}

function updateStepper() {
  document.querySelectorAll('.wizard-step').forEach((section, idx) => {
    section.hidden = idx !== currentStepIndex;
  });
  document.querySelectorAll('.step').forEach((el, idx) => {
    el.classList.toggle('active', idx === currentStepIndex);
  });
  document.getElementById('backBtn').disabled = currentStepIndex === 0;
  document.getElementById('nextBtn').textContent = currentStepIndex === steps.length - 1 ? 'Submit' : 'Next';
}

function setField(id, value) {
  const el = document.getElementById(id);
  if (el) el.value = value || '';
}

function hydrateForm() {
  const company = wizardState.company || {};
  setField('legalName', company.legalName);
  setField('ein', company.ein);
  setField('contactName', company.contact?.name);
  setField('contactEmail', company.contact?.email);
  setField('contactPhone', company.contact?.phone);

  renderAddresses();
  renderTaxAccounts();
  renderSchedules();
  updateStepper();
}

function renderAddresses() {
  const wrapper = document.getElementById('addressList');
  wrapper.innerHTML = '';
  wizardState.addresses.forEach((address, idx) => {
    const div = document.createElement('div');
    div.className = 'list-card';
    div.dataset.index = idx;
    div.innerHTML = `
      <div class="flex" style="justify-content: space-between; align-items: center;">
        <strong>Address ${idx + 1}</strong>
        <button type="button" class="secondary" data-remove-address="${idx}">Remove</button>
      </div>
      <div class="form-grid" data-kind="address" data-index="${idx}">
        <div>
          <label>Type</label>
          <select name="type">
            <option value="legal">Legal</option>
            <option value="mailing">Mailing</option>
            <option value="worksite">Worksite</option>
          </select>
        </div>
        <div>
          <label>Line 1</label>
          <input name="line1" />
          <div class="error" data-error="address-${idx}-line1"></div>
        </div>
        <div>
          <label>Line 2</label>
          <input name="line2" />
        </div>
        <div>
          <label>City</label>
          <input name="city" />
          <div class="error" data-error="address-${idx}-city"></div>
        </div>
        <div>
          <label>State</label>
          <select name="state"></select>
          <div class="error" data-error="address-${idx}-state"></div>
        </div>
        <div>
          <label>Postal code</label>
          <input name="postalCode" />
          <div class="error" data-error="address-${idx}-postalCode"></div>
        </div>
      </div>
    `;
    wrapper.appendChild(div);

    const grid = div.querySelector('[data-kind="address"]');
    const selectState = grid.querySelector('select[name="state"]');
    selectState.innerHTML = metadata.states.map((s) => `<option value="${s}">${s}</option>`).join('');

    Object.entries(address || {}).forEach(([key, value]) => {
      const field = grid.querySelector(`[name="${key}"]`);
      if (field) field.value = value;
    });
  });
}

function renderTaxAccounts() {
  const wrapper = document.getElementById('taxList');
  wrapper.innerHTML = '';
  wizardState.taxAccounts.forEach((account, idx) => {
    const div = document.createElement('div');
    div.className = 'list-card';
    div.innerHTML = `
      <div class="flex" style="justify-content: space-between; align-items: center;">
        <strong>Tax account ${idx + 1}</strong>
        <button type="button" class="secondary" data-remove-tax="${idx}">Remove</button>
      </div>
      <div class="form-grid" data-kind="tax" data-index="${idx}">
        <div>
          <label>Jurisdiction</label>
          <select name="jurisdiction"></select>
          <div class="error" data-error="tax-${idx}-jurisdiction"></div>
        </div>
        <div>
          <label>Account number</label>
          <input name="accountNumber" />
          <div class="error" data-error="tax-${idx}-accountNumber"></div>
        </div>
        <div>
          <label>Filing frequency</label>
          <select name="filingFrequency"></select>
          <div class="error" data-error="tax-${idx}-filingFrequency"></div>
        </div>
      </div>
    `;
    wrapper.appendChild(div);

    const grid = div.querySelector('[data-kind="tax"]');
    grid.querySelector('select[name="jurisdiction"]').innerHTML = metadata.states
      .map((s) => `<option value="${s}">${s}</option>`)
      .join('');
    grid.querySelector('select[name="filingFrequency"]').innerHTML = metadata.filingFrequencies
      .map((s) => `<option value="${s}">${s}</option>`)
      .join('');

    Object.entries(account || {}).forEach(([key, value]) => {
      const field = grid.querySelector(`[name="${key}"]`);
      if (field) field.value = value;
    });
  });
}

function renderSchedules() {
  const wrapper = document.getElementById('scheduleList');
  wrapper.innerHTML = '';
  wizardState.paySchedules.forEach((schedule, idx) => {
    const div = document.createElement('div');
    div.className = 'list-card';
    div.innerHTML = `
      <div class="flex" style="justify-content: space-between; align-items: center;">
        <strong>Schedule ${idx + 1}</strong>
        <button type="button" class="secondary" data-remove-schedule="${idx}">Remove</button>
      </div>
      <div class="form-grid" data-kind="schedule" data-index="${idx}">
        <div>
          <label>Name</label>
          <input name="name" />
          <div class="error" data-error="schedule-${idx}-name"></div>
        </div>
        <div>
          <label>Cadence</label>
          <select name="cadence"></select>
          <div class="error" data-error="schedule-${idx}-cadence"></div>
        </div>
        <div>
          <label>First pay date</label>
          <input type="date" name="firstPayDate" />
          <div class="error" data-error="schedule-${idx}-firstPayDate"></div>
        </div>
        <div>
          <label>Timezone</label>
          <input name="timezone" placeholder="e.g. America/New_York" />
          <div class="error" data-error="schedule-${idx}-timezone"></div>
        </div>
      </div>
    `;
    wrapper.appendChild(div);

    const grid = div.querySelector('[data-kind="schedule"]');
    grid.querySelector('select[name="cadence"]').innerHTML = metadata.cadenceOptions
      .map((s) => `<option value="${s}">${s}</option>`)
      .join('');

    Object.entries(schedule || {}).forEach(([key, value]) => {
      const field = grid.querySelector(`[name="${key}"]`);
      if (field) field.value = value;
    });
  });
}

function setErrors(errors) {
  document.querySelectorAll('.error').forEach((el) => (el.textContent = ''));
  Object.entries(errors || {}).forEach(([key, value]) => {
    const el = document.querySelector(`[data-error="${key}"]`);
    if (el) el.textContent = value;
  });
}

function collectCompany() {
  return {
    legalName: document.getElementById('legalName').value.trim(),
    ein: document.getElementById('ein').value.trim(),
    contact: {
      name: document.getElementById('contactName').value.trim(),
      email: document.getElementById('contactEmail').value.trim(),
      phone: document.getElementById('contactPhone').value.trim()
    }
  };
}

function collectAddresses() {
  return Array.from(document.querySelectorAll('[data-kind="address"]')).map((container) => {
    const data = {};
    container.querySelectorAll('input, select').forEach((input) => {
      data[input.name] = input.value.trim();
    });
    return data;
  });
}

function collectTaxAccounts() {
  return Array.from(document.querySelectorAll('[data-kind="tax"]')).map((container) => {
    const data = {};
    container.querySelectorAll('input, select').forEach((input) => {
      data[input.name] = input.value.trim();
    });
    return data;
  });
}

function collectSchedules() {
  return Array.from(document.querySelectorAll('[data-kind="schedule"]')).map((container) => {
    const data = {};
    container.querySelectorAll('input, select').forEach((input) => {
      data[input.name] = input.value.trim();
    });
    return data;
  });
}

function validateCompany(company) {
  const errors = {};
  if (!company.legalName) errors.legalName = 'Legal name is required';
  if (!/^\d{2}-\d{7}$/.test(company.ein)) errors.ein = 'EIN must match NN-NNNNNNN';
  if (!company.contact.name) errors.contactName = 'Contact name is required';
  if (!company.contact.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(company.contact.email)) {
    errors.contactEmail = 'Enter a valid email';
  }
  if (!company.contact.phone || company.contact.phone.replace(/\D/g, '').length < 10) {
    errors.contactPhone = 'Enter a 10 digit phone number';
  }
  return errors;
}

function validateAddresses(addresses) {
  const errors = {};
  addresses.forEach((address, idx) => {
    if (!address.line1) errors[`address-${idx}-line1`] = 'Line 1 is required';
    if (!address.city) errors[`address-${idx}-city`] = 'City is required';
    if (!metadata.states.includes(address.state)) errors[`address-${idx}-state`] = 'Select a state';
    if (!/^\d{5}(-\d{4})?$/.test(address.postalCode || '')) {
      errors[`address-${idx}-postalCode`] = 'ZIP must be 5 or 9 digits';
    }
  });
  if (!addresses.length) {
    errors.addresses = 'Add at least one address';
  }
  return errors;
}

function validateTaxAccounts(accounts) {
  const errors = {};
  accounts.forEach((account, idx) => {
    if (!metadata.states.includes(account.jurisdiction)) errors[`tax-${idx}-jurisdiction`] = 'Pick a jurisdiction';
    if (!account.accountNumber || account.accountNumber.length < 3) errors[`tax-${idx}-accountNumber`] = 'Account number required';
    if (!metadata.filingFrequencies.includes(account.filingFrequency)) errors[`tax-${idx}-filingFrequency`] = 'Select frequency';
  });
  if (!accounts.length) errors.taxAccounts = 'Add at least one tax account';
  return errors;
}

function validateSchedules(schedules) {
  const errors = {};
  schedules.forEach((schedule, idx) => {
    if (!schedule.name) errors[`schedule-${idx}-name`] = 'Name required';
    if (!metadata.cadenceOptions.includes(schedule.cadence)) errors[`schedule-${idx}-cadence`] = 'Select cadence';
    if (!schedule.firstPayDate || Number.isNaN(Date.parse(schedule.firstPayDate))) {
      errors[`schedule-${idx}-firstPayDate`] = 'Valid date required';
    }
    if (!schedule.timezone) errors[`schedule-${idx}-timezone`] = 'Timezone required';
  });
  if (!schedules.length) errors.paySchedules = 'Add at least one pay schedule';
  return errors;
}

function validateStep(step) {
  let errors = {};
  if (step === 'company') {
    errors = validateCompany(collectCompany());
  } else if (step === 'addresses') {
    errors = validateAddresses(collectAddresses());
  } else if (step === 'tax') {
    errors = validateTaxAccounts(collectTaxAccounts());
  } else if (step === 'paySchedules') {
    errors = validateSchedules(collectSchedules());
  }
  setErrors(errors);
  return Object.keys(errors).length === 0;
}

function updateStateFromForm() {
  wizardState.company = collectCompany();
  wizardState.addresses = collectAddresses();
  wizardState.taxAccounts = collectTaxAccounts();
  wizardState.paySchedules = collectSchedules();
}

async function submitSetup() {
  updateStateFromForm();
  const token = getAdminToken();
  if (!token) {
    showMessage('error', 'Admin token required to submit setup');
    return;
  }
  persistLocalDraft();
  try {
    const res = await fetch('/api/admin/setup', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Token': token
      },
      body: JSON.stringify({ ...wizardState, completed: true, currentStep: 'complete' })
    });
    if (!res.ok) {
      const body = await res.json();
      throw new Error(body.error || 'Unable to save');
    }
    const data = await res.json();
    wizardState = data;
    currentStepIndex = steps.length - 1;
    setBadge('Setup complete', 'Payroll functions are unlocked.');
    showMessage('success', 'Company setup saved');
    updateStepper();
    persistLocalDraft();
  } catch (error) {
    showMessage('error', error.message);
  }
}

async function saveDraftFlow() {
  updateStateFromForm();
  persistLocalDraft();
  await persistServerDraft({
    ...wizardState,
    completed: false,
    currentStep: steps[currentStepIndex]
  });
}

function goNext() {
  const step = steps[currentStepIndex];
  if (!validateStep(step)) return;
  updateStateFromForm();
  if (currentStepIndex === steps.length - 1) {
    submitSetup();
  } else {
    currentStepIndex += 1;
    wizardState.currentStep = steps[currentStepIndex];
    updateStepper();
  }
  persistLocalDraft();
}

function goBack() {
  if (currentStepIndex === 0) return;
  currentStepIndex -= 1;
  wizardState.currentStep = steps[currentStepIndex];
  updateStepper();
}

function attachEvents() {
  document.getElementById('nextBtn').addEventListener('click', goNext);
  document.getElementById('backBtn').addEventListener('click', goBack);
  document.getElementById('saveDraft').addEventListener('click', saveDraftFlow);
  document.getElementById('addAddress').addEventListener('click', () => {
    wizardState.addresses.push({ type: 'legal', line1: '', line2: '', city: '', state: metadata.states[0], postalCode: '' });
    renderAddresses();
  });
  document.getElementById('addTax').addEventListener('click', () => {
    wizardState.taxAccounts.push({ jurisdiction: metadata.states[0], accountNumber: '', filingFrequency: metadata.filingFrequencies[0] });
    renderTaxAccounts();
  });
  document.getElementById('addSchedule').addEventListener('click', () => {
    wizardState.paySchedules.push({ name: '', cadence: metadata.cadenceOptions[0], firstPayDate: '', timezone: 'America/New_York' });
    renderSchedules();
  });

  document.getElementById('addressList').addEventListener('click', (e) => {
    const index = e.target.getAttribute('data-remove-address');
    if (index !== null) {
      wizardState.addresses.splice(Number(index), 1);
      renderAddresses();
    }
  });
  document.getElementById('taxList').addEventListener('click', (e) => {
    const index = e.target.getAttribute('data-remove-tax');
    if (index !== null) {
      wizardState.taxAccounts.splice(Number(index), 1);
      renderTaxAccounts();
    }
  });
  document.getElementById('scheduleList').addEventListener('click', (e) => {
    const index = e.target.getAttribute('data-remove-schedule');
    if (index !== null) {
      wizardState.paySchedules.splice(Number(index), 1);
      renderSchedules();
    }
  });

  adminTokenEl.addEventListener('input', (e) => {
    localStorage.setItem('adminToken', e.target.value);
  });
}

async function hydrateFromServer() {
  try {
    const [metaRes, setupRes] = await Promise.all([
      fetch('/api/metadata'),
      fetch('/api/setup')
    ]);
    metadata = await metaRes.json();
    const { setup, payrollEnabled } = await setupRes.json();
    wizardState = {
      ...wizardState,
      ...setup,
      company: setup.company || wizardState.company,
      addresses: setup.addresses || [],
      taxAccounts: setup.taxAccounts || [],
      paySchedules: setup.paySchedules || [],
      completed: setup.completed || false
    };
    currentStepIndex = Math.max(0, steps.indexOf(setup.currentStep || 'company'));
    hydrateForm();
    setBadge(
      payrollEnabled ? 'Setup complete' : 'Setup required',
      payrollEnabled
        ? 'Payroll actions are enabled.'
        : 'Finish all steps before running payroll. Progress is saved automatically.'
    );
  } catch (error) {
    setBadge('Offline mode', 'Unable to reach the server');
  }
}

function hydrateFromLocalDraft() {
  const draft = localStorage.getItem('wizardDraft');
  if (!draft) return;
  try {
    const parsed = JSON.parse(draft);
    wizardState = { ...wizardState, ...parsed.wizardState };
    currentStepIndex = parsed.currentStepIndex || 0;
  } catch (error) {
    console.warn('Unable to read draft');
  }
}

async function init() {
  const savedToken = localStorage.getItem('adminToken');
  if (savedToken) adminTokenEl.value = savedToken;
  hydrateFromLocalDraft();
  attachEvents();
  await hydrateFromServer();
  persistLocalDraft();
}

init();

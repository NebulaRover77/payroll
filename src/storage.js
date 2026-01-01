const fs = require('fs');
const path = require('path');

const setupPath = path.join(__dirname, '..', 'data', 'setup.json');
const auditPath = path.join(__dirname, '..', 'data', 'audit-log.json');

const defaultSetup = {
  company: null,
  addresses: [],
  taxAccounts: [],
  paySchedules: [],
  completed: false,
  currentStep: 'company'
};

function ensureFiles() {
  if (!fs.existsSync(setupPath)) {
    writeJson(setupPath, defaultSetup);
  }
  if (!fs.existsSync(auditPath)) {
    writeJson(auditPath, []);
  }
}

function writeJson(filePath, data) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
}

function readJson(filePath) {
  try {
    const raw = fs.readFileSync(filePath, 'utf-8');
    return JSON.parse(raw);
  } catch (error) {
    return null;
  }
}

function loadSetup() {
  ensureFiles();
  return readJson(setupPath) || { ...defaultSetup };
}

function saveSetup(payload) {
  ensureFiles();
  const current = loadSetup();
  const merged = { ...current, ...payload, updatedAt: new Date().toISOString() };
  writeJson(setupPath, merged);
  return merged;
}

function resetSetup() {
  writeJson(setupPath, defaultSetup);
}

function appendAuditEvent(event) {
  ensureFiles();
  const events = readJson(auditPath) || [];
  events.push(event);
  writeJson(auditPath, events);
  return event;
}

function loadAuditLog() {
  ensureFiles();
  return readJson(auditPath) || [];
}

module.exports = {
  loadSetup,
  saveSetup,
  resetSetup,
  appendAuditEvent,
  loadAuditLog,
  defaultSetup
};

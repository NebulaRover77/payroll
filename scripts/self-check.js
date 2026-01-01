const { validateSetup } = require('../src/validators');
const { saveSetup, loadSetup } = require('../src/storage');

const sample = {
  company: {
    legalName: 'Acme Payroll Co',
    ein: '12-3456789',
    contact: { name: 'Ada Admin', email: 'ada@example.com', phone: '+1 555 123 1234' }
  },
  addresses: [
    {
      type: 'legal',
      line1: '123 Main St',
      line2: '',
      city: 'Springfield',
      state: 'CA',
      postalCode: '94105',
      country: 'US'
    }
  ],
  taxAccounts: [
    { jurisdiction: 'CA', accountNumber: '12345', filingFrequency: 'monthly' }
  ],
  paySchedules: [
    { name: 'Biweekly', cadence: 'biweekly', firstPayDate: '2024-10-15', timezone: 'America/Los_Angeles' }
  ],
  completed: false,
  currentStep: 'company'
};

function main() {
  const result = validateSetup(sample);
  if (!result.valid) {
    throw new Error(`Validation failed: ${JSON.stringify(result.errors, null, 2)}`);
  }
  saveSetup(sample);
  const read = loadSetup();
  if (!read.company || read.company.legalName !== sample.company.legalName) {
    throw new Error('Setup file not saved correctly');
  }
  console.log('Validation and storage healthy');
}

main();

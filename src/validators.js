const STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC'
];

const EIN_REGEX = /^\d{2}-\d{7}$/;
const ZIP_REGEX = /^\d{5}(-\d{4})?$/;

function validateCompany(company = {}) {
  const errors = {};
  if (!company.legalName) errors.legalName = 'Legal name is required';
  if (!company.ein || !EIN_REGEX.test(company.ein)) errors.ein = 'EIN must match NN-NNNNNNN';
  const contact = company.contact || {};
  if (contact.name && contact.name.trim().length === 0) {
    errors.contactName = 'Contact name cannot be blank';
  }
  if (contact.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact.email)) {
    errors.contactEmail = 'Provide a valid contact email';
  }
  if (contact.phone && contact.phone.replace(/\D/g, '').length < 10) {
    errors.contactPhone = 'Provide a phone number with 10 digits';
  }
  return errors;
}

function validateAddresses(addresses = []) {
  const errors = {};
  addresses.forEach((address, idx) => {
    if (!address.line1) errors[`address-${idx}-line1`] = 'Address line 1 is required';
    if (!address.city) errors[`address-${idx}-city`] = 'City is required';
    if (!address.state || !STATES.includes(address.state)) errors[`address-${idx}-state`] = 'Select a state';
    if (!address.postalCode || !ZIP_REGEX.test(address.postalCode)) {
      errors[`address-${idx}-postalCode`] = 'Postal code must be 5 or 9 digits';
    }
  });
  if (!addresses.length) errors.addresses = 'Add at least one address';
  return errors;
}

function validateTaxAccounts(accounts = []) {
  const errors = {};
  accounts.forEach((account, idx) => {
    if (!account.jurisdiction || !STATES.includes(account.jurisdiction)) {
      errors[`tax-${idx}-jurisdiction`] = 'Jurisdiction is required';
    }
    if (!account.accountNumber || account.accountNumber.length < 3) {
      errors[`tax-${idx}-accountNumber`] = 'Account number must be at least 3 characters';
    }
    if (!['monthly', 'quarterly', 'annual'].includes(account.filingFrequency)) {
      errors[`tax-${idx}-filingFrequency`] = 'Filing frequency is required';
    }
  });
  if (!accounts.length) errors.taxAccounts = 'Add at least one tax account';
  return errors;
}

function validateSchedules(schedules = []) {
  const errors = {};
  schedules.forEach((schedule, idx) => {
    if (!schedule.name) errors[`schedule-${idx}-name`] = 'Schedule name is required';
    if (!['weekly', 'biweekly', 'semimonthly', 'monthly'].includes(schedule.cadence)) {
      errors[`schedule-${idx}-cadence`] = 'Cadence is required';
    }
    if (!schedule.firstPayDate || Number.isNaN(Date.parse(schedule.firstPayDate))) {
      errors[`schedule-${idx}-firstPayDate`] = 'First pay date is required';
    }
    if (!schedule.timezone) errors[`schedule-${idx}-timezone`] = 'Timezone is required';
  });
  if (!schedules.length) errors.paySchedules = 'Add at least one pay schedule';
  return errors;
}

function validateSetup(payload = {}) {
  const errors = {
    ...validateCompany(payload.company),
    ...validateAddresses(payload.addresses),
    ...validateTaxAccounts(payload.taxAccounts),
    ...validateSchedules(payload.paySchedules)
  };
  return {
    valid: Object.keys(errors).length === 0,
    errors
  };
}

function validatePartialSetup(payload = {}) {
  const errors = {};
  if (payload.company) Object.assign(errors, validateCompany(payload.company));
  if (payload.addresses) Object.assign(errors, validateAddresses(payload.addresses));
  if (payload.taxAccounts) Object.assign(errors, validateTaxAccounts(payload.taxAccounts));
  if (payload.paySchedules) Object.assign(errors, validateSchedules(payload.paySchedules));
  return {
    valid: Object.keys(errors).length === 0,
    errors
  };
}

module.exports = {
  STATES,
  EIN_REGEX,
  validateCompany,
  validateAddresses,
  validateTaxAccounts,
  validateSchedules,
  validateSetup,
  validatePartialSetup
};

# Security Architecture and Control Plan

This document outlines the target architecture for integrating strong authentication, MFA, RBAC, encryption, secrets management, audit logging, and session controls for the payroll platform. It is written to guide engineering toward SOC 2 Type II-aligned implementation.

## Authentication and MFA
- **Identity provider**: Use OIDC/SAML with an external IdP (e.g., Okta, Azure AD) to centralize identity, enforce SSO, and manage lifecycle. Local auth can be supported as a fallback only if it meets the password policy below.
- **MFA options**: Support multiple factors and allow per-role policies:
  - **TOTP**: RFC 6238 apps (e.g., Authy, Google Authenticator). Store shared secret encrypted at rest; display recovery codes once on enrollment.
  - **SMS**: Deliver via trusted SMS provider with rate limiting and country restrictions; treat as lower assurance and pair with device binding for higher-risk actions.
  - **WebAuthn**: Prefer platform authenticators with resident keys; attest trusted devices; support user verification for phishing resistance.
- **Adaptive enforcement**: Require MFA on high-risk actions (approvals, payment release, PII exports) and on new devices/locations.
- **Account recovery**: Require admin-assisted recovery plus recent activity verification; log all recovery events.

## Role-Based Access Control (RBAC)
- **Roles**: `admin`, `payroll_manager`, `approver`, `employee`.
- **Model**: Attribute- and permission-based RBAC with least privilege; permissions should be composable per endpoint/service method.
- **Scopes and examples**:
  - `admin`: identity lifecycle, role assignment, config/secrets management, audit access.
  - `payroll_manager`: payroll runs, adjustments, PII read/write, payment initiation, export.
  - `approver`: approve payroll batches, payments, and adjustments; view summaries but not full PII by default.
  - `employee`: view own payslips, tax docs, time data.
- **Implementation notes**: Enforce authorization server-side and in background jobs; include role claims in tokens but revalidate against server-side policy on each critical operation.

## Encryption and Secrets
- **Data at rest**: Use disk encryption (cloud-managed) plus application-level encryption for PII columns (SSN, bank info, home address, tax IDs). Use envelope encryption with KMS-managed DEKs (rotate quarterly) and store key metadata alongside ciphertext.
- **Data in transit**: Enforce TLS 1.2+ everywhere; HSTS and secure cookies; disable plaintext ports; pin certificates for internal service calls where feasible.
- **Secrets management**: Store secrets in an external manager (e.g., AWS Secrets Manager/Parameter Store, GCP Secret Manager, Vault). Inject via environment variables at runtime; never commit secrets. Provide short TTL tokens where possible and rotation runbooks.

## Audit Logging
- **Coverage**: Log `who/when/what` for all CRUD on employees/payroll, approvals, calculations, payment initiations, exports/downloads, authentication events (login/MFA/recovery), and admin actions.
- **Content**: Include actor ID, role, device fingerprint, IP/location, request ID, correlation ID, target record IDs, before/after hashes for sensitive fields (avoid storing full PII in logs), and outcome (success/failure).
- **Integrity**: Write to append-only sink (e.g., cloud logging with bucket retention lock or WORM storage). Include tamper-evident hashing or signing of batches and clock synchronization.
- **Access**: Restrict viewing to admins via dedicated tooling; include alerting on anomalous patterns.

## Session Management and Password Policy
- **Sessions**: Short-lived access tokens (5–15 min) with refresh tokens bound to device and IP; rotate tokens on privilege changes. Implement server-side session store for revocation. Idle timeout (15–30 min) and absolute lifetime (8–12 hours).
- **Device/session revocation**: Admin UI and self-service to list and revoke active sessions/devices; propagate revocations to caches and invalidate refresh tokens immediately.
- **Password policy**: Minimum 14 characters, block breached/weak passwords, enforce lockout with exponential backoff, disallow reuse of last 12, and require periodic rotation only when risk detected. Always store with modern KDF (Argon2id preferred, scrypt acceptable) and pepper stored in KMS.

## Monitoring and Controls (SOC 2 Type II Alignment)
- Map controls to change management, logical access, and system operations: code reviews for auth logic changes, IaC for policies, automated CI checks for secrets/PII, and quarterly access recertification.
- Configure SIEM ingestion for audit logs, MFA anomalies, and failed login/approval attempts; define runbooks and on-call alerts.
- Perform regular tabletop exercises for incident response and recovery of credentials/secrets.
- Document data flows and keep a RACI matrix for approvals and releases.

## Implementation Checklist
- [ ] Integrate IdP with OIDC/SAML, including MFA factor enrollment flows and device binding.
- [ ] Implement RBAC middleware/policies and attach to every endpoint and background job.
- [ ] Encrypt PII columns with envelope encryption and rotate data keys.
- [ ] Enforce TLS-only ingress and secure service-to-service calls; enable HSTS.
- [ ] Move all secrets to an external manager and load via environment on startup.
- [ ] Add structured audit logging with immutable storage and alerts for anomalies.
- [ ] Build session store with revocation and short-lived tokens; add device listing UI/API.
- [ ] Enforce password policy with breach checks and strong KDF; add recovery protections.
- [ ] Map and evidence each control for SOC 2 (monitoring, access reviews, incident response).

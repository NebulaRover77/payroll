# Payroll Run Domain Design

## Entity Overview
- **PayrollRun**
  - **Statuses:** `draft`, `reviewed`, `approved`, `paid` (with `voided` and `reissued` flags for history).
  - **Associations:**
    - Links to **PaySchedule** and specific **PayPeriod** window.
    - Many-to-many relation to **Employee** records via **PayrollRunEmployee** bridge containing per-employee state.
    - Aggregates **TimeEntry** references (only approved entries within the period) and **ManualAdjustment** rows (bonuses, deductions, overrides).
  - **Financial Snapshots:** Immutable calculation snapshots per run and per rerun, storing earnings, deductions, taxes, employer contributions, and net pay per employee.
  - **Audit Trail:** Append-only events (creation, imports, approvals, payments, voids, reissues) with actor, timestamp, and payload checksum.

## Workflow (Wizard)
1. **Select schedule & period**: choose PaySchedule + PayPeriod; prefill defaults (pay groups, earning codes, tax profiles).
2. **Pull approved time & defaults**: import approved TimeEntry records and default earnings/benefits; lock source identifiers for traceability.
3. **Enter adjustments**: add bonuses, deductions, corrections via ManualAdjustment rows with typed reason codes and effective dates.
4. **Calculate**: run payroll engine to produce immutable snapshots per employee and overall summary; flag validation issues.
5. **Review**: reviewers validate totals, discrepancies, warnings; generate audit event on sign-off.
6. **Approval**: requires admin + designated approver sign-offs; upon completion, transition to `approved` and prepare payment batches.

## Reruns, Voids, Reissues
- **Rerun**: new PayrollRun version linked to prior run; clones inputs (time entries, adjustments, defaults) and recalculates; preserves original snapshots.
- **Void**: mark run as voided with reason; lock payout actions; record audit event; retain snapshots for history.
- **Reissue**: create reissue run referencing voided run; allows corrected payouts with linkage for reconciliation.

## Multi-Approver Flow
- **Roles**: `admin` and `approver` must both sign off; approvals captured as audit events with digital signatures/actor IDs.
- **Sequencing**: either order allowed, but payment release requires both.
- **Delegation & Cutoffs**: assign backup approvers; enforce cutoff reminders (scheduled notifications before pay date/approval deadline).
- **Notifications**: emit notifications on review request, approval completion, rerun start, void/reissue actions, and upcoming cutoff reminders.

## Data Considerations
- Enforce immutability on calculation snapshots; new versions created for reruns/reissues instead of updates.
- Maintain referential integrity between runs, employees, time entries, and adjustments; disallow deleting source records once linked to a run.
- Store checksum/hash on snapshot payloads to detect tampering.
- Support reporting views to show lineage from original run → rerun → void → reissue.

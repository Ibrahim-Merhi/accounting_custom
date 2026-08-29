# Accounting Program

This app integrates the requested donation, custody, payment memo, payroll-review,
and management-reporting processes with ERPNext and HRMS.

## Setup after migration

1. Assign the generated roles to the appropriate users: Collector, Treasurer,
   Finance Officer, Association President, HR Coordinator, Responsible Manager,
   Volunteer, Public Relations, and CEO.
2. Create one Collector Profile for each collector. Add one custody account row
   for every currency the collector may receive.
3. Configure each Supplier's Accounts table for the companies in which it can be
   selected. Set Company on every Institution.
4. Confirm Mode of Payment accounts, company exchange rates, donor accounts,
   projects, and cost centers.
5. Give HR and Finance access to Employee Monthly Adjustment and configure
   deduction Salary Components.
6. Finance uses Payroll Cost Center Allocation to distribute each submitted
   Salary Structure Assignment across one or more company cost centers.

## Donation lifecycle

Collectors use Quick Donor when only name and phone are available. A Donation
Entry is submitted for finance approval. Submission is blocked until approved.
Approved collector donations debit the collector's currency custody account and
credit the selected donation/revenue account. Collector Handover transfers the
money from custody to the office cash or bank account and prevents handing over
more than the receipt balance.

## Payment Memo lifecycle

- Normal payment/custody: Applicant -> Responsible Manager -> Finance Officer ->
  Association President -> Treasurer.
- Salary advance: Applicant -> HR Coordinator -> Responsible Manager -> Finance
  Officer -> Association President -> Treasurer.
- Treasurer request: Treasurer -> Finance Officer -> Association President ->
  Treasurer.

Finance selects the payment or custody account. Each line can use a different
account, cost center, project, and invoice reference. Return and Reject are
available at each review stage. Custody Closure references the original custody
memo and cannot exceed its outstanding amount.

## Payroll

Payroll Cost Center Allocation lets Finance allocate a submitted Salary Structure
Assignment across one or more cost centers totaling 100%; cancellation restores
the previous allocation. Employee Monthly Adjustment records HR's monthly
deduction notes and creates submitted Additional Salary deductions after Finance
submission. Payroll Review records CEO and Association President review,
comments, returns, and approval of the exported Salary Register.

## Reports

- Daily Treasury Report
- Collector Collections
- Donor Donation History
- Project Donation Summary
- Pending Accounting Approvals
- Open Custodies
- Weekly Cost Center Comparison
- Weekly Cash Bank Comparison
- Monthly Cost Center Movement
- Monthly Cash Bank Balance
- Balance Sheet by Cost Center

All transactions and reports are linked from the Accounting Program workspace.

## Deployment

Run as the bench owner:

    bench --site erp.itihad.org migrate
    bench --site erp.itihad.org clear-cache

Verify the installed schema:

    bench --site erp.itihad.org execute accounting_custom.verification.verify_accounting_program

Then reload the web workers:

    sudo supervisorctl restart frappe-bench-web:frappe-bench-frappe-web

Existing Institution records must be assigned a Company. Existing collector
receipts can remain direct receipts or be assigned to a Collector Profile before
submission.

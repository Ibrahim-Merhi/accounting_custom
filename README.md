# Accounting Custom

A source-controlled ERPNext/Frappe v15 extension for company-specific exchange rates and donation accounting.

## Included

- App-owned `Company Exchange Rate` with direct/inverse lookup API
- App-owned, submittable `Donation Entry` with multi-currency payment rows
- Balanced `Accounting Payment Entry` with debit/credit rows and supported parties
- Collector profiles, multi-currency custody accounts, and treasury handovers
- Finance-approved donation receipts with restricted quick donor creation
- Multi-stage Payment Memos for payments, custody, salary advances, and closures
- Finance-owned payroll cost-center allocations, monthly employee adjustments,
  and CEO/president payroll review
- Operational and management accounting reports in the Accounting Program workspace

See [Accounting Program](docs/accounting_program.md) for setup and workflow details.
- Company-scoped Branch tracking on Journal Entry and GL Entry
- Donor/company account validation through `Donor.custom_accounts`
- Supported four-row GL posting per donation payment and immutable-ledger cancellation
- Combined USD/LBP receipt totals and Arabic amount in words
- Browser Umm Al-Qura Hijri date behavior
- Arabic `سند قبض` print format
- Company-abbreviation naming for new Journal Entries and Payment Entries
- Existing-site adoption and fresh-site installation support

The legacy non_profit/relief_management `Donation` DocType is intentionally not modified.

See [production migration](docs/production_migration.md) before deploying.

## Dependencies

- Frappe v15
- ERPNext v15
- non_profit (provides Donor)

## Development

Run the app test suite on a dedicated test site:

```bash
bench --site test_site run-tests --app accounting_custom
```

Do not run migration tests first on production. Use a restored clone and verify exchange-rate record counts and GL history before deployment.

## License

MIT

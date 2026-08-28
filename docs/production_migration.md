# Production migration

`accounting_custom` adopts the existing UI-created `Donation Entry` and `Company Exchange Rate` objects in place.
It does not replace or migrate the legacy `Donation` DocType.

## Before deployment

1. Back up the production database and site files.
2. Record counts and names for Company Exchange Rate and Donation Entry.
3. Confirm Donation Entry contains no business records, as expected.
4. Confirm Company abbreviations are `ITHD`, `N`, `MNT`, `TUL`, and `EP` as applicable.
5. Keep the exported CSV files as the rollback specification.
6. Decide and record the Company for every existing Branch before migration.

## Deployment

1. Pull the reviewed app revision as the production `frappe` user.
2. Run `bench --site <site> migrate`.
3. Verify both DocTypes have module `Accounting Custom` and existing exchange-rate rows remain unchanged.
4. Verify the runtime scripts with the exact exported names are disabled, not manually deleted.
5. Test direct and inverse exchange rates.
6. Create and submit one Donation Entry containing one USD row and one LBP row in a controlled test company.
7. Confirm exactly eight active GL rows, then cancel and confirm immutable reversal history.
8. Render `سند قبض` and verify Arabic wording, dates, logo, and signatures.
9. Assign Company on each Branch, then create a Journal Entry and verify Branch reaches its GL rows.
10. Create a balanced multi-currency Accounting Payment Entry and verify debit equals credit in GL.

## Rollback

Restore the database backup and the previous app revision together. Do not restore only one side of the migration.
Never rename historical Journal Entries, Payment Entries, or GL vouchers.

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry import (
	AccountingPaymentEntry,
)


class TestAccountingPaymentGL(TestCase):
	@patch("accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry.get_account_details")
	@patch("accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry.get_mode_of_payment_account")
	def test_builds_balanced_multi_currency_rows(self, mode_account, details):
		mode_account.side_effect = ["Cash USD", "Cash LBP"]
		details.side_effect = lambda account, _company: __import__("frappe")._dict(
			account_currency="LBP" if account == "Cash LBP" else "USD", account_type=""
		)
		doc = SimpleNamespace(
			company="Itihad", custom_company_currency="USD", posting_date="2026-08-28",
			doctype="Accounting Payment Entry", name="APE-2026-00001",
			custom_branch="Beirut", remarks="Payment",
			accounting_rows=[
				SimpleNamespace(idx=1, mode_of_payment="Cash USD", account="Expense USD",
					currency="USD", amount=100, base_amount=100, cost_center="Main",
					party_type=None, party=None),
				SimpleNamespace(idx=2, mode_of_payment="Cash LBP", account="Supplier Control",
					currency="LBP", amount=8950000, base_amount=100, cost_center="Main",
					party_type="Supplier", party="SUP-1"),
			],
		)

		rows = AccountingPaymentEntry.get_gl_entries(doc)

		self.assertEqual(len(rows), 4)
		self.assertEqual(sum(row.debit for row in rows), 200)
		self.assertEqual(sum(row.credit for row in rows), 200)
		self.assertEqual(rows[2].party_type, "Supplier")
		self.assertEqual(rows[3].account, "Cash LBP")
		self.assertEqual(rows[3].credit_in_account_currency, 8950000)
		self.assertTrue(all(row.custom_branch == "Beirut" for row in rows))

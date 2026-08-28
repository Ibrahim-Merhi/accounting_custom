from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry import (
	AccountingPaymentEntry,
)


class TestAccountingPaymentGL(TestCase):
	@patch("accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry.frappe.get_cached_value")
	def test_builds_balanced_multi_currency_rows(self, get_cached_value):
		get_cached_value.side_effect = ["USD", "USD"]
		doc = SimpleNamespace(
			company="Itihad", custom_company_currency="USD", posting_date="2026-08-28",
			doctype="Accounting Payment Entry", name="APE-2026-00001",
			custom_branch="Beirut", remarks="Payment",
			accounts=[
				SimpleNamespace(idx=1, account="Cash USD", currency="USD", debit=100, credit=0,
					base_debit=100, base_credit=0, cost_center="Main", party_type=None, party=None),
				SimpleNamespace(idx=2, account="Expense USD", currency="LBP", debit=0, credit=8950000,
					base_debit=0, base_credit=100, cost_center="Main", party_type="Supplier", party="SUP-1"),
			],
		)

		rows = AccountingPaymentEntry.get_gl_entries(doc)

		self.assertEqual(sum(row.debit for row in rows), 100)
		self.assertEqual(sum(row.credit for row in rows), 100)
		self.assertEqual(rows[1].credit_in_account_currency, 100)
		self.assertEqual(rows[1].party_type, "Supplier")
		self.assertTrue(all(row.custom_branch == "Beirut" for row in rows))

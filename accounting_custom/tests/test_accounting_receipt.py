from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from accounting_custom.accounting_custom.doctype.accounting_receipt_entry.accounting_receipt_entry import (
	AccountingReceiptEntry,
)


class TestAccountingReceiptGL(TestCase):
	@patch("accounting_custom.accounting_custom.doctype.accounting_receipt_entry.accounting_receipt_entry.get_account_details")
	@patch("accounting_custom.accounting_custom.doctype.accounting_receipt_entry.accounting_receipt_entry.get_mode_of_payment_account")
	def test_mode_of_payment_is_debit_and_account_is_credit(self, mode_account, details):
		mode_account.return_value = "Cash LBP"
		details.side_effect = lambda account, _company: frappe._dict(
			account_currency="LBP" if account == "Cash LBP" else "USD",
			account_type="",
		)
		doc = SimpleNamespace(
			company="Itihad", custom_company_currency="USD", posting_date="2026-09-04",
			doctype="Accounting Receipt Entry", name="ITHD-ACC-ARE-2026-00001",
			custom_branch="Beirut", remarks="Receipt", custom_accounting_rows_copy=[
				SimpleNamespace(
					idx=1, mode_of_payment="Cash LBP", account="Income USD",
					currency="LBP", amount=8950000, base_amount=100, cost_center="Main",
					party_type=None, party=None,
				),
			],
		)

		rows = AccountingReceiptEntry.get_gl_entries(doc)

		self.assertEqual(len(rows), 2)
		self.assertEqual(rows[0].account, "Cash LBP")
		self.assertEqual(rows[0].debit, 100)
		self.assertEqual(rows[0].debit_in_account_currency, 8950000)
		self.assertEqual(rows[1].account, "Income USD")
		self.assertEqual(rows[1].credit, 100)
		self.assertEqual(rows[1].credit_in_account_currency, 100)
		self.assertEqual(rows[0].against, "Income USD")
		self.assertEqual(rows[1].against, "Cash LBP")

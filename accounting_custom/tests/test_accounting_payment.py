from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry import (
	AccountingPaymentEntry,
	backfill_arabic_amounts,
	can_submit_payment,
	get_supplier_account,
)


class TestAccountingPaymentGL(TestCase):
	def test_amendment_starts_new_approval_cycle(self):
		doc = SimpleNamespace(
			docstatus=0, amended_from="APE-00001", approval_status="Approved",
			approved_by="user@example.com", approved_on="2026-09-05",
			journal_entry="JV-00001", is_new=lambda: True,
		)

		AccountingPaymentEntry._reset_amendment_state(doc)

		self.assertEqual(doc.approval_status, "Draft")
		self.assertIsNone(doc.approved_by)
		self.assertIsNone(doc.approved_on)
		self.assertIsNone(doc.journal_entry)

	def test_saved_amendment_keeps_approval_progress(self):
		doc = SimpleNamespace(
			docstatus=0, amended_from="APE-00001",
			approval_status="Pending Finance Approval",
			approved_by=None, approved_on=None, journal_entry=None,
			is_new=lambda: False,
		)

		AccountingPaymentEntry._reset_amendment_state(doc)

		self.assertEqual(doc.approval_status, "Pending Finance Approval")

	@patch.object(frappe.db, "has_column")
	@patch.object(frappe.db, "table_exists", return_value=False)
	def test_backfill_skips_missing_table_during_install(self, table_exists, has_column):
		backfill_arabic_amounts()

		table_exists.assert_called_once_with("Accounting Payment Entry", cached=False)
		has_column.assert_not_called()

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
			custom_accounting_rows_copy=[
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

	@patch("accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry.get_account_details")
	@patch("accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry.get_mode_of_payment_account")
	def test_same_company_currency_account_accepts_multiple_row_currencies(self, mode_account, details):
		mode_account.side_effect = ["Cash USD", "Cash LBP"]
		details.side_effect = lambda account, _company: __import__("frappe")._dict(
			account_currency={
				"Cash USD": "USD",
				"Cash LBP": "LBP",
				"Shared Expense": "USD",
			}[account],
			account_type="",
		)
		doc = SimpleNamespace(
			company="Itihad", custom_company_currency="USD", posting_date="2026-09-22",
			doctype="Accounting Payment Entry", name="APE-2026-00002",
			custom_branch="Beirut", remarks="Mixed-currency payment",
			custom_accounting_rows_copy=[
				SimpleNamespace(idx=1, mode_of_payment="Cash USD", account="Shared Expense",
					currency="USD", amount=100, base_amount=100, cost_center="Main",
					party_type=None, party=None),
				SimpleNamespace(idx=2, mode_of_payment="Cash LBP", account="Shared Expense",
					currency="LBP", amount=8950000, base_amount=100, cost_center="Main",
					party_type=None, party=None),
			],
		)

		rows = AccountingPaymentEntry.get_gl_entries(doc)

		self.assertEqual(len(rows), 4)
		self.assertEqual([row.account for row in rows], [
			"Shared Expense", "Cash USD", "Shared Expense", "Cash LBP",
		])
		self.assertEqual([rows[0].debit_in_account_currency, rows[2].debit_in_account_currency], [100, 100])
		self.assertEqual(rows[1].credit_in_account_currency, 100)
		self.assertEqual(rows[3].credit_in_account_currency, 8950000)
		self.assertEqual(sum(row.debit for row in rows), 200)
		self.assertEqual(sum(row.credit for row in rows), 200)

	@patch("accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry.get_company_exchange_rate")
	@patch("accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry.get_account_details")
	@patch("accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry.get_mode_of_payment_account")
	def test_converts_row_to_third_currency_destination_account(self, mode_account, details, exchange_rate):
		mode_account.return_value = "Cash USD"
		details.side_effect = lambda account, _company: __import__("frappe")._dict(
			account_currency="LBP" if account == "Expense LBP" else "USD",
			account_type="",
		)
		exchange_rate.return_value = {"exchange_rate": 1 / 89500}
		doc = SimpleNamespace(
			company="Itihad", custom_company_currency="USD", posting_date="2026-09-22",
			doctype="Accounting Payment Entry", name="APE-2026-00003",
			custom_branch="Beirut", remarks="USD payment to LBP account",
			custom_accounting_rows_copy=[
				SimpleNamespace(idx=1, mode_of_payment="Cash USD", account="Expense LBP",
					currency="USD", amount=100, base_amount=100, cost_center="Main",
					party_type=None, party=None),
			],
		)

		rows = AccountingPaymentEntry.get_gl_entries(doc)

		self.assertEqual(rows[0].account_currency, "LBP")
		self.assertAlmostEqual(rows[0].debit_in_account_currency, 8950000)
		self.assertEqual(rows[0].debit, 100)
		self.assertEqual(rows[1].account_currency, "USD")
		self.assertEqual(rows[1].credit_in_account_currency, 100)
		exchange_rate.assert_called_once_with("Itihad", "LBP", "USD", "2026-09-22")

	def test_builds_debit_and_credit_totals_per_currency(self):
		totals = []
		doc = SimpleNamespace(
			custom_accounting_rows_copy=[
				SimpleNamespace(currency="USD", amount=100),
				SimpleNamespace(currency="LBP", amount=8950000),
				SimpleNamespace(currency="USD", amount=50),
			],
			set=lambda _fieldname, _value: totals.clear(),
			append=lambda _fieldname, value: totals.append(value),
		)

		AccountingPaymentEntry.set_currency_totals(doc)

		self.assertEqual(totals, [
			{"currency": "USD", "total_debit": 150, "total_credit": 150},
			{"currency": "LBP", "total_debit": 8950000, "total_credit": 8950000},
		])

	def test_treasurer_cannot_submit_payment(self):
		self.assertFalse(can_submit_payment("treasurer@example.com", ["Treasurer"]))
		self.assertTrue(can_submit_payment("finance@example.com", ["Finance Officer"]))

	@patch("accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry.get_account_details")
	@patch.object(frappe.db, "get_value", return_value="21100001 - Supplier - ITHD")
	def test_fetches_supplier_account_for_company(self, get_value, account_details):
		account = get_supplier_account("SUP-0001", "Itihad")

		self.assertEqual(account, "21100001 - Supplier - ITHD")
		get_value.assert_called_once_with(
			"Party Account",
			{"parenttype": "Supplier", "parent": "SUP-0001", "company": "Itihad"},
			"account",
		)
		account_details.assert_called_once_with("21100001 - Supplier - ITHD", "Itihad")

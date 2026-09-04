from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from accounting_custom.accounting.branch import (
	backfill_journal_entry_transaction_currency,
	set_journal_entry_transaction_currency,
	validate_journal_entry_branch,
)


class TestBranchValidation(TestCase):
	def setUp(self):
		translation = patch("accounting_custom.accounting.branch._", side_effect=lambda message: message)
		translation.start()
		self.addCleanup(translation.stop)

	@patch("accounting_custom.accounting.branch.frappe.db.get_value", return_value="Itihad")
	def test_matching_branch_company_is_allowed(self, _get_value):
		validate_journal_entry_branch(SimpleNamespace(company="Itihad", accounts=[SimpleNamespace(idx=1, custom_branch="Beirut")]))

	@patch("accounting_custom.accounting.branch.frappe.db.get_value")
	def test_empty_branch_is_allowed(self, get_value):
		validate_journal_entry_branch(SimpleNamespace(company="Itihad", accounts=[SimpleNamespace(idx=1, custom_branch=None)]))
		get_value.assert_not_called()

	@patch("accounting_custom.accounting.branch.frappe.throw", side_effect=frappe.ValidationError)
	@patch("accounting_custom.accounting.branch.frappe.db.get_value", return_value="Other")
	def test_cross_company_branch_is_rejected(self, _get_value, _throw):
		with self.assertRaises(frappe.ValidationError):
			validate_journal_entry_branch(SimpleNamespace(company="Itihad", accounts=[SimpleNamespace(idx=1, custom_branch="Beirut")]))


class TestJournalEntryTransactionCurrency(TestCase):
	def test_lbp_account_amount_is_preserved_for_general_ledger(self):
		gl_entry = frappe._dict({
			"voucher_type": "Journal Entry",
			"account_currency": "LBP",
			"debit": 198.88,
			"credit": 0,
			"debit_in_account_currency": 17800000,
			"credit_in_account_currency": 0,
		})

		set_journal_entry_transaction_currency(gl_entry)

		self.assertEqual(gl_entry.transaction_currency, "LBP")
		self.assertEqual(gl_entry.debit_in_transaction_currency, 17800000)
		self.assertEqual(gl_entry.credit_in_transaction_currency, 0)
		self.assertAlmostEqual(gl_entry.transaction_exchange_rate, 198.88 / 17800000)

	def test_usd_credit_is_preserved_for_general_ledger(self):
		gl_entry = frappe._dict({
			"voucher_type": "Journal Entry",
			"account_currency": "USD",
			"debit": 0,
			"credit": 200,
			"debit_in_account_currency": 0,
			"credit_in_account_currency": 200,
		})

		set_journal_entry_transaction_currency(gl_entry)

		self.assertEqual(gl_entry.transaction_currency, "USD")
		self.assertEqual(gl_entry.credit_in_transaction_currency, 200)
		self.assertEqual(gl_entry.transaction_exchange_rate, 1)

	@patch("accounting_custom.accounting.branch.frappe.db.sql")
	@patch("accounting_custom.accounting.branch.frappe.db.table_exists", return_value=True)
	def test_existing_journal_gl_entries_are_backfilled(self, _table_exists, sql):
		backfill_journal_entry_transaction_currency()

		query = sql.call_args.args[0]
		self.assertIn("transaction_currency = account_currency", query)
		self.assertIn("debit_in_transaction_currency = debit_in_account_currency", query)
		self.assertIn("credit_in_transaction_currency = credit_in_account_currency", query)
		self.assertIn("voucher_type = 'Journal Entry'", query)

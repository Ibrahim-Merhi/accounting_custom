from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from accounting_custom.accounting.donation_gl import (
	build_gl_entries,
	cancel_gl_entries,
	get_mode_of_payment_currency,
	post_gl_entries,
)


class TestDonationGL(TestCase):
	def setUp(self):
		frappe.local.flags = frappe._dict(in_test=True)
		frappe.local.message_log = []
		frappe.local.db = Mock()
		frappe.local.db.exists.return_value = None
		translation = patch("accounting_custom.accounting.donation_gl._", side_effect=lambda message: message)
		translation.start()
		self.addCleanup(translation.stop)
		self.doc = SimpleNamespace(
			doctype="Donation Entry", name="DON-2026-00001", company="Itihad",
			posting_date="2026-08-28", donor_account="Donor Account", donor="DONOR-1",
			project="Project 1", custom_company_currency="USD", remarks="Donation",
			payments=[
				SimpleNamespace(idx=1, mode_of_payment="Cash", received_in_account="Income",
					cost_center="Main - ITHD", currency="USD", donation_amount=200, base_amount=200),
				SimpleNamespace(idx=2, mode_of_payment="Bank", received_in_account="Income",
					cost_center="North - ITHD", currency="LBP", donation_amount=8950000, base_amount=100),
			],
		)

	@patch("accounting_custom.accounting.donation_gl.get_account_details")
	@patch("accounting_custom.accounting.donation_gl.get_mode_of_payment_account")
	def test_builds_four_rows_per_payment(self, mode_account, details):
		mode_account.side_effect = ["Cash Account", "Bank Account"]
		details.return_value = frappe._dict(account_currency="USD", account_type="")
		rows = build_gl_entries(self.doc)
		self.assertEqual(len(rows), 8)
		self.assertEqual([(r.account, r.debit, r.credit) for r in rows[:4]], [
			("Cash Account", 200, 0), ("Income", 0, 200),
			("Donor Account", 200, 0), ("Donor Account", 0, 200),
		])
		self.assertEqual([(r.account, r.debit, r.credit) for r in rows[4:]], [
			("Bank Account", 100, 0), ("Income", 0, 100),
			("Donor Account", 100, 0), ("Donor Account", 0, 100),
		])
		self.assertTrue(all(row.cost_center == "Main - ITHD" for row in rows[:4]))
		self.assertTrue(all(row.cost_center == "North - ITHD" for row in rows[4:]))
		self.assertEqual(rows[2].party_type, "Donor")
		self.assertEqual(rows[2].party, "DONOR-1")
		self.assertEqual(rows[4].transaction_currency, "LBP")
		self.assertEqual(rows[4].debit_in_transaction_currency, 8950000)
		self.assertEqual(rows[5].credit_in_transaction_currency, 8950000)

	@patch("accounting_custom.accounting.donation_gl.get_account_details")
	@patch("accounting_custom.accounting.donation_gl.get_mode_of_payment_account", return_value="Cash LBP")
	def test_mode_of_payment_currency_comes_from_default_account(self, _mode_account, details):
		details.return_value = frappe._dict(account_currency="LBP")

		self.assertEqual(get_mode_of_payment_currency("Cash LBP", "Itihad"), "LBP")

	@patch("accounting_custom.accounting.donation_gl.get_account_details")
	@patch("accounting_custom.accounting.donation_gl.get_mode_of_payment_account", return_value="Cash Account")
	def test_sets_donor_party_on_receivable_received_account(self, _mode_account, details):
		def account_details(account, _company):
			return frappe._dict(
				account_currency="USD",
				account_type="Receivable" if account == "Income" else "",
			)

		details.side_effect = account_details
		self.doc.payments = self.doc.payments[:1]
		rows = build_gl_entries(self.doc)

		self.assertEqual(rows[1].party_type, "Donor")
		self.assertEqual(rows[1].party, "DONOR-1")

	@patch("accounting_custom.accounting.donation_gl.make_gl_entries")
	@patch("accounting_custom.accounting.donation_gl.build_gl_entries", return_value=[1, 2, 3, 4])
	def test_posts_without_merging(self, _build, make_entries):
		post_gl_entries(self.doc)
		make_entries.assert_called_once_with([1, 2, 3, 4], merge_entries=False, update_outstanding="No")

	@patch("accounting_custom.accounting.donation_gl.make_reverse_gl_entries")
	def test_cancellation_uses_supported_reverse_api(self, reverse):
		cancel_gl_entries(self.doc)
		reverse.assert_called_once_with(
			voucher_type="Donation Entry", voucher_no="DON-2026-00001", update_outstanding="No"
		)

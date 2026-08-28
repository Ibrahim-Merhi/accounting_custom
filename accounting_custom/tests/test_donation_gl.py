from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from accounting_custom.accounting.donation_gl import build_gl_entries, cancel_gl_entries, post_gl_entries


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
			posting_date="2026-08-28", mode_of_payment="Cash", received_in_account="Income",
			donor_account="Donor Account", donor="DONOR-1", cost_center="Main - ITHD",
			project="Project 1", custom_company_currency="USD", currency="USD", donation_amount=200,
			base_donation_amount=200, remarks="Donation",
		)

	@patch("accounting_custom.accounting.donation_gl.get_account_currency_amount", return_value=200)
	@patch("accounting_custom.accounting.donation_gl.get_account_details")
	@patch("accounting_custom.accounting.donation_gl.get_mode_of_payment_account", return_value="Cash Account")
	def test_builds_exact_four_rows(self, _mode, details, _amount):
		details.return_value = frappe._dict(account_currency="USD")
		rows = build_gl_entries(self.doc)
		self.assertEqual(len(rows), 4)
		self.assertEqual([(r.account, r.debit, r.credit) for r in rows], [
			("Cash Account", 200, 0), ("Income", 0, 200),
			("Donor Account", 200, 0), ("Donor Account", 0, 200),
		])
		self.assertTrue(all(r.cost_center == "Main - ITHD" for r in rows))
		self.assertTrue(all(r.project == "Project 1" for r in rows))
		self.assertEqual(rows[2].party_type, "Donor")
		self.assertEqual(rows[2].party, "DONOR-1")

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

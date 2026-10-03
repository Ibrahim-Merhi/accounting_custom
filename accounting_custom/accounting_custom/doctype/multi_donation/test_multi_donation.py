from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from accounting_custom.accounting_custom.doctype.multi_donation.multi_donation import (
	MultiDonation,
	build_gl_entries,
)


class TestMultiDonation(FrappeTestCase):
	def test_metadata_contains_batch_fields(self):
		meta = frappe.get_meta("Multi Donation")
		self.assertTrue(meta.is_submittable)
		for fieldname in (
			"company", "posting_date", "custom_branch", "cost_center", "donor_account",
			"received_in_account", "remarks", "donations", "base_donation_amount",
		):
			self.assertTrue(meta.has_field(fieldname), fieldname)

	@patch("accounting_custom.accounting_custom.doctype.multi_donation.multi_donation.get_mode_of_payment_account")
	@patch("accounting_custom.accounting_custom.doctype.multi_donation.multi_donation.get_account_details")
	def test_gl_consolidates_receipts_and_keeps_each_donor_history(self, details, mode_account):
		mode_account.side_effect = lambda mode, _company: {"Cash USD": "Cash USD", "Cash LBP": "Cash LBP"}[mode]
		def account_details(account, _company):
			currencies = {"Cash USD": "USD", "Cash LBP": "LBP", "Donation Income": "USD", "Donor Control": "USD"}
			return frappe._dict(account_currency=currencies[account], account_type="")
		details.side_effect = account_details
		doc = SimpleNamespace(
			doctype="Multi Donation", name="MDON-1", company="Itihad", posting_date="2026-10-03",
			custom_branch="Tripoli", cost_center="Main", donor_account="Donor Control",
			received_in_account="Donation Income", custom_company_currency="USD", remarks="Batch",
			donations=[
				SimpleNamespace(idx=1, donor="DONOR-1", mode_of_payment="Cash USD", currency="USD", donation_amount=100, base_amount=100),
				SimpleNamespace(idx=2, donor="DONOR-2", mode_of_payment="Cash USD", currency="USD", donation_amount=50, base_amount=50),
			],
		)

		rows = build_gl_entries(doc)

		self.assertEqual(len(rows), 6)
		self.assertEqual(rows[0].account, "Cash USD")
		self.assertEqual(rows[0].debit, 150)
		self.assertEqual(rows[1].account, "Donation Income")
		self.assertEqual(rows[1].credit, 150)
		self.assertEqual([(row.party, row.debit, row.credit) for row in rows[2:]], [
			("DONOR-1", 100, 0), ("DONOR-1", 0, 100),
			("DONOR-2", 50, 0), ("DONOR-2", 0, 50),
		])

	def test_unapproved_document_cannot_submit(self):
		doc = SimpleNamespace(approval_status="Pending Finance Approval")
		with self.assertRaises(frappe.ValidationError):
			MultiDonation.before_submit(doc)

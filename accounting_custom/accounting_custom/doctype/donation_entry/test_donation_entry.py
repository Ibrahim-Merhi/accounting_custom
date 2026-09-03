import frappe
from frappe.tests.utils import FrappeTestCase

from accounting_custom.accounting_custom.doctype.donation_entry.donation_entry import DonationEntry


class TestDonationEntryMetadata(FrappeTestCase):
	def test_app_owned_metadata_is_compatible_with_export(self):
		meta = frappe.get_meta("Donation Entry")
		self.assertEqual(meta.module, "Accounting Custom")
		self.assertTrue(meta.is_submittable)
		self.assertEqual(meta.autoname, "DON-.YYYY.-.#####")
		for fieldname in (
			"donor", "company", "mode_of_payment", "base_donation_amount", "donor_account",
			"cost_center", "currency", "custom_company_currency", "project", "donation_amount",
			"exchange_rate", "received_in_account", "custom_hijri_date",
			"custom_amount_in_words_arabic", "total_usd", "total_lbp", "payments",
		):
			self.assertTrue(meta.has_field(fieldname), fieldname)

	def test_cost_center_is_submit_only_required(self):
		field = frappe.get_meta("Donation Entry").get_field("cost_center")
		self.assertFalse(field.reqd)

	def test_first_payment_is_synced_to_legacy_header_fields(self):
		doc = DonationEntry({"doctype": "Donation Entry"})
		doc.append("payments", {
			"mode_of_payment": "Cash",
			"cost_center": "Main - ITHD",
			"currency": "USD",
			"donation_amount": 100,
			"exchange_rate": 1,
			"received_in_account": "Donation Income - ITHD",
		})

		doc.sync_legacy_payment_fields()

		self.assertEqual(doc.mode_of_payment, "Cash")
		self.assertEqual(doc.cost_center, "Main - ITHD")
		self.assertEqual(doc.currency, "USD")
		self.assertEqual(doc.donation_amount, 100)
		self.assertEqual(doc.exchange_rate, 1)
		self.assertEqual(doc.received_in_account, "Donation Income - ITHD")

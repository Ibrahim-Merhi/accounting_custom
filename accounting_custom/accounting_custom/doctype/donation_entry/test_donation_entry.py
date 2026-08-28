import frappe
from frappe.tests.utils import FrappeTestCase


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

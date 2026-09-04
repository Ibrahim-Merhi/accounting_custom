from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from accounting_custom.naming.company_series import (
	set_accounting_payment_entry_series,
	set_accounting_receipt_entry_series,
	set_company_series,
	set_donation_entry_series,
)


class TestCompanyNaming(TestCase):
	def setUp(self):
		self.translation = patch(
			"accounting_custom.naming.company_series._", side_effect=lambda message: message
		)
		self.translation.start()
		self.addCleanup(self.translation.stop)

	@patch("accounting_custom.naming.company_series.frappe.get_cached_value")
	def test_journal_and_payment_patterns(self, get_cached_value):
		for abbreviation in ("ITHD", "N", "MNT", "TUL", "EP"):
			get_cached_value.return_value = abbreviation
			journal = SimpleNamespace(company="Company", doctype="Journal Entry")
			payment = SimpleNamespace(company="Company", doctype="Payment Entry")
			set_company_series(journal, "JV")
			set_company_series(payment, "PAY")
			self.assertEqual(journal.naming_series, f"{abbreviation}-ACC-JV-.YYYY.-.#####")
			self.assertEqual(payment.naming_series, f"{abbreviation}-ACC-PAY-.YYYY.-.#####")

	@patch("accounting_custom.naming.company_series.frappe.throw", side_effect=frappe.ValidationError)
	@patch("accounting_custom.naming.company_series.frappe.get_cached_value", return_value="BAD ABBR")
	def test_invalid_abbreviation_is_rejected(self, _get_cached_value, _throw):
		with self.assertRaises(frappe.ValidationError):
			set_company_series(SimpleNamespace(company="Company", doctype="Journal Entry"), "JV")

	@patch("accounting_custom.naming.company_series.frappe.get_cached_value", return_value="ITHD")
	def test_custom_accounting_document_patterns(self, _get_cached_value):
		payment = SimpleNamespace(company="Company", doctype="Accounting Payment Entry")
		donation = SimpleNamespace(company="Company", doctype="Donation Entry")

		set_accounting_payment_entry_series(payment)
		set_donation_entry_series(donation)

		self.assertEqual(payment.naming_series, "ITHD-ACC-APE-.YYYY.-.#####")
		self.assertEqual(donation.naming_series, "ITHD-ACC-DON-.YYYY.-.#####")

	@patch("accounting_custom.naming.company_series.frappe.get_cached_value", return_value="ITHD")
	def test_accounting_receipt_pattern(self, _get_cached_value):
		receipt = SimpleNamespace(company="Company", doctype="Accounting Receipt Entry")
		set_accounting_receipt_entry_series(receipt)
		self.assertEqual(receipt.naming_series, "ITHD-ACC-ARE-.YYYY.-.#####")

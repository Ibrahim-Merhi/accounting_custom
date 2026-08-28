from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from accounting_custom.accounting_custom.doctype.company_exchange_rate.company_exchange_rate import (
	CompanyExchangeRate,
)


class TestCompanyExchangeRate(FrappeTestCase):
	def make_rate(self, **values):
		return CompanyExchangeRate(
			{
				"doctype": "Company Exchange Rate",
				"company": "Test Company",
				"from_currency": "USD",
				"to_currency": "LBP",
				"exchange_rate": 89500,
				"effective_date": "2026-08-28",
				"enabled": 1,
				**values,
			}
		)

	@patch("frappe.db.exists", return_value=None)
	def test_valid_rate(self, _exists):
		self.make_rate().validate()

	def test_same_currency_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_rate(to_currency="USD").validate()

	def test_zero_rate_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_rate(exchange_rate=0).validate()

	def test_negative_rate_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_rate(exchange_rate=-1).validate()

	def test_missing_company_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_rate(company=None).validate()

	def test_missing_from_currency_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_rate(from_currency=None).validate()

	def test_missing_to_currency_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_rate(to_currency=None).validate()

	def test_missing_effective_date_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_rate(effective_date=None).validate()

	@patch("frappe.db.exists", return_value="CER-00001")
	def test_enabled_duplicate_is_rejected(self, _exists):
		with self.assertRaises(frappe.ValidationError):
			self.make_rate().validate()

	@patch("frappe.db.exists", return_value="CER-00001")
	def test_disabled_duplicate_is_allowed(self, exists):
		self.make_rate(enabled=0).validate()
		exists.assert_not_called()

	@patch("frappe.db.exists", return_value=None)
	def test_current_document_is_excluded_from_duplicate_check(self, exists):
		doc = self.make_rate()
		doc.name = "CER-00001"
		doc.validate()

		filters = exists.call_args.args[1]
		self.assertEqual(filters["name"], ["!=", "CER-00001"])

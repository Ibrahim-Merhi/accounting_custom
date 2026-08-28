from unittest import TestCase
from unittest.mock import patch

import frappe
from frappe.utils import getdate

from accounting_custom.api.exchange_rate import get_company_exchange_rate


class TestGetCompanyExchangeRate(TestCase):
	def setUp(self):
		frappe.local.flags = frappe._dict(in_test=True)
		frappe.local.message_log = []
		translation = patch("accounting_custom.api.exchange_rate._", side_effect=lambda message: message)
		translation.start()
		self.addCleanup(translation.stop)
		throw = patch("accounting_custom.api.exchange_rate.frappe.throw", side_effect=frappe.ValidationError)
		throw.start()
		self.addCleanup(throw.stop)

	@patch("accounting_custom.api.exchange_rate.nowdate", return_value="2026-08-28")
	@patch("accounting_custom.api.exchange_rate.frappe.get_all")
	def test_same_currency_returns_one_without_query(self, get_all, _nowdate):
		result = get_company_exchange_rate("Itihad", "USD", "USD")

		self.assertEqual(result["exchange_rate"], 1)
		self.assertEqual(result["rate_date"], getdate("2026-08-28"))
		self.assertIsNone(result["rate_document"])
		self.assertEqual(result["is_inverse"], 0)
		get_all.assert_not_called()

	@patch("accounting_custom.api.exchange_rate.frappe.get_all")
	def test_direct_rate(self, get_all):
		get_all.return_value = [
			frappe._dict(name="CER-00001", exchange_rate=89500, effective_date="2026-08-01")
		]

		result = get_company_exchange_rate("Itihad", "USD", "LBP", "2026-08-28")

		self.assertEqual(result["exchange_rate"], 89500)
		self.assertEqual(result["rate_document"], "CER-00001")
		self.assertEqual(result["is_inverse"], 0)
		self.assertEqual(get_all.call_count, 1)

	@patch("accounting_custom.api.exchange_rate.frappe.get_all")
	def test_inverse_rate(self, get_all):
		get_all.side_effect = [
			[],
			[frappe._dict(name="CER-00002", exchange_rate=89500, effective_date="2026-08-01")],
		]

		result = get_company_exchange_rate("Itihad", "LBP", "USD", "2026-08-28")

		self.assertAlmostEqual(result["exchange_rate"], 1 / 89500)
		self.assertEqual(result["rate_document"], "CER-00002")
		self.assertEqual(result["is_inverse"], 1)

	@patch("accounting_custom.api.exchange_rate.frappe.get_all", return_value=[])
	def test_missing_rate_is_rejected(self, _get_all):
		with self.assertRaises(frappe.ValidationError):
			get_company_exchange_rate("Itihad", "USD", "LBP", "2026-08-28")

	@patch("accounting_custom.api.exchange_rate.frappe.get_all")
	def test_zero_direct_rate_is_rejected(self, get_all):
		get_all.return_value = [
			frappe._dict(name="CER-00001", exchange_rate=0, effective_date="2026-08-01")
		]

		with self.assertRaises(frappe.ValidationError):
			get_company_exchange_rate("Itihad", "USD", "LBP", "2026-08-28")

	@patch("accounting_custom.api.exchange_rate.frappe.get_all")
	def test_zero_inverse_rate_is_rejected(self, get_all):
		get_all.side_effect = [
			[],
			[frappe._dict(name="CER-00002", exchange_rate=0, effective_date="2026-08-01")],
		]

		with self.assertRaises(frappe.ValidationError):
			get_company_exchange_rate("Itihad", "LBP", "USD", "2026-08-28")

	def test_company_is_required(self):
		with self.assertRaises(frappe.ValidationError):
			get_company_exchange_rate(None, "USD", "LBP", "2026-08-28")

	def test_from_currency_is_required(self):
		with self.assertRaises(frappe.ValidationError):
			get_company_exchange_rate("Itihad", None, "LBP", "2026-08-28")

	def test_to_currency_is_required(self):
		with self.assertRaises(frappe.ValidationError):
			get_company_exchange_rate("Itihad", "USD", None, "2026-08-28")

	@patch("accounting_custom.api.exchange_rate.frappe.get_all")
	def test_query_filters_and_order(self, get_all):
		get_all.return_value = [
			frappe._dict(name="CER-00001", exchange_rate=89500, effective_date="2026-08-01")
		]

		get_company_exchange_rate("Itihad", "USD", "LBP", "2026-08-28")

		kwargs = get_all.call_args.kwargs
		self.assertEqual(kwargs["filters"]["company"], "Itihad")
		self.assertEqual(kwargs["filters"]["from_currency"], "USD")
		self.assertEqual(kwargs["filters"]["to_currency"], "LBP")
		self.assertEqual(kwargs["filters"]["effective_date"], ["<=", getdate("2026-08-28")])
		self.assertEqual(kwargs["filters"]["enabled"], 1)
		self.assertEqual(kwargs["order_by"], "effective_date desc, creation desc")
		self.assertEqual(kwargs["limit_page_length"], 1)

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from accounting_custom.accounting.standard_exchange_rate import (
	apply_journal_entry_exchange_rates,
	apply_payment_entry_exchange_rates,
	apply_transaction_exchange_rate,
)


class TestStandardExchangeRate(TestCase):
	def setUp(self):
		translation = patch(
			"accounting_custom.accounting.standard_exchange_rate._", side_effect=lambda message: message
		)
		translation.start()
		self.addCleanup(translation.stop)

	@patch("accounting_custom.accounting.standard_exchange_rate.get_company_exchange_rate")
	@patch("accounting_custom.accounting.standard_exchange_rate.frappe.get_cached_value", return_value="USD")
	def test_transaction_uses_document_date_and_currency(self, _company_currency, get_rate):
		get_rate.return_value = {"exchange_rate": 89500}
		doc = frappe._dict(
			doctype="Sales Order", company="Itihad", currency="LBP",
			transaction_date="2026-08-28", conversion_rate=1,
		)

		apply_transaction_exchange_rate(doc)

		self.assertEqual(doc.conversion_rate, 89500)
		get_rate.assert_called_once_with(
			company="Itihad", from_currency="LBP", to_currency="USD",
			transaction_date="2026-08-28",
		)

	@patch("accounting_custom.accounting.standard_exchange_rate.get_company_exchange_rate")
	@patch("accounting_custom.accounting.standard_exchange_rate.frappe.get_cached_value", return_value="USD")
	def test_payment_sets_both_account_rates(self, _company_currency, get_rate):
		get_rate.side_effect = [{"exchange_rate": 1}, {"exchange_rate": 1 / 89500}]
		doc = SimpleNamespace(
			company="Itihad", posting_date="2026-08-28",
			paid_from_account_currency="USD", paid_to_account_currency="LBP",
			source_exchange_rate=0, target_exchange_rate=0,
		)

		apply_payment_entry_exchange_rates(doc)

		self.assertEqual(doc.source_exchange_rate, 1)
		self.assertAlmostEqual(doc.target_exchange_rate, 1 / 89500)

	@patch("accounting_custom.accounting.standard_exchange_rate.get_company_exchange_rate")
	@patch("accounting_custom.accounting.standard_exchange_rate.frappe.get_cached_value", return_value="USD")
	def test_journal_sets_each_row_rate(self, _company_currency, get_rate):
		get_rate.side_effect = [{"exchange_rate": 1}, {"exchange_rate": 1 / 89500}]
		doc = SimpleNamespace(
			company="Itihad", posting_date="2026-08-28",
			accounts=[
				SimpleNamespace(account="Cash USD", account_currency="USD", exchange_rate=0),
				SimpleNamespace(account="Cash LBP", account_currency="LBP", exchange_rate=0),
			],
		)

		apply_journal_entry_exchange_rates(doc)

		self.assertEqual(doc.accounts[0].exchange_rate, 1)
		self.assertAlmostEqual(doc.accounts[1].exchange_rate, 1 / 89500)

	@patch("accounting_custom.accounting.standard_exchange_rate.get_company_exchange_rate")
	def test_journal_keeps_transaction_specific_rates(self, get_rate):
		doc = frappe._dict(
			company="Itihad",
			posting_date="2026-08-28",
			flags=frappe._dict(ignore_company_exchange_rate=True),
			accounts=[frappe._dict(exchange_rate=1 / 90000)],
		)

		apply_journal_entry_exchange_rates(doc)

		self.assertAlmostEqual(doc.accounts[0].exchange_rate, 1 / 90000)
		get_rate.assert_not_called()

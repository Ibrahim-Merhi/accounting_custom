from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from accounting_custom.accounting_custom.doctype.currency_exchange.currency_exchange import CurrencyExchange


class TestCurrencyExchange(TestCase):
	@patch("accounting_custom.accounting_custom.doctype.currency_exchange.currency_exchange.get_company_exchange_rate")
	def test_cross_rate_and_target_amount_are_balanced(self, get_rate):
		get_rate.side_effect = [{"exchange_rate": 1}, {"exchange_rate": 1 / 89500}]
		doc = CurrencyExchange({"doctype": "Currency Exchange", "from_amount": 100})
		doc.company = "Itihad"
		doc.company_currency = "USD"
		doc.posting_date = "2026-09-03"
		doc.from_currency = "USD"
		doc.to_currency = "LBP"

		doc._set_amounts()

		self.assertAlmostEqual(doc.exchange_rate, 89500)
		self.assertAlmostEqual(doc.to_amount, 8950000)

	@patch("accounting_custom.accounting_custom.doctype.currency_exchange.currency_exchange.get_account_details")
	@patch("accounting_custom.accounting_custom.doctype.currency_exchange.currency_exchange.get_mode_of_payment_account")
	def test_payment_account_currency_is_used(self, get_account, get_details):
		get_account.return_value = "Cash LBP - ITHD"
		get_details.return_value = SimpleNamespace(account_currency="LBP")
		doc = CurrencyExchange({"doctype": "Currency Exchange", "company": "Itihad"})
		doc.company_currency = "USD"

		self.assertEqual(doc._get_payment_account("Cash LBP"), ("Cash LBP - ITHD", "LBP"))

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from accounting_custom.accounting_custom.doctype.accounting_currency_exchange.accounting_currency_exchange import (
	AccountingCurrencyExchange,
)


class TestAccountingCurrencyExchange(TestCase):
	@patch("accounting_custom.accounting_custom.doctype.accounting_currency_exchange.accounting_currency_exchange.get_company_exchange_rate")
	def test_cross_rate_and_target_amount_are_balanced(self, get_rate):
		get_rate.side_effect = [{"exchange_rate": 1}, {"exchange_rate": 1 / 89500}]
		doc = AccountingCurrencyExchange({"doctype": "Accounting Currency Exchange", "from_amount": 100})
		doc.company = "Itihad"
		doc.company_currency = "USD"
		doc.posting_date = "2026-09-03"
		doc.from_currency = "USD"
		doc.to_currency = "LBP"

		doc._set_amounts()

		self.assertAlmostEqual(doc.exchange_rate, 89500)
		self.assertAlmostEqual(doc.to_amount, 8950000)

	@patch("accounting_custom.accounting_custom.doctype.accounting_currency_exchange.accounting_currency_exchange.get_account_details")
	@patch("accounting_custom.accounting_custom.doctype.accounting_currency_exchange.accounting_currency_exchange.get_mode_of_payment_account")
	def test_payment_account_currency_is_used(self, get_account, get_details):
		get_account.return_value = "Cash LBP - ITHD"
		get_details.return_value = SimpleNamespace(account_currency="LBP")
		doc = AccountingCurrencyExchange({"doctype": "Accounting Currency Exchange", "company": "Itihad"})
		doc.company_currency = "USD"

		self.assertEqual(doc._get_payment_account("Cash LBP"), ("Cash LBP - ITHD", "LBP"))

	@patch("accounting_custom.accounting_custom.doctype.accounting_currency_exchange.accounting_currency_exchange.frappe.get_doc")
	def test_submit_creates_journal_with_remarks(self, get_doc):
		journal = MagicMock()
		get_doc.return_value = journal
		doc = AccountingCurrencyExchange({
			"doctype": "Accounting Currency Exchange",
			"name": "ACX-2026-00001",
			"company": "Itihad",
			"posting_date": "2026-09-03",
			"company_currency": "USD",
			"source_account": "Cash USD - ITHD",
			"from_currency": "USD",
			"from_amount": 10,
			"target_account": "Cash LBP - ITHD",
			"to_currency": "LBP",
			"to_amount": 895000,
			"remarks": "Exchange cash for office use",
		})
		doc._base_rate = MagicMock(side_effect=[1 / 89500, 1])
		doc.db_set = MagicMock()

		doc.on_submit()

		journal_values = get_doc.call_args.args[0]
		self.assertEqual(journal_values["user_remark"], "Exchange cash for office use")
		self.assertEqual(journal.append.call_count, 2)
		journal.insert.assert_called_once_with()
		journal.submit.assert_called_once_with()

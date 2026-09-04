from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from accounting_custom.accounting_custom.doctype.accounting_currency_exchange.accounting_currency_exchange import (
	AccountingCurrencyExchange,
)


class TestAccountingCurrencyExchange(TestCase):
	def test_exchange_rate_field_is_removed(self):
		meta = frappe.get_meta("Accounting Currency Exchange")
		self.assertFalse(meta.has_field("exchange_rate"))
		self.assertFalse(meta.get_field("to_amount").read_only)

	@patch("accounting_custom.accounting_custom.doctype.accounting_currency_exchange.accounting_currency_exchange._get_rate")
	def test_company_rates_are_used_for_ledger_valuation(self, get_rate):
		get_rate.side_effect = [1, 1 / 90000]
		doc = AccountingCurrencyExchange({
			"doctype": "Accounting Currency Exchange",
			"company_currency": "USD",
			"from_currency": "USD",
			"to_currency": "LBP",
			"company": "Itihad",
			"posting_date": "2026-09-04",
		})

		source_rate, target_rate = doc._journal_exchange_rates()

		self.assertEqual(source_rate, 1)
		self.assertAlmostEqual(target_rate, 1 / 90000)
		self.assertEqual(get_rate.call_count, 2)

	@patch("accounting_custom.accounting_custom.doctype.accounting_currency_exchange.accounting_currency_exchange.get_account_details")
	@patch("accounting_custom.accounting_custom.doctype.accounting_currency_exchange.accounting_currency_exchange.get_mode_of_payment_account")
	def test_payment_account_currency_is_used(self, get_account, get_details):
		get_account.return_value = "Cash LBP - ITHD"
		get_details.return_value = SimpleNamespace(account_currency="LBP")
		doc = AccountingCurrencyExchange({"doctype": "Accounting Currency Exchange", "company": "Itihad"})
		doc.company_currency = "USD"

		self.assertEqual(doc._get_payment_account("Cash LBP"), ("Cash LBP - ITHD", "LBP"))

	@patch("accounting_custom.accounting_custom.doctype.accounting_currency_exchange.accounting_currency_exchange.frappe.get_doc")
	@patch.object(AccountingCurrencyExchange, "_get_round_off_account", return_value="67500002 - Round Off - ITHD")
	@patch.object(AccountingCurrencyExchange, "_journal_exchange_rates", return_value=(1, 1 / 90000))
	def test_submit_creates_journal_with_remarks_and_rounding(self, get_rates, get_round_off, get_doc):
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
			"from_cost_center": "General - ITHD",
			"target_account": "Cash LBP - ITHD",
			"to_currency": "LBP",
			"to_amount": 895000,
			"to_cost_center": "General - ITHD",
			"remarks": "Exchange cash for office use",
		})
		doc.db_set = MagicMock()

		doc.on_submit()

		journal_values = get_doc.call_args.args[0]
		self.assertEqual(journal_values["user_remark"], "Exchange cash for office use")
		self.assertEqual(journal.append.call_count, 3)
		target_row = journal.append.call_args_list[0].args[1]
		source_row = journal.append.call_args_list[1].args[1]
		self.assertEqual(target_row["debit_in_account_currency"], 895000)
		self.assertEqual(target_row["cost_center"], "General - ITHD")
		self.assertEqual(source_row["credit_in_account_currency"], 10)
		self.assertEqual(source_row["cost_center"], "General - ITHD")
		rounding_row = journal.append.call_args_list[2].args[1]
		self.assertEqual(rounding_row["account"], "67500002 - Round Off - ITHD")
		self.assertAlmostEqual(rounding_row["debit_in_account_currency"], 10 - (895000 / 90000))
		self.assertEqual(rounding_row["account_currency"], "USD")
		self.assertTrue(journal.flags.ignore_company_exchange_rate)
		journal.insert.assert_called_once_with()
		journal.submit.assert_called_once_with()

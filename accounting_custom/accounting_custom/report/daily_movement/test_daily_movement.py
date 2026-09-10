from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from accounting_custom.accounting_custom.report.daily_movement.daily_movement import (
	company_condition,
	currency_account_condition,
	execute,
	get_selected_companies,
	get_transactions,
)


class TestDailyMovement(TestCase):
	def setUp(self):
		frappe.local.lang = "en"
		frappe.local.db = Mock()
		translation = patch(
			"accounting_custom.accounting_custom.report.daily_movement.daily_movement._",
			side_effect=lambda message: message,
		)
		translation.start()
		self.addCleanup(translation.stop)

	def test_company_condition_supports_one_or_all_except_namaa(self):
		selected = company_condition("gle", frappe._dict(companies=("Itihad", "Other")))
		all_companies = company_condition("gle", frappe._dict(companies=()))

		self.assertIn("gle.company in %(companies)s", selected)
		self.assertIn("gle.company != %(excluded_company)s", selected)
		self.assertEqual(all_companies, "gle.company != %(excluded_company)s")

	def test_selected_companies_are_normalized_and_namaa_is_excluded(self):
		self.assertEqual(get_selected_companies('["Itihad", "Namaa", "Other"]'), ("Itihad", "Other"))
		self.assertEqual(get_selected_companies("Itihad"), ("Itihad",))
		self.assertEqual(get_selected_companies(None), ())

	def test_usd_is_limited_to_the_configured_cash_account(self):
		condition = currency_account_condition("gle", "account")

		self.assertIn("gle.account_currency != 'USD'", condition)
		self.assertIn("account.account_number = '53000002'", condition)

	@patch("frappe.db.sql", return_value=[])
	def test_transactions_are_limited_to_journal_entries(self, db_sql):
		get_transactions(
			frappe._dict(
				companies=("Test",),
				excluded_company="Namaa",
				date="2026-09-01",
			)
		)
		query = db_sql.call_args.args[0]

		self.assertIn("`tabJournal Entry`", query)
		self.assertIn("gle.voucher_type = 'Journal Entry'", query)
		self.assertIn("coalesce(gle.party_type, '') = ''", query)
		self.assertIn("coalesce(line.party_type, '') = ''", query)
		self.assertEqual(query.count("account.account_number = '53000002'"), 2)
		self.assertIn("line.parent = gle.voucher_no", query)
		self.assertIn("line.account = gle.account", query)
		self.assertEqual(query.count("max(nullif(line.user_remark, ''))"), 2)
		self.assertIn("trim(replace(max(nullif(gle.remarks, '')), 'Note:', ''))", query)
		self.assertIn("trim(replace(max(nullif(journal.user_remark, '')), 'Note:', ''))", query)
		self.assertNotIn("`tabDonation Entry`", query)
		self.assertNotIn("`tabAccounting Payment Entry`", query)
		self.assertNotIn("`tabAccounting Receipt Entry`", query)

	@patch(
		"accounting_custom.accounting_custom.report.daily_movement.daily_movement.get_transactions"
	)
	@patch("accounting_custom.accounting_custom.report.daily_movement.daily_movement.get_balances")
	def test_current_balance_uses_opening_and_visible_movements(self, get_balances, get_transactions):
		get_balances.return_value = {("Test", "LBP"): 1_000_000, ("Test", "USD"): 500}
		get_transactions.return_value = [
			frappe._dict(currency="LBP", incoming=300_000, outgoing=None),
			frappe._dict(currency="LBP", incoming=None, outgoing=100_000),
			frappe._dict(currency="USD", incoming=100, outgoing=None),
			frappe._dict(currency="USD", incoming=None, outgoing=50),
		]

		_columns, rows = execute({"company": "Test", "date": "2026-09-01"})
		sections = {row["currency"]: row for row in rows if row.get("is_section")}

		self.assertEqual(sections["LBP"]["previous_balance"], 1_000_000)
		self.assertEqual(sections["LBP"]["current_balance"], 1_200_000)
		self.assertEqual(sections["USD"]["previous_balance"], 500)
		self.assertEqual(sections["USD"]["current_balance"], 550)

	@patch(
		"accounting_custom.accounting_custom.report.daily_movement.daily_movement.get_transactions"
	)
	@patch("accounting_custom.accounting_custom.report.daily_movement.daily_movement.get_balances")
	def test_all_companies_have_screen_separators(self, get_balances, get_transactions):
		get_balances.return_value = {}
		get_transactions.return_value = [
			frappe._dict(company="Alpha", currency="LBP", incoming=10, outgoing=None),
			frappe._dict(company="Beta", currency="LBP", incoming=20, outgoing=None),
		]

		_columns, rows = execute({"date": "2026-09-01"})
		company_rows = [row for row in rows if row.get("is_company")]

		self.assertEqual([row["description"] for row in company_rows], ["Company: Alpha", "Company: Beta"])
		self.assertTrue(all(not row.get("voucher_no") for row in company_rows))
		section_order = [
			(row.get("company"), row.get("currency")) for row in rows if row.get("is_section")
		]
		self.assertEqual(
			section_order,
			[("Alpha", "LBP"), ("Alpha", "USD"), ("Beta", "LBP"), ("Beta", "USD")],
		)

	@patch(
		"accounting_custom.accounting_custom.report.daily_movement.daily_movement.get_transactions"
	)
	@patch("accounting_custom.accounting_custom.report.daily_movement.daily_movement.get_balances")
	def test_additional_currencies_get_their_own_section(self, get_balances, get_transactions):
		get_balances.return_value = {("Test", "QAR"): 500}
		get_transactions.return_value = [
			frappe._dict(company="Test", currency="QAR", incoming=100, outgoing=25),
		]

		_columns, rows = execute({"company": "Test", "date": "2026-09-10"})
		section = next(row for row in rows if row.get("is_section") and row["currency"] == "QAR")

		self.assertEqual(section["description"], "QAR")
		self.assertEqual(section["previous_balance"], 500)
		self.assertEqual(section["current_balance"], 575)
		self.assertEqual(section["opening_date"], "09-09-2026")

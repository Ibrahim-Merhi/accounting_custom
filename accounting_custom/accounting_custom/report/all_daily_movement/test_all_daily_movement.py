from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from accounting_custom.accounting_custom.report.all_daily_movement.all_daily_movement import (
	company_condition,
	currency_account_condition,
	execute,
	get_selected_companies,
	get_transactions,
)


class TestAllDailyMovement(TestCase):
	def setUp(self):
		frappe.local.lang = "en"
		frappe.local.db = Mock()
		translation = patch(
			"accounting_custom.accounting_custom.report.all_daily_movement.all_daily_movement._",
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

	def test_each_report_uses_only_its_configured_cash_accounts(self):
		condition = currency_account_condition("gle", "account")

		self.assertIn("gle.account_currency = 'LBP'", condition)
		self.assertIn("account.account_number in ('53000001')", condition)
		self.assertIn("gle.account_currency = 'USD'", condition)
		self.assertIn("account.account_number in ('53000002', '53010001')", condition)
		for account_number in range(53000003, 53000011):
			self.assertIn(str(account_number), condition)
		self.assertIn("account.account_number in ('53000004', '53010003')", condition)
		self.assertIn("account.account_number in ('53000005', '53010002')", condition)

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
		self.assertEqual(query.count("account.account_number in ('53000001')"), 2)
		self.assertEqual(query.count("account.account_number in ('53000002', '53010001')"), 2)
		self.assertIn("53000003", query)
		self.assertIn("line.parent = gle.voucher_no", query)
		self.assertIn("line.account = gle.account", query)
		self.assertEqual(query.count("max(nullif(line.user_remark, ''))"), 2)
		self.assertIn("trim(replace(max(nullif(gle.remarks, '')), 'Note:', ''))", query)
		self.assertIn("trim(replace(max(nullif(journal.user_remark, '')), 'Note:', ''))", query)
		self.assertNotIn("`tabDonation Entry`", query)
		self.assertNotIn("`tabAccounting Payment Entry`", query)
		self.assertNotIn("`tabAccounting Receipt Entry`", query)

	@patch(
		"accounting_custom.accounting_custom.report.all_daily_movement.all_daily_movement.get_transactions"
	)
	@patch("accounting_custom.accounting_custom.report.all_daily_movement.all_daily_movement.get_balances")
	def test_current_balance_uses_opening_and_visible_movements(self, get_balances, get_transactions):
		get_balances.return_value = {("Test", "53000001"): 1_000_000, ("Test", "53000002"): 500}
		get_transactions.return_value = [
			frappe._dict(currency="LBP", account_number="53000001", incoming=300_000, outgoing=None),
			frappe._dict(currency="LBP", account_number="53000001", incoming=None, outgoing=100_000),
			frappe._dict(currency="USD", account_number="53000002", incoming=100, outgoing=None),
			frappe._dict(currency="USD", account_number="53000002", incoming=None, outgoing=50),
		]

		_columns, rows = execute({"company": "Test", "date": "2026-09-01"})
		sections = {row["section_key"]: row for row in rows if row.get("is_section")}

		self.assertEqual(sections["53000001"]["previous_balance"], 1_000_000)
		self.assertEqual(sections["53000001"]["current_balance"], 1_200_000)
		self.assertEqual(sections["53000001"]["currency_name_ar"], "الليرة اللبنانية")
		self.assertEqual(sections["53000002"]["previous_balance"], 500)
		self.assertEqual(sections["53000002"]["current_balance"], 550)

	@patch(
		"accounting_custom.accounting_custom.report.all_daily_movement.all_daily_movement.get_transactions"
	)
	@patch("accounting_custom.accounting_custom.report.all_daily_movement.all_daily_movement.get_balances")
	def test_all_companies_have_screen_separators(self, get_balances, get_transactions):
		get_balances.return_value = {}
		get_transactions.return_value = [
			frappe._dict(company="Alpha", currency="LBP", account_number="53000001", incoming=10, outgoing=None),
			frappe._dict(company="Beta", currency="LBP", account_number="53000001", incoming=20, outgoing=None),
		]

		_columns, rows = execute({"date": "2026-09-01"})
		company_rows = [row for row in rows if row.get("is_company")]

		self.assertEqual([row["description"] for row in company_rows], ["Company: Alpha", "Company: Beta"])
		self.assertTrue(all(not row.get("voucher_no") for row in company_rows))
		section_order = [
			(row.get("company"), row.get("currency")) for row in rows if row.get("is_section")
		]
		self.assertEqual(
			section_order[:2],
			[("Alpha", "LBP"), ("Alpha", "USD")],
		)

	@patch(
		"accounting_custom.accounting_custom.report.all_daily_movement.all_daily_movement.get_transactions"
	)
	@patch("accounting_custom.accounting_custom.report.all_daily_movement.all_daily_movement.get_balances")
	def test_report_includes_all_configured_account_sections(self, get_balances, get_transactions):
		get_balances.return_value = {
			("Test", "53000001"): 1_000,
			("Test", "53010001"): 10,
			("Test", "53000005"): 500,
		}
		get_transactions.return_value = [
			frappe._dict(company="Test", currency="LBP", account_number="53000001", incoming=100, outgoing=None),
			frappe._dict(company="Test", currency="USD", account_number="53010001", incoming=10, outgoing=None),
			frappe._dict(company="Test", currency="QAR", account_number="53000005", incoming=100, outgoing=25),
		]

		_columns, rows = execute({"company": "Test", "date": "2026-09-10"})
		sections = [row for row in rows if row.get("is_section")]
		self.assertEqual(
			[row["section_key"] for row in sections],
			["53000001", "53000002", "53000003", "53000004", "53000005", "53000006", "53000007", "53000008", "53000009", "53000010", "53010001", "53010002", "53010003"],
		)
		section = next(row for row in sections if row["section_key"] == "53000005")

		self.assertEqual(section["currency_name"], "Qatari Riyal")
		self.assertTrue(section["currency_name_ar"])
		self.assertEqual(section["currency_symbol"], "QAR")
		self.assertEqual(section["previous_balance"], 500)
		self.assertEqual(section["current_balance"], 575)
		self.assertEqual(section["opening_date"], "09-09-2026")
		external_usd = next(row for row in sections if row["section_key"] == "53010001")
		self.assertEqual(external_usd["currency_name"], "US Dollar External")
		external_qar = next(row for row in sections if row["section_key"] == "53010002")
		external_sar = next(row for row in sections if row["section_key"] == "53010003")
		self.assertEqual(external_qar["currency_name"], "Qatari Riyal External")
		self.assertEqual(external_sar["currency_name"], "Saudi Riyal External")

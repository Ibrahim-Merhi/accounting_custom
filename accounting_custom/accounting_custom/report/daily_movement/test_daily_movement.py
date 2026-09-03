from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from accounting_custom.accounting_custom.report.daily_movement.daily_movement import (
	company_condition,
	execute,
)


class TestDailyMovement(FrappeTestCase):
	def test_company_condition_supports_one_or_all_except_namaa(self):
		selected = company_condition("gle", frappe._dict(company="Itihad"))
		all_companies = company_condition("gle", frappe._dict(company=None))

		self.assertIn("gle.company = %(company)s", selected)
		self.assertIn("gle.company != %(excluded_company)s", selected)
		self.assertEqual(all_companies, "gle.company != %(excluded_company)s")

	@patch(
		"accounting_custom.accounting_custom.report.daily_movement.daily_movement.get_transactions"
	)
	@patch("accounting_custom.accounting_custom.report.daily_movement.daily_movement.get_balances")
	def test_current_balance_uses_opening_and_visible_movements(self, get_balances, get_transactions):
		get_balances.return_value = {"LBP": 1_000_000, "USD": 500}
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
		get_balances.return_value = {"LBP": 0, "USD": 0}
		get_transactions.return_value = [
			frappe._dict(company="Alpha", currency="LBP", incoming=10, outgoing=None),
			frappe._dict(company="Beta", currency="LBP", incoming=20, outgoing=None),
		]

		_columns, rows = execute({"date": "2026-09-01"})
		company_rows = [row for row in rows if row.get("is_company")]

		self.assertEqual([row["description"] for row in company_rows], ["Company: Alpha", "Company: Beta"])
		self.assertTrue(all(not row.get("voucher_no") for row in company_rows))

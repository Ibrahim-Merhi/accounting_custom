from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from accounting_custom.accounting_custom.report.daily_movement.daily_movement import execute


class TestDailyMovement(FrappeTestCase):
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

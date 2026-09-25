from unittest import TestCase

import frappe

from accounting_custom.accounting_custom.report.account_and_cost_center_report.account_and_cost_center_report import (
	_build_data,
	_get_columns,
)


class TestAccountAndCostCenterReport(TestCase):
	def test_account_precedes_name_and_four_detail_columns(self):
		visible = [column["fieldname"] for column in _get_columns() if not column.get("hidden")]
		self.assertEqual(visible, ["account_number", "account_name", "cost_center", "debit", "credit", "total"])

	def test_groups_all_cost_centers_below_their_account(self):
		rows = [
			frappe._dict(company="Itihad", currency="USD", account="Cash USD - ITHD",
				account_number="53000002", account_name="Cash USD", cost_center="Beirut - ITHD",
				cost_center_name="Beirut", opening_total=10, debit=100, credit=25),
			frappe._dict(company="Itihad", currency="USD", account="Cash USD - ITHD",
				account_number="53000002", account_name="Cash USD", cost_center="Tripoli - ITHD",
				cost_center_name="Tripoli", opening_total=0, debit=20, credit=5),
		]

		data = _build_data(rows)

		self.assertEqual(len(data), 3)
		self.assertEqual(data[0]["account_number"], "53000002")
		self.assertEqual(data[0]["debit"], 120)
		self.assertEqual(data[0]["credit"], 30)
		self.assertEqual(data[0]["total"], 100)
		self.assertEqual([row["cost_center"] for row in data[1:]], ["Beirut - ITHD", "Tripoli - ITHD"])
		self.assertTrue(all(row["parent_row_id"] == data[0]["row_id"] for row in data[1:]))

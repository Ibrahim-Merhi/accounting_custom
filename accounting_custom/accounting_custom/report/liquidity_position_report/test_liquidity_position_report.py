import unittest
from types import SimpleNamespace

from accounting_custom.setup.custom_fields import liquidity_classification_for_account
from accounting_custom.accounting_custom.report.liquidity_position_report.liquidity_position_report import (
	_build_rows,
	_calculate_metrics,
)


class TestLiquidityPositionReport(unittest.TestCase):
	def test_default_account_classifications_follow_specification(self):
		self.assertEqual(liquidity_classification_for_account("13801"), "Excluded")
		self.assertEqual(liquidity_classification_for_account("1380"), "Opening Balance")
		self.assertEqual(liquidity_classification_for_account("5300-01"), "Internal Cash")
		self.assertEqual(liquidity_classification_for_account("5301-02"), "External Cash")
		self.assertEqual(liquidity_classification_for_account("4689"), "Operating Advance")
		self.assertEqual(liquidity_classification_for_account("4699"), "Long-term Advances and Loans")
		self.assertEqual(liquidity_classification_for_account("", "Receivable"), "Receivable")

	def test_liquidity_formulas_and_cost_center_tree(self):
		centers = [
			SimpleNamespace(name="Root", cost_center_name="Root", parent_cost_center="", is_group=1),
			SimpleNamespace(name="Project", cost_center_name="Project", parent_cost_center="Root", is_group=0),
		]
		entries = [
			self.entry("Opening Balance", "2026-01-01", debit=0, credit=1000),
			self.entry("Cash Revenue", "2026-09-10", debit=0, credit=200),
			self.entry("Cash Expense", "2026-09-11", debit=50, credit=0),
			self.entry("Internal Cash", "2026-01-01", debit=1000, credit=0),
			self.entry("Internal Cash", "2026-09-10", debit=200, credit=0),
			self.entry("Internal Cash", "2026-09-11", debit=0, credit=50),
		]
		metrics = _calculate_metrics(entries, "2026-09-01", "2026-09-30")
		rows = _build_rows(centers, metrics, "liquidity")
		project = rows[1]
		self.assertEqual(project["balance"], 1150)
		self.assertEqual(project["available_liquidity"], 1150)
		self.assertEqual(project["check"], 0)
		self.assertEqual(rows[0]["available_liquidity"], 1150)

	def test_movement_reconciles(self):
		centers = [SimpleNamespace(name="Project", cost_center_name="Project", parent_cost_center="", is_group=0)]
		entries = [
			self.entry("Internal Cash", "2026-08-31", debit=100, credit=0),
			self.entry("Internal Cash", "2026-09-02", debit=25, credit=0),
			self.entry("Cash Revenue", "2026-09-02", debit=0, credit=25),
		]
		rows = _build_rows(centers, _calculate_metrics(entries, "2026-09-01", "2026-09-30"), "movement")
		self.assertEqual(rows[0]["opening_liquidity"], 100)
		self.assertEqual(rows[0]["ending_liquidity"], 125)
		self.assertEqual(rows[0]["difference"], 0)

	def test_old_balance_sheet_entries_remain_visible(self):
		entries = [self.entry("Internal Cash", "2024-01-01", debit=750, credit=0)]
		metrics = _calculate_metrics(entries, "2026-09-01", "2026-09-30", "2026-01-01")
		self.assertEqual(metrics["Project"]["internal_cash_end"], 750)
		self.assertEqual(metrics["Project"]["internal_cash_start"], 750)

	@staticmethod
	def entry(classification, date, debit=0, credit=0):
		return SimpleNamespace(
			cost_center="Project", account=classification, posting_date=date,
			debit=debit, credit=credit, classification=classification,
		)


if __name__ == "__main__":
	unittest.main()

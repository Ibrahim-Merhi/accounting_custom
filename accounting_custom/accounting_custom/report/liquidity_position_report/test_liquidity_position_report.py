import unittest
from types import SimpleNamespace

from accounting_custom.setup.custom_fields import liquidity_classification_for_account
from accounting_custom.accounting_custom.report.liquidity_position_report.liquidity_position_report import (
	_apply_print_sections,
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
		self.assertEqual(rows[0]["_print_direct"]["available_liquidity"], 0)
		self.assertEqual(project["_print_direct"]["available_liquidity"], 1150)

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

	def test_any_negative_liquidity_displays_the_note(self):
		centers = [SimpleNamespace(name="Project", cost_center_name="Project", parent_cost_center="", is_group=0)]
		entries = [self.entry("Internal Cash", "2026-09-01", debit=0, credit=0.01)]
		rows = _build_rows(
			centers,
			_calculate_metrics(entries, "2026-09-01", "2026-09-30"),
			"liquidity",
		)
		self.assertEqual(rows[0]["available_liquidity"], -0.01)
		self.assertIn("note", rows[0])

	def test_designated_leaf_centers_become_print_sections(self):
		rows = [
			{"cost_center_id": "HAN000 - HANAYA - ITHD", "cost_center": "HANAYA"},
			{"cost_center_id": "HTY000 - Hayat School - ITHD", "cost_center": "Hayat School"},
			{"cost_center_id": "UDR001 - Undivided Revenue - ITHD", "cost_center": "Undivided Revenue"},
		]
		_apply_print_sections(rows)
		self.assertEqual([row["cost_center"] for row in rows], ["حنايا", "مدرسة الحياة", "إيرادات غير موزعة"])
		self.assertTrue(all(row["print_section"] for row in rows))
		self.assertTrue(all(row["indent"] == 0 and row["parent_cost_center"] is None for row in rows))

	def test_itihad_print_total_contains_only_direct_centers(self):
		rows = [
			{"cost_center_id": "Itihad - ITHD", "cost_center": "الاتحاد", "indent": 0, "is_group": 1},
			{"cost_center_id": "100 - General - ITHD", "cost_center": "عام", "indent": 1, "is_group": 0},
			{"cost_center_id": "DAR - ITHD", "cost_center": "دار القرآن", "indent": 1, "is_group": 1},
			{"cost_center_id": "DAR001 - ITHD", "cost_center": "دار بيروت", "indent": 2, "is_group": 0},
			{"cost_center_id": "HAN000 - HANAYA - ITHD", "cost_center": "HANAYA", "indent": 1, "is_group": 0},
			{"cost_center_id": "500 - Verdun - ITHD", "cost_center": "عقارات", "indent": 1, "is_group": 0},
		]
		_apply_print_sections(rows)
		self.assertEqual(
			[row["cost_center"] for row in rows],
			["الاتحاد", "عام", "عقارات", "دار القرآن", "دار بيروت", "حنايا"],
		)
		self.assertEqual([row["indent"] for row in rows], [0, 1, 1, 0, 1, 0])
		self.assertTrue(rows[3]["print_section"])

	@staticmethod
	def entry(classification, date, debit=0, credit=0):
		return SimpleNamespace(
			cost_center="Project", account=classification, posting_date=date,
			debit=debit, credit=credit, classification=classification,
		)


if __name__ == "__main__":
	unittest.main()

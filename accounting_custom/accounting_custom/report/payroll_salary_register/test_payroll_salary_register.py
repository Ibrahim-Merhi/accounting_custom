from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from accounting_custom.accounting_custom.report.payroll_salary_register.payroll_salary_register import (
	_cost_center_field,
	_columns,
	_blank_zero,
	_build_employee_register_rows,
	_employee_subcategory,
	_deduction_notes,
	_manual_deduction_totals,
	_summary,
	_is_arabic,
	_static_columns,
	_static_register,
)


class TestPayrollSalaryRegister(FrappeTestCase):
	def test_print_language_can_be_forced_to_arabic(self):
		previous = getattr(frappe.flags, "payroll_register_force_arabic", False)
		try:
			frappe.flags.payroll_register_force_arabic = True
			self.assertTrue(_is_arabic())
		finally:
			frappe.flags.payroll_register_force_arabic = previous

	def test_cost_center_columns_are_stable_and_unique(self):
		first = _cost_center_field("100 - General - ITHD")
		second = _cost_center_field("200 - Education - ITHD")
		self.assertEqual(first, _cost_center_field("100 - General - ITHD"))
		self.assertNotEqual(first, second)
		columns = _columns(["100 - General - ITHD"], {"100 - General - ITHD": "عام"})
		self.assertTrue(any(column["fieldname"] == first and column["label"] == "عام" for column in columns))
		self.assertFalse(any(column["fieldname"] == "company" for column in columns))

	def test_administrator_and_forum_reports_include_group_column(self):
		admin_columns = _columns([], {}, "اداريين")
		forum_columns = _columns([], {}, "منتديات")
		self.assertTrue(any(column["fieldname"] == "sub_category" and column["label"] == "الادارة" for column in admin_columns))
		self.assertTrue(any(column["fieldname"] == "sub_category" and column["label"] == "المؤسسة" for column in forum_columns))
		self.assertEqual(_employee_subcategory({"admin_department": "مالية"}, "اداريين"), "مالية")
		self.assertEqual(_employee_subcategory({"forum_institution": "عالم الفرقان"}, "منتديات"), "عالم الفرقان")

	def test_zero_amounts_are_blank(self):
		self.assertIsNone(_blank_zero(0))
		self.assertEqual(_blank_zero(25), 25)

	def test_manual_deductions_are_summed_per_employee_and_company(self):
		run = frappe._dict(manual_deductions=[
			frappe._dict(employee="EMP-1", company="Company A", amount=10),
			frappe._dict(employee="EMP-1", company="Company A", amount=15),
			frappe._dict(employee="EMP-1", company="Company B", amount=5),
		])
		self.assertEqual(_manual_deduction_totals(run), {
			("EMP-1", "Company A"): 25,
			("EMP-1", "Company B"): 5,
		})

	def test_manual_deduction_reasons_are_added_to_notes(self):
		run = frappe._dict(manual_deductions=[
			frappe._dict(employee="EMP-1", company="Company A", amount=25, note="غياب", salary_component="Penalty"),
			frappe._dict(employee="EMP-1", company="Company A", amount=10, note="", salary_component="Other Deduction"),
		])
		self.assertEqual(_deduction_notes(run), {
			("EMP-1", "Company A"): ["غياب: 25", "Other Deduction: 10"],
		})

	def test_same_employee_in_multiple_companies_is_merged(self):
		employees = [
			frappe._dict(employee="MASTER-1", employee_name="Employee", company="A", deductions=25, pay_this_run=300),
			frappe._dict(employee="MASTER-1", employee_name="Employee", company="B", deductions=10, pay_this_run=200),
		]
		allocations = [
			frappe._dict(employee="MASTER-1", company="A", component="Basic Salary", cost_center="CC-A", amount=300),
			frappe._dict(employee="MASTER-1", company="B", component="Basic Salary", cost_center="CC-B", amount=200),
			frappe._dict(employee="MASTER-1", company="A", component="Transportation", cost_center="CC-A", amount=50),
		]
		rows = _build_employee_register_rows(
			employees, allocations, ["CC-A", "CC-B"],
			{"MASTER-1": {"arabic_name": "الموظف", "category": "دعاة"}},
			{("MASTER-1", "A"): 5, ("MASTER-1", "B"): 10},
			{("MASTER-1", "A"): ["حسم: 5"], ("MASTER-1", "B"): ["حسم: 10"]},
			"دعاة",
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["basic_total"], 500)
		self.assertEqual(rows[0]["transportation"], 50)
		self.assertEqual(rows[0]["deduction"], 15)
		self.assertEqual(rows[0]["advance"], 20)
		self.assertEqual(rows[0]["net_salary"], 500)
		self.assertEqual(rows[0][_cost_center_field("CC-A")], 300)
		self.assertEqual(rows[0][_cost_center_field("CC-B")], 200)

	def test_report_summary_accepts_dictionary_rows(self):
		summary = _summary([{"net_salary": 100}, {"net_salary": 250}])
		self.assertEqual(summary[0]["value"], 2)
		self.assertEqual(summary[1]["value"], 350)

	def test_static_mosque_register_uses_payroll_month_only(self):
		run = frappe._dict(payroll_month="September", payroll_year=2026)
		columns, rows, message, _chart, summary = _static_register(run, "مسجد الفرقان")
		self.assertEqual([row["employee_name"] for row in rows], ["الشيخ علاء العماري", "عبيدة الأحمد"])
		self.assertEqual(sum(row["total"] for row in rows), 710)
		self.assertIn("2026", message)
		self.assertEqual(summary[1]["value"], 710)
		self.assertFalse(any(column["fieldname"] in ("basic_lbp", "additional_usd") for column in columns))

	def test_static_columns_follow_each_mosque_layout(self):
		columns = _static_columns(("basic_usd", "family_allowance", "deduction"))
		fields = [column["fieldname"] for column in columns]
		self.assertEqual(fields, ["row_number", "employee_name", "basic_usd", "family_allowance", "deduction", "total", "notes"])

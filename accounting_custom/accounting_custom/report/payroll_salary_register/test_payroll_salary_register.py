from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from accounting_custom.accounting_custom.report.payroll_salary_register.payroll_salary_register import (
	_cost_center_field,
	_columns,
	_blank_zero,
	_employee_subcategory,
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

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from accounting_custom.accounting.payroll import validate_payroll_manual_deductions


class TestPayrollManualDeduction(FrappeTestCase):
	@patch("accounting_custom.accounting.payroll.frappe.db.get_value")
	def test_valid_deduction_for_payroll_employee(self, get_value):
		get_value.side_effect = lambda doctype, name, field: "Itihad" if doctype == "Employee" else "Deduction"
		doc = frappe._dict(company="Itihad", employees=[frappe._dict(employee="PAY-EMP-1-ITHD")], custom_manual_deductions=[
			frappe._dict(idx=1, employee="PAY-EMP-1-ITHD", salary_component="Manual Deduction", amount=25)
		])
		validate_payroll_manual_deductions(doc)

	def test_rejects_employee_outside_payroll_run(self):
		doc = frappe._dict(company="Itihad", employees=[], custom_manual_deductions=[
			frappe._dict(idx=1, employee="PAY-EMP-1-ITHD", salary_component="Manual Deduction", amount=25)
		])
		with self.assertRaises(frappe.ValidationError):
			validate_payroll_manual_deductions(doc)

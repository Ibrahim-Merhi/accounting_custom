from unittest import TestCase
from unittest.mock import patch

import frappe

from accounting_custom.accounting.consolidated_payslip import _deduction_reasons


class TestConsolidatedPayslip(TestCase):
	@patch(
		"accounting_custom.accounting.consolidated_payslip._additional_salary_reasons",
		return_value={"ADD-1": "Late attendance"},
	)
	@patch("accounting_custom.accounting.consolidated_payslip.frappe.get_all")
	def test_deduction_reasons_use_notes_and_component_fallback(self, get_all, _reasons):
		get_all.return_value = [
			frappe._dict(salary_component="Other Deduction", amount=25, additional_salary="ADD-1"),
			frappe._dict(salary_component="Income Tax", amount=10, additional_salary=None),
			frappe._dict(salary_component="Other Deduction", amount=5, additional_salary="ADD-1"),
		]

		result = _deduction_reasons(["SAL-1"], "USD")

		self.assertEqual(result, "Late attendance: 30 USD\nIncome Tax: 10 USD")

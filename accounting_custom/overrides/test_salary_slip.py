from unittest.mock import PropertyMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from accounting_custom.overrides.salary_slip import CustomSalarySlip


class TestCustomSalarySlip(FrappeTestCase):
	def test_structure_selection_uses_actual_payroll_start(self):
		slip = CustomSalarySlip({
			"doctype": "Salary Slip", "employee": "EMP-1",
			"start_date": "2026-09-01", "end_date": "2026-09-30",
			"actual_start_date": "2026-09-01", "payroll_frequency": "Monthly",
		})
		with patch.object(CustomSalarySlip, "actual_start_date", new_callable=PropertyMock, return_value="2026-09-01"), patch.object(
			frappe.db, "sql", return_value=[["Managed-EMP-1-R3"]]
		) as query:
			self.assertEqual(slip.check_sal_struct(), "Managed-EMP-1-R3")
		params = query.call_args.args[1]
		self.assertEqual(str(params["cutoff"]), "2026-09-01")
		self.assertEqual(params["payroll_frequency"], "Monthly")

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from accounting_custom.accounting_custom.doctype.payroll_cost_center_allocation.payroll_cost_center_allocation import (
	PayrollCostCenterAllocation,
)


class FakeAssignment:
	def __init__(self):
		self.payroll_cost_centers = [SimpleNamespace(cost_center="Old CC", percentage=100)]
		self.flags = SimpleNamespace(ignore_permissions=False)
		self.save_count = 0

	def set(self, fieldname, value):
		setattr(self, fieldname, value)

	def append(self, fieldname, value):
		getattr(self, fieldname).append(SimpleNamespace(**value))

	def save(self):
		self.save_count += 1


class TestPayrollCostCenterAllocation(TestCase):
	@patch("accounting_custom.accounting_custom.doctype.payroll_cost_center_allocation.payroll_cost_center_allocation.frappe.get_doc")
	def test_applies_all_cost_centers_in_one_assignment_save(self, get_doc):
		assignment = FakeAssignment()
		get_doc.return_value = assignment
		doc = SimpleNamespace(salary_structure_assignment="SSA-1")

		PayrollCostCenterAllocation.apply_allocations(doc, [
			{"cost_center": "CC-A", "percentage": 60},
			{"cost_center": "CC-B", "percentage": 40},
		])

		self.assertEqual(assignment.save_count, 1)
		self.assertTrue(assignment.flags.ignore_permissions)
		self.assertEqual(
			[(row.cost_center, row.percentage) for row in assignment.payroll_cost_centers],
			[("CC-A", 60), ("CC-B", 40)],
		)

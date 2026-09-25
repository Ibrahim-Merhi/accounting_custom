import frappe
from frappe.tests.utils import FrappeTestCase


class TestEmployeePositionHistory(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_left_position_moves_to_read_only_history(self):
		frappe.set_user("Administrator")
		employee = frappe.get_doc({
			"doctype": "Employee", "first_name": "Position History Test", "gender": "Male",
			"date_of_birth": "1990-01-01", "date_of_joining": "2025-01-01",
			"status": "Active", "company": "Itihad",
			"custom_branches": [
				{"company": "Itihad", "branch": "Tripoli", "from_date": "2026-01-01"},
				{"company": "Itihad", "branch": "Tripoli", "from_date": "2025-01-01", "left_position": 1, "leaving_date": "2025-12-31"},
			],
		}).insert(ignore_permissions=True)
		self.assertEqual(len(employee.custom_branches), 1)
		self.assertEqual(len(employee.custom_past_positions), 1)
		self.assertEqual(str(employee.custom_past_positions[0].to_date), "2025-12-31")

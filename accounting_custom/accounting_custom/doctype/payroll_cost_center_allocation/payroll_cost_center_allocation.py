import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PayrollCostCenterAllocation(Document):
	def validate(self):
		if not self.allocations:
			frappe.throw(_("Add at least one payroll cost center."))
		assignment = frappe.db.get_value(
			"Salary Structure Assignment", self.salary_structure_assignment,
			["employee", "company", "docstatus", "from_date"], as_dict=True,
		)
		if not assignment or assignment.docstatus != 1:
			frappe.throw(_("Select a submitted Salary Structure Assignment."))
		if assignment.employee != self.employee or assignment.company != self.company:
			frappe.throw(_("Salary Structure Assignment must match the employee and company."))
		if self.effective_date < assignment.from_date:
			frappe.throw(_("Effective Date cannot precede the Salary Structure Assignment."))
		seen = set()
		self.total_percentage = 0
		for row in self.allocations:
			if row.cost_center in seen:
				frappe.throw(_("Cost Center {0} is duplicated.").format(row.cost_center))
			seen.add(row.cost_center)
			if frappe.db.get_value("Cost Center", row.cost_center, "company") != self.company:
				frappe.throw(_("Cost Center {0} does not belong to the selected company.").format(row.cost_center))
			self.total_percentage += flt(row.percentage)
		if self.total_percentage != 100:
			frappe.throw(_("Payroll cost-center allocation must total 100%."))

	def before_submit(self):
		assignment = frappe.get_doc("Salary Structure Assignment", self.salary_structure_assignment)
		self.previous_allocations = json.dumps([
			{"cost_center": row.cost_center, "percentage": row.percentage}
			for row in assignment.payroll_cost_centers
		])

	def on_submit(self):
		self.apply_allocations([
			{"cost_center": row.cost_center, "percentage": row.percentage}
			for row in self.allocations
		])

	def on_cancel(self):
		self.apply_allocations(json.loads(self.previous_allocations or "[]"))

	def apply_allocations(self, allocations):
		assignment = frappe.get_doc("Salary Structure Assignment", self.salary_structure_assignment)
		assignment.set("payroll_cost_centers", [])
		for row in allocations:
			assignment.append("payroll_cost_centers", row)
		assignment.flags.ignore_permissions = True
		assignment.save()

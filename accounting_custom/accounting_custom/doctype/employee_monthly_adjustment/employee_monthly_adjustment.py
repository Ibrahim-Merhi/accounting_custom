import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class EmployeeMonthlyAdjustment(Document):
	def validate(self):
		if not self.deductions:
			frappe.throw(_("Add at least one monthly deduction or note."))
		self.total_deductions = 0
		for row in self.deductions:
			if frappe.db.get_value("Salary Component", row.salary_component, "type") != "Deduction":
				frappe.throw(_("Row {0}: Salary Component must be a deduction.").format(row.idx))
			if flt(row.amount) <= 0:
				frappe.throw(_("Row {0}: Amount must be greater than zero.").format(row.idx))
			self.total_deductions += flt(row.amount)

	def on_submit(self):
		created = []
		for row in self.deductions:
			doc = frappe.get_doc({
				"doctype": "Additional Salary", "employee": self.employee,
				"company": self.company, "payroll_date": self.payroll_date,
				"salary_component": row.salary_component, "amount": row.amount,
				"ref_doctype": self.doctype, "ref_docname": self.name,
			})
			doc.insert(ignore_permissions=True)
			doc.flags.ignore_permissions = True
			doc.submit()
			created.append(doc.name)
		self.db_set("additional_salary_documents", "\n".join(created))

	def on_cancel(self):
		for name in (self.additional_salary_documents or "").splitlines():
			if frappe.db.exists("Additional Salary", name):
				doc = frappe.get_doc("Additional Salary", name)
				if doc.docstatus == 1:
					doc.flags.ignore_permissions = True
					doc.cancel()

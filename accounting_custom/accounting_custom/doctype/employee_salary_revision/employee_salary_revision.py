import frappe
from frappe import _
from frappe.model.document import Document


class EmployeeSalaryRevision(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw(_("Salary revisions are immutable."))

	def on_trash(self):
		if not frappe.flags.in_uninstall:
			frappe.throw(_("Salary revisions cannot be deleted."))

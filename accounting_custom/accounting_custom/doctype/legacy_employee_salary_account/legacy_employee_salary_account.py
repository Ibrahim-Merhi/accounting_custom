import frappe
from frappe import _
from frappe.model.document import Document


class LegacyEmployeeSalaryAccount(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw(_("Legacy salary account archives are immutable."))

	def on_trash(self):
		if not frappe.flags.in_uninstall:
			frappe.throw(_("Legacy salary account archives cannot be deleted."))

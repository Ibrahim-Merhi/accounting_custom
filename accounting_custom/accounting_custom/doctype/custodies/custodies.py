import frappe
from frappe import _
from frappe.model.document import Document


class Custodies(Document):
	def validate(self):
		account = frappe.db.get_value(
			"Account", self.account,
			["company", "account_type", "is_group", "disabled"], as_dict=True,
		)
		if not account or account.company != self.company:
			frappe.throw(_("The custody account must belong to the selected company."))
		if account.is_group or account.disabled:
			frappe.throw(_("Select an enabled ledger account for this custody."))
		if account.account_type != "Receivable":
			frappe.throw(_("The custody account must be a Receivable account."))

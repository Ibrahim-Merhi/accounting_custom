import frappe
from frappe import _
from frappe.model.document import Document


class CollectorProfile(Document):
	def validate(self):
		duplicate = frappe.db.exists(
			"Collector Profile", {"user": self.user, "company": self.company, "name": ["!=", self.name]}
		)
		if duplicate:
			frappe.throw(_("A Collector Profile already exists for this user and company."))
		donor_account = frappe.db.get_value(
			"Account", self.default_donor_account, ["company", "is_group"], as_dict=True
		)
		if not donor_account or donor_account.company != self.company or donor_account.is_group:
			frappe.throw(_("Default Donor Account must be a ledger account for the selected company."))
		seen = set()
		for row in self.custody_accounts:
			if row.currency in seen:
				frappe.throw(_("Only one custody account is allowed per currency."))
			seen.add(row.currency)
			details = frappe.db.get_value(
				"Account", row.account, ["company", "account_currency", "is_group"], as_dict=True
			)
			if not details or details.company != self.company:
				frappe.throw(_("Custody Account must belong to the selected company."))
			if details.is_group:
				frappe.throw(_("Custody Account cannot be a group account."))
			if details.account_currency != row.currency:
				frappe.throw(_("Custody Account currency must match the row currency."))

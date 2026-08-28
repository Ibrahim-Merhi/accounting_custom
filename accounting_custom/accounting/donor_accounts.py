import frappe
from frappe import _


def get_donor_account(donor, company):
	rows = frappe.get_all(
		"Party Account",
		filters={
			"parenttype": "Donor",
			"parentfield": "custom_accounts",
			"parent": donor,
			"company": company,
		},
		fields=["account"],
		limit_page_length=2,
	)
	if not rows or not rows[0].account:
		frappe.throw(_("Donor {0} is not configured for company {1}.").format(donor, company))
	if len(rows) > 1:
		frappe.throw(_("Donor {0} has more than one account configured for company {1}.").format(donor, company))
	return rows[0].account

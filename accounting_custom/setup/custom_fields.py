import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


DONOR_FIELDS = [
	{
		"fieldname": "custom_accounts_section",
		"label": "Accounts Section",
		"fieldtype": "Section Break",
		"insert_after": "contact_html",
		"module": "Accounting Custom",
	},
	{
		"fieldname": "custom_accounts",
		"label": "Accounts",
		"fieldtype": "Table",
		"options": "Party Account",
		"insert_after": "custom_accounts_section",
		"module": "Accounting Custom",
	},
]


def ensure_donor_account_fields():
	if not frappe.db.exists("DocType", "Donor"):
		return
	existing_fields = {field.fieldname for field in frappe.get_meta("Donor").fields}
	for definition in DONOR_FIELDS:
		if definition["fieldname"] not in existing_fields:
			create_custom_field("Donor", definition)
			existing_fields.add(definition["fieldname"])
	frappe.clear_cache(doctype="Donor")

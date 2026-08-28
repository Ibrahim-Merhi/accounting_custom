import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


CUSTOM_FIELDS = {
	"Branch": [
		{
			"fieldname": "custom_company", "label": "Company", "fieldtype": "Link",
			"options": "Company", "insert_after": "branch",
		},
	],
	"Donor": [
		{
			"fieldname": "custom_accounts_section", "label": "Accounts Section",
			"fieldtype": "Section Break", "insert_after": "contact_html",
		},
		{
			"fieldname": "custom_accounts", "label": "Accounts", "fieldtype": "Table",
			"options": "Party Account", "insert_after": "custom_accounts_section",
		},
	],
	"Journal Entry": [
		{
			"fieldname": "custom_branch", "label": "Branch", "fieldtype": "Link",
			"options": "Branch", "insert_after": "company",
		},
	],
	"GL Entry": [
		{
			"fieldname": "custom_branch", "label": "Branch", "fieldtype": "Link",
			"options": "Branch", "insert_after": "company", "read_only": 1,
		},
	],
}


def ensure_custom_fields():
	for doctype, definitions in CUSTOM_FIELDS.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		existing = {field.fieldname for field in frappe.get_meta(doctype).fields}
		for definition in definitions:
			if definition["fieldname"] not in existing:
				create_custom_field(doctype, {**definition, "module": "Accounting Custom"})
				existing.add(definition["fieldname"])
		frappe.clear_cache(doctype=doctype)


def ensure_donor_account_fields():
	ensure_custom_fields()

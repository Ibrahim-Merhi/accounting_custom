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
	"Accounting Payment Entry": [
		{
			"fieldname": "custom_accounting_rows_copy", "label": "Accounting Rows",
			"fieldtype": "Table", "options": "Accounting Payment Detail",
			"insert_after": "accounts_section", "reqd": 1,
		},
	],
	"Journal Entry": [
		{
			"fieldname": "custom_branch", "label": "Branch (Legacy)", "fieldtype": "Link",
			"options": "Branch", "insert_after": "company", "hidden": 1,
		},
	],
	"Journal Entry Account": [
		{
			"fieldname": "custom_branch", "label": "Branch", "fieldtype": "Link",
			"options": "Branch", "insert_after": "cost_center", "in_list_view": 1, "reqd": 1,
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
			else:
				custom_field = frappe.db.exists("Custom Field", f"{doctype}-{definition['fieldname']}")
				if custom_field:
					values = {key: value for key, value in definition.items() if key != "fieldname"}
					frappe.db.set_value("Custom Field", custom_field, values, update_modified=False)
		frappe.clear_cache(doctype=doctype)
	migrate_journal_entry_branches()
	migrate_accounting_payment_rows()


def migrate_journal_entry_branches():
	if not (frappe.db.has_column("Journal Entry", "custom_branch") and frappe.db.has_column("Journal Entry Account", "custom_branch")):
		return
	frappe.db.sql("""
		update `tabJournal Entry Account` account
		inner join `tabJournal Entry` journal on journal.name = account.parent
		set account.custom_branch = journal.custom_branch
		where ifnull(account.custom_branch, '') = ''
		and ifnull(journal.custom_branch, '') != ''
	""")


def migrate_accounting_payment_rows():
	canonical_fieldname = "custom_accounting_rows_copy"
	canonical_name = "Accounting Payment Entry-custom_accounting_rows_copy"
	if not frappe.db.exists("Custom Field", canonical_name):
		return

	duplicate_fields = frappe.get_all(
		"Custom Field",
		filters={
			"dt": "Accounting Payment Entry",
			"fieldname": ["like", "custom_accounting_rows_copy%"],
			"fieldtype": "Table",
			"options": "Accounting Payment Detail",
		},
		fields=["name", "fieldname"],
	)
	legacy_fieldnames = ["accounts", "accounting_rows"]
	legacy_fieldnames.extend(
		field.fieldname for field in duplicate_fields if field.name != canonical_name
	)
	for fieldname in legacy_fieldnames:
		frappe.db.sql(
			"""
			update `tabAccounting Payment Detail`
			set parentfield = %s
			where parenttype = 'Accounting Payment Entry' and parentfield = %s
			""",
			(canonical_fieldname, fieldname),
		)

	for field in duplicate_fields:
		if field.name != canonical_name:
			frappe.db.set_value(
				"Custom Field", field.name,
				{"hidden": 1, "reqd": 0, "label": "Accounting Rows Copy (Legacy)"},
				update_modified=False,
			)

	frappe.db.set_value(
		"Custom Field", canonical_name,
		{"hidden": 0, "reqd": 1, "label": "Accounting Rows"},
		update_modified=False,
	)
	frappe.clear_cache(doctype="Accounting Payment Entry")


def ensure_donor_account_fields():
	ensure_custom_fields()

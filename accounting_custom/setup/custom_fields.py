import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


CUSTOM_FIELDS = {
	"Account": [
		{
			"fieldname": "custom_account_name_arabic", "label": "Arabic Account Name",
			"fieldtype": "Data", "insert_after": "account_name", "in_list_view": 1,
		},
		{
			"fieldname": "custom_arabic_name_source", "label": "Arabic Name Source",
			"fieldtype": "Data", "insert_after": "custom_account_name_arabic", "hidden": 1,
			"read_only": 1,
		},
		{
			"fieldname": "custom_parent_account_arabic", "label": "Arabic Parent Account",
			"fieldtype": "Data", "insert_after": "parent_account",
			"fetch_from": "parent_account.custom_account_name_arabic",
		},
	],
	"Company": [
		{
			"fieldname": "custom_company_name_arabic", "label": "Arabic Company Name",
			"fieldtype": "Data", "insert_after": "company_name", "in_list_view": 1,
		},
		{
			"fieldname": "custom_arabic_name_source", "label": "Arabic Name Source",
			"fieldtype": "Data", "insert_after": "custom_company_name_arabic", "hidden": 1,
			"read_only": 1,
		},
	],
	"Cost Center": [
		{
			"fieldname": "custom_cost_center_name_arabic", "label": "Arabic Cost Center Name",
			"fieldtype": "Data", "insert_after": "cost_center_name", "in_list_view": 1,
		},
		{
			"fieldname": "custom_arabic_name_source", "label": "Arabic Name Source",
			"fieldtype": "Data", "insert_after": "custom_cost_center_name_arabic", "hidden": 1,
			"read_only": 1,
		},
		{
			"fieldname": "custom_parent_cost_center_arabic", "label": "Arabic Parent Cost Center",
			"fieldtype": "Data", "insert_after": "parent_cost_center", "read_only": 0,
			"fetch_from": "parent_cost_center.custom_cost_center_name_arabic",
		},
		{
			"fieldname": "custom_company_name_arabic", "label": "Arabic Company Name",
			"fieldtype": "Data", "insert_after": "company", "read_only": 0,
			"fetch_from": "company.custom_company_name_arabic",
		},
	],
	"Branch": [
		{
			"fieldname": "custom_branch_name_arabic", "label": "Arabic Branch Name",
			"fieldtype": "Data", "insert_after": "branch", "in_list_view": 1,
		},
		{
			"fieldname": "custom_company", "label": "Company", "fieldtype": "Link",
			"options": "Company", "insert_after": "custom_branch_name_arabic",
		},
	],
	"Donor": [
		{
			"fieldname": "custom_phone_numper", "label": "Phone Number", "fieldtype": "Data",
			"insert_after": "donor_name", "in_list_view": 1, "in_standard_filter": 1, "reqd": 0,
		},
		{
			"fieldname": "custom_accounts_section", "label": "Accounts Section",
			"fieldtype": "Section Break", "insert_after": "contact_html",
		},
		{
			"fieldname": "custom_accounts", "label": "Accounts", "fieldtype": "Table",
			"options": "Party Account", "insert_after": "custom_accounts_section",
		},
	],
	"Employee": [
		{
			"fieldname": "custom_master_employee", "label": "Master Employee", "fieldtype": "Link",
			"options": "Employee", "insert_after": "employee_number", "hidden": 1, "read_only": 1, "no_copy": 1,
		},
		{
			"fieldname": "custom_is_payroll_identity", "label": "Payroll Company Identity", "fieldtype": "Check",
			"insert_after": "custom_master_employee", "hidden": 1, "read_only": 1, "no_copy": 1,
		},
		{
			"fieldname": "custom_accounting_assignments_section", "label": "Company and Accounting Details",
			"fieldtype": "Section Break", "insert_after": "branch",
		},
		{
			"fieldname": "custom_branches", "label": "Company and Accounting Details", "fieldtype": "Table",
			"options": "Employee Branch Assignment", "insert_after": "custom_accounting_assignments_section", "reqd": 0,
		},
		{
			"fieldname": "custom_past_positions_section", "label": "Past Positions",
			"fieldtype": "Section Break", "insert_after": "custom_branches", "collapsible": 1,
		},
		{
			"fieldname": "custom_past_positions", "label": "Past Positions", "fieldtype": "Table",
			"options": "Employee Past Position", "insert_after": "custom_past_positions_section", "read_only": 1,
		},
		{
			"fieldname": "custom_secure_salary_profile", "label": "Salary Profile",
			"fieldtype": "HTML", "insert_after": "salary_information",
		},
	],
	"Payroll Entry": [
		{
			"fieldname": "custom_manual_deductions_section", "label": "Manual Deductions",
			"fieldtype": "Section Break", "insert_after": "employees", "collapsible": 1,
		},
		{
			"fieldname": "custom_manual_deductions", "label": "Employee Manual Deductions",
			"fieldtype": "Table", "options": "Payroll Manual Deduction",
			"insert_after": "custom_manual_deductions_section",
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
			"options": "Branch", "insert_after": "cost_center", "in_list_view": 1, "reqd": 0,
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
	remove_obsolete_payment_entry_fields()
	remove_obsolete_supplier_company_field()
	remove_legacy_donation_requirements()
	configure_quick_donor_creation()
	configure_employee_accounting_profile()
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
	migrate_employee_positions()
	remove_obsolete_employee_assignment_fields()
	backfill_arabic_branch_names()


def migrate_employee_positions():
	"""Backfill current position dimensions and start dates."""
	if not (
		frappe.get_meta("Employee").has_field("custom_branches")
		and frappe.db.table_exists("Employee Branch Assignment")
	):
		return
	for employee in frappe.get_all(
		"Employee",
		fields=["name", "company", "branch", "department", "designation", "employment_type", "date_of_joining", "custom_is_payroll_identity"],
	):
		if employee.custom_is_payroll_identity:
			continue
		rows = frappe.get_all(
			"Employee Branch Assignment",
			filters={"parent": employee.name, "parenttype": "Employee"},
			fields=["name", "company", "branch", "department", "designation", "employment_type", "from_date"],
			order_by="idx asc",
		)
		if not rows:
			branch = employee.branch or ensure_unassigned_branch(employee.company)
			branch_company = frappe.db.get_value("Branch", branch, "custom_company")
			frappe.get_doc({
				"doctype": "Employee Branch Assignment", "parent": employee.name,
				"parenttype": "Employee", "parentfield": "custom_branches",
				"company": branch_company or employee.company, "branch": branch,
				"department": employee.department, "designation": employee.designation,
				"employment_type": employee.employment_type, "from_date": employee.date_of_joining,
			}).db_insert()
			rows = frappe.get_all(
				"Employee Branch Assignment", filters={"parent": employee.name, "parenttype": "Employee"},
				fields=["name", "company", "branch", "department", "designation", "employment_type", "from_date"],
			)
		for row in rows:
			company = row.company or frappe.db.get_value("Branch", row.branch, "custom_company") or employee.company
			frappe.db.set_value("Employee Branch Assignment", row.name, {
				"company": company, "department": row.department or employee.department,
				"designation": row.designation or employee.designation,
				"employment_type": row.employment_type or employee.employment_type,
				"from_date": row.from_date or employee.date_of_joining,
			}, update_modified=False)
		from accounting_custom.accounting.employee_profile import sync_company_payroll_identities
		sync_company_payroll_identities(frappe.get_doc("Employee", employee.name))


def remove_obsolete_employee_assignment_fields():
	"""Archive legacy salary accounts securely before removing the HR-visible table field."""
	fieldname = "Employee-custom_salary_accounts"
	if not frappe.db.exists("Custom Field", fieldname):
		return
	if frappe.db.table_exists("Employee Salary Account") and frappe.db.table_exists("Legacy Employee Salary Account"):
		for row in frappe.get_all("Employee Salary Account", fields=["parent", "company", "account"]):
			if not row.parent or not row.account:
				continue
			company = row.company or frappe.db.get_value("Account", row.account, "company")
			if frappe.db.exists("Legacy Employee Salary Account", {"employee": row.parent, "account": row.account, "company": company}):
				continue
			frappe.get_doc({
				"doctype": "Legacy Employee Salary Account", "employee": row.parent,
				"employee_name": frappe.db.get_value("Employee", row.parent, "employee_name"),
				"company": company, "account": row.account, "migrated_on": frappe.utils.now(),
			}).insert(ignore_permissions=True)
	frappe.delete_doc("Custom Field", fieldname, ignore_permissions=True)
	frappe.clear_cache(doctype="Employee")


def backfill_arabic_branch_names():
	if not frappe.db.has_column("Branch", "custom_branch_name_arabic"):
		return
	translations = {
		"beirut": "بيروت",
		"tripoli": "طرابلس",
		"saidon": "صيدا",
		"sidon": "صيدا",
		"saida": "صيدا",
		"bekaa": "البقاع",
		"montada": "المنتدى",
		"itihad": "الاتحاد",
	}
	for branch in frappe.get_all(
		"Branch", fields=["name", "branch", "custom_branch_name_arabic"]
	):
		if branch.custom_branch_name_arabic:
			continue
		english_name = branch.branch or branch.name
		parts = [part.strip() for part in english_name.split(" - ")]
		translated = [translations.get(part.lower(), part) for part in parts]
		arabic_name = " - ".join(translated)
		if arabic_name != english_name:
			frappe.db.set_value(
				"Branch", branch.name, "custom_branch_name_arabic", arabic_name,
				update_modified=False,
			)


def remove_obsolete_payment_entry_fields():
	fieldname = "Payment Entry-custom_amount_in_words_arabic"
	if frappe.db.exists("Custom Field", fieldname):
		frappe.delete_doc("Custom Field", fieldname, ignore_permissions=True)
		frappe.clear_cache(doctype="Payment Entry")


def remove_legacy_donation_requirements():
	"""Legacy header fields are hidden; payment requirements belong to child rows."""
	if not frappe.db.exists("DocType", "Donation Entry"):
		return
	legacy_fields = (
		"mode_of_payment", "cost_center", "currency", "donation_amount",
		"exchange_rate", "received_in_account", "reference_no", "reference_date",
	)
	frappe.db.delete(
		"Property Setter",
		{
			"doc_type": "Donation Entry",
			"field_name": ["in", legacy_fields],
			"property": "reqd",
		},
	)
	frappe.clear_cache(doctype="Donation Entry")


def configure_quick_donor_creation():
	if not frappe.db.exists("DocType", "Donor"):
		return
	for fieldname in ("donor_type", "professional_title", "email", "custom_phone_numper"):
		property_name = f"Donor-{fieldname}-reqd"
		if frappe.db.exists("Property Setter", property_name):
			frappe.db.set_value(
				"Property Setter",
				property_name,
				{"value": "0", "property_type": "Check"},
				update_modified=False,
			)
		else:
			frappe.make_property_setter({
				"doctype": "Donor", "fieldname": fieldname, "property": "reqd",
				"value": "0", "property_type": "Check",
			})
	frappe.clear_cache(doctype="Donor")


def configure_employee_accounting_profile():
	"""Use the Working Branches table while retaining the standard primary branch internally."""
	if not frappe.db.exists("DocType", "Employee"):
		return
	for fieldname in (
		"company_details_section", "branch", "grade", "ctc", "salary_currency",
		"salary_mode", "payroll_cost_center",
	):
		property_name = f"Employee-{fieldname}-hidden"
		values = {"value": "1", "property_type": "Check"}
		if frappe.db.exists("Property Setter", property_name):
			frappe.db.set_value("Property Setter", property_name, values, update_modified=False)
		else:
			frappe.make_property_setter({
				"doctype": "Employee", "fieldname": fieldname, "property": "hidden",
				**values,
			})
	frappe.clear_cache(doctype="Employee")


def remove_obsolete_supplier_company_field():
	fieldname = "Supplier-custom_company"
	if frappe.db.exists("Custom Field", fieldname):
		frappe.delete_doc("Custom Field", fieldname, ignore_permissions=True)
		frappe.clear_cache(doctype="Supplier")


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


def ensure_unassigned_branch(company):
	"""Create an explicit reviewable placeholder instead of guessing an employee branch."""
	branch_name = f"Unassigned - {company}"
	if frappe.db.exists("Branch", branch_name):
		if not frappe.db.get_value("Branch", branch_name, "custom_company"):
			frappe.db.set_value("Branch", branch_name, "custom_company", company, update_modified=False)
		return branch_name
	branch = frappe.get_doc({
		"doctype": "Branch", "branch": branch_name, "custom_company": company,
		"custom_branch_name_arabic": f"غير محدد - {company}",
	})
	branch.insert(ignore_permissions=True)
	return branch.name

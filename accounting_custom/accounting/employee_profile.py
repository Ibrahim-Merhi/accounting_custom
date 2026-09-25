import frappe
from frappe import _


def validate_employee_accounting_profile(doc, method=None):
	_validate_unique_rows(doc, "custom_branches", "branch", _("Branch"))
	_validate_unique_rows(doc, "custom_salary_accounts", "account", _("Salary Account"))

	for row in doc.get("custom_branches") or []:
		branch_company = frappe.db.get_value("Branch", row.branch, "custom_company")
		if branch_company and branch_company != doc.company:
			frappe.throw(_("Row {0}: Branch {1} does not belong to company {2}.").format(row.idx, row.branch, doc.company))

	for row in doc.get("custom_salary_accounts") or []:
		account = frappe.db.get_value(
			"Account", row.account, ["company", "is_group", "disabled"], as_dict=True
		)
		if not account or account.company != doc.company:
			frappe.throw(_("Row {0}: Salary Account {1} does not belong to company {2}.").format(row.idx, row.account, doc.company))
		if account.is_group or account.disabled:
			frappe.throw(_("Row {0}: Salary Account {1} must be an enabled ledger account.").format(row.idx, row.account))


def _validate_unique_rows(doc, table_field, value_field, label):
	seen = set()
	for row in doc.get(table_field) or []:
		value = row.get(value_field)
		if not value:
			continue
		if value in seen:
			frappe.throw(_("{0} {1} is entered more than once.").format(label, value))
		seen.add(value)

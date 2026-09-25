import frappe
from frappe import _


ASSIGNMENT_FIELDS = ("company", "branch", "department", "designation", "employment_type", "account")


def validate_employee_accounting_profile(doc, method=None):
	assignments = [row for row in (doc.get("custom_branches") or []) if row.company and row.branch]
	if not assignments:
		frappe.throw(_("Please add at least one Company and Accounting Details row."))

	_validate_unique_assignments(assignments)
	for row in assignments:
		branch_company = frappe.db.get_value("Branch", row.branch, "custom_company")
		if branch_company and branch_company != row.company:
			frappe.throw(_("Row {0}: Branch {1} does not belong to company {2}.").format(row.idx, row.branch, row.company))

		if row.department:
			department_company = frappe.db.get_value("Department", row.department, "company")
			if department_company and department_company != row.company:
				frappe.throw(_("Row {0}: Department {1} does not belong to company {2}.").format(row.idx, row.department, row.company))

		if row.account:
			account = frappe.db.get_value("Account", row.account, ["company", "is_group", "disabled"], as_dict=True)
			if not account or account.company != row.company:
				frappe.throw(_("Row {0}: Salary Account {1} does not belong to company {2}.").format(row.idx, row.account, row.company))
			if account.is_group or account.disabled:
				frappe.throw(_("Row {0}: Salary Account {1} must be an enabled ledger account.").format(row.idx, row.account))

	# Standard HRMS fields remain populated internally for reports, payroll, and permissions.
	primary = next((row for row in assignments if not row.left_position), assignments[0])
	doc.company = primary.company
	doc.branch = primary.branch
	doc.department = primary.department
	doc.designation = primary.designation
	doc.employment_type = primary.employment_type


def _validate_unique_assignments(assignments):
	seen = set()
	for row in assignments:
		key = tuple(row.get(fieldname) or "" for fieldname in ASSIGNMENT_FIELDS)
		if key in seen:
			frappe.throw(_("Row {0}: This company, work assignment, and salary account is duplicated.").format(row.idx))
		seen.add(key)

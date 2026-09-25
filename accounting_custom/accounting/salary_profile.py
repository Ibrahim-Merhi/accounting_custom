import frappe
from frappe import _


SALARY_ROLES = {"Accounts Manager"}


def check_salary_access():
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles()).intersection(SALARY_ROLES):
		frappe.throw(_("You are not permitted to access salary information."), frappe.PermissionError)


@frappe.whitelist()
def get_salary_profile_summary(employee):
	check_salary_access()
	profile = frappe.db.get_value(
		"Employee Salary Profile",
		{"employee": employee},
		["name", "effective_date", "last_action_date", "basic_salary", "transportation", "family_allowance", "total_salary", "latest_revision"],
		as_dict=True,
	)
	if not profile:
		return {"exists": False}
	profile.exists = True
	profile.revision_count = frappe.db.count("Employee Salary Revision", {"salary_profile": profile.name})
	payroll_employees = frappe.get_all("Employee", filters={"custom_master_employee": employee}, pluck="name")
	payroll_employees.append(employee)
	profile.salary_slips = frappe.get_all(
		"Salary Slip", filters={"employee": ["in", payroll_employees], "docstatus": ["<", 2]},
		fields=["name", "company", "start_date", "end_date", "currency", "net_pay", "docstatus"],
		order_by="end_date desc", limit=5,
	)
	return profile


@frappe.whitelist()
def get_revision_history(profile):
	check_salary_access()
	return frappe.get_all(
		"Employee Salary Revision", filters={"salary_profile": profile},
		fields=["name", "revision_number", "effective_from", "effective_to", "action_date", "basic_salary", "transportation", "family_allowance", "total_salary", "changed_by", "change_summary"],
		order_by="revision_number desc",
	)

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
	profile_doc = frappe.get_doc("Employee Salary Profile", profile.name)
	for table_field in ("basic_allocations", "transportation_allocations", "family_allowance_allocations"):
		profile[table_field] = [row.as_dict() for row in profile_doc.get(table_field)]
	profile.revision_count = frappe.db.count("Employee Salary Revision", {"salary_profile": profile.name})
	profile.revisions = get_revision_history(profile.name)
	payroll_employees = frappe.get_all("Employee", filters={"custom_master_employee": employee}, pluck="name")
	payroll_employees.append(employee)
	profile.salary_slips = frappe.get_all(
		"Salary Slip", filters={"employee": ["in", payroll_employees], "docstatus": ["<", 2]},
		fields=["name", "company", "start_date", "end_date", "currency", "net_pay", "docstatus"],
		order_by="end_date desc", limit=5,
	)
	return profile


@frappe.whitelist()
def get_salary_profile_editor(employee):
	check_salary_access()
	profile_name = frappe.db.get_value("Employee Salary Profile", {"employee": employee}, "name")
	if not profile_name:
		return {"exists": False, "employee": employee}
	profile = frappe.get_doc("Employee Salary Profile", profile_name)
	return {
		"exists": True,
		"name": profile.name,
		"employee": employee,
		"effective_date": profile.effective_date,
		"last_action_date": profile.last_action_date,
		"basic_allocations": [row.as_dict() for row in profile.basic_allocations],
		"transportation_allocations": [row.as_dict() for row in profile.transportation_allocations],
		"family_allowance_allocations": [row.as_dict() for row in profile.family_allowance_allocations],
	}


@frappe.whitelist()
def save_salary_profile_from_employee(payload):
	check_salary_access()
	data = frappe.parse_json(payload)
	employee = data.get("employee")
	if not employee or not frappe.db.exists("Employee", employee):
		frappe.throw(_("Select a valid employee."))
	profile_name = frappe.db.get_value("Employee Salary Profile", {"employee": employee}, "name")
	profile = frappe.get_doc("Employee Salary Profile", profile_name) if profile_name else frappe.new_doc("Employee Salary Profile")
	profile.employee = employee
	profile.effective_date = data.get("effective_date")
	profile.action_date = data.get("action_date")
	for table_field in ("basic_allocations", "transportation_allocations", "family_allowance_allocations"):
		profile.set(table_field, [])
		for row in data.get(table_field) or []:
			profile.append(table_field, {
				"company": row.get("company"),
				"account": row.get("account"),
				"cost_center": row.get("cost_center"),
				"amount": row.get("amount"),
			})
	profile.save()
	return get_salary_profile_summary(employee)


@frappe.whitelist()
def get_revision_history(profile):
	check_salary_access()
	return frappe.get_all(
		"Employee Salary Revision", filters={"salary_profile": profile},
		fields=["name", "revision_number", "effective_from", "effective_to", "action_date", "basic_salary", "transportation", "family_allowance", "total_salary", "changed_by", "change_summary"],
		order_by="revision_number desc",
	)
